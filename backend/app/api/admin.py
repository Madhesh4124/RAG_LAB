from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.compare.collection_registry import clear_collection_registry
from app.models.user import User
from app.services.pipeline_manager import PipelineManager

try:
    from chromadb import PersistentClient
except Exception:  # pragma: no cover - chromadb should be installed in runtime
    PersistentClient = None

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _is_admin_user(user: User) -> bool:
    if getattr(user, "is_admin", False):
        return True
    seed_username = os.getenv("AUTH_SEED_USERNAME", "admin")
    seed_email = os.getenv("AUTH_SEED_EMAIL", "admin@local")
    return user.username == seed_username or user.email == seed_email


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _storage_roots() -> List[Path]:
    roots = [
        Path(os.getenv("CHROMA_PERSIST_DIR", str(_project_root() / "chroma_db"))),
        _project_root() / "chroma_db",
        _project_root() / "chroma_store",
        _project_root() / "chroma_data",
    ]
    deduped: List[Path] = []
    seen = set()
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(resolved)
    return deduped


def _collection_client(root: Path):
    if PersistentClient is None:
        raise HTTPException(status_code=500, detail="Chroma client is not available")
    root.mkdir(parents=True, exist_ok=True)
    return PersistentClient(path=str(root))


def _clear_collections_in_root(root: Path) -> List[str]:
    """Delete all collections from a specific root using Chroma APIs first."""
    try:
        client = _collection_client(root)
        collections = client.list_collections()
    except Exception:
        return []

    deleted: List[str] = []
    for collection in collections:
        name = getattr(collection, "name", collection if isinstance(collection, str) else None)
        if not name:
            continue
        try:
            client.delete_collection(name=name)
            deleted.append(str(name))
        except Exception:
            continue
    return deleted


def _clear_runtime_caches() -> None:
    """Release in-memory references that can keep Chroma files/collections active."""
    try:
        clear_collection_registry()
    except Exception:
        pass
    try:
        PipelineManager.clear_cache()
    except Exception:
        pass


def _list_root_collections(root: Path) -> List[Dict[str, Any]]:
    try:
        client = _collection_client(root)
        collections = client.list_collections()
    except Exception:
        return []

    summaries: List[Dict[str, Any]] = []
    for collection in collections:
        collection_obj = collection
        if isinstance(collection, str):
            try:
                collection_obj = client.get_collection(name=collection)
            except Exception:
                collection_obj = None

        if collection_obj is None:
            continue

        try:
            count = int(collection_obj.count())
        except Exception:
            count = 0

        sample_docs: List[Dict[str, Any]] = []
        try:
            sample = collection_obj.get(limit=3, include=["documents", "metadatas"])
            ids = sample.get("ids", []) if isinstance(sample, dict) else []
            documents = sample.get("documents", []) if isinstance(sample, dict) else []
            metadatas = sample.get("metadatas", []) if isinstance(sample, dict) else []
            for idx, sample_id in enumerate(ids[:3]):
                sample_docs.append({
                    "id": sample_id,
                    "document": documents[idx] if idx < len(documents) else None,
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                })
        except Exception:
            sample_docs = []

        summaries.append({
            "name": getattr(collection_obj, "name", collection if isinstance(collection, str) else "unknown"),
            "count": count,
            "metadata": getattr(collection_obj, "metadata", {}) or {},
            "samples": sample_docs,
        })
    return summaries


class ChromaCollectionDetail(BaseModel):
    name: str
    count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    samples: List[Dict[str, Any]] = Field(default_factory=list)


class ChromaRootDetail(BaseModel):
    root_path: str
    collections: List[ChromaCollectionDetail] = Field(default_factory=list)


class ChromaDeleteResponse(BaseModel):
    status: str
    deleted: List[str] = Field(default_factory=list)


@router.get("/chroma", response_model=List[ChromaRootDetail])
def list_chroma_roots(current_user: User = Depends(require_admin)):
    _ = current_user
    roots = []
    for root in _storage_roots():
        roots.append(
            ChromaRootDetail(
                root_path=str(root),
                collections=[ChromaCollectionDetail(**collection) for collection in _list_root_collections(root)],
            )
        )
    return roots


@router.get("/chroma/collections/{collection_name}", response_model=List[ChromaRootDetail])
def view_collection(collection_name: str, current_user: User = Depends(require_admin)):
    _ = current_user
    roots: List[ChromaRootDetail] = []
    for root in _storage_roots():
        collections = [collection for collection in _list_root_collections(root) if collection["name"] == collection_name]
        if collections:
            roots.append(ChromaRootDetail(root_path=str(root), collections=[ChromaCollectionDetail(**collection) for collection in collections]))
    return roots


@router.delete("/chroma/collections/{collection_name}", response_model=ChromaDeleteResponse)
def delete_collection(
    collection_name: str,
    root_path: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
):
    _ = current_user
    deleted: List[str] = []
    roots = _storage_roots() if root_path is None else [Path(root_path).resolve()]

    for root in roots:
        try:
            client = _collection_client(root)
            client.delete_collection(name=collection_name)
            deleted.append(f"{root}:{collection_name}")
        except Exception:
            continue

    if not deleted:
        raise HTTPException(status_code=404, detail="Collection not found")

    return ChromaDeleteResponse(status="success", deleted=deleted)


@router.delete("/chroma/root", response_model=ChromaDeleteResponse)
def clear_root(
    root_path: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
):
    _ = current_user
    roots = [Path(root_path).resolve()] if root_path else _storage_roots()
    deleted: List[str] = []

    _clear_runtime_caches()

    for target_root in roots:
        try:
            _clear_collections_in_root(target_root)
        except Exception:
            pass

        if target_root.exists():
            try:
                shutil.rmtree(target_root)
            except Exception:
                # If filesystem removal is blocked by locks, keep folder but collections
                # are already deleted through Chroma API.
                pass
        target_root.mkdir(parents=True, exist_ok=True)
        deleted.append(str(target_root))

    return ChromaDeleteResponse(status="success", deleted=deleted)