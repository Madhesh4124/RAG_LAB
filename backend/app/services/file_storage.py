import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

class FileStorageBackend(ABC):
    @abstractmethod
    def save(self, data: bytes, extension: str) -> str:
        """Save data and return a unique storage key."""
        pass

    @abstractmethod
    def load(self, key: str) -> bytes:
        """Load data by storage key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete data by storage key."""
        pass

class LocalFileStorage(FileStorageBackend):
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.getenv("UPLOAD_DIR", "./uploads")
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, extension: str = "pdf") -> str:
        key = f"{uuid.uuid4().hex}.{extension}"
        file_path = self.base_dir / key
        file_path.write_bytes(data)
        return key

    def load(self, key: str) -> bytes:
        file_path = self.base_dir / key
        if not file_path.exists():
            raise FileNotFoundError(f"File with key {key} not found in LocalFileStorage")
        return file_path.read_bytes()

    def delete(self, key: str) -> None:
        file_path = self.base_dir / key
        if file_path.exists():
            file_path.unlink()

# Simple factory
def get_file_storage() -> FileStorageBackend:
    # In the future, we can read an env var STORAGE_BACKEND=s3 to return S3FileStorage
    return LocalFileStorage()
