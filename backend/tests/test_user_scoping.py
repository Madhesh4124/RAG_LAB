from fastapi import HTTPException
from app.api.documents import get_index_status, list_documents, search_documents
from app.services.indexing_jobs import IndexingJobStore


import pytest


@pytest.mark.anyio
async def test_list_documents_scopes_by_user(async_db_session, user_a, user_b, sample_docs):
    rows_a = await list_documents(skip=0, limit=50, current_user=user_a, db=async_db_session)
    rows_b = await list_documents(skip=0, limit=50, current_user=user_b, db=async_db_session)

    assert len(rows_a) == 1
    assert rows_a[0].filename == "alpha.txt"

    assert len(rows_b) == 1
    assert rows_b[0].filename == "beta.txt"


@pytest.mark.anyio
async def test_search_documents_scopes_by_user(async_db_session, user_a, user_b, sample_docs):
    # user_a should not be able to discover user_b docs via search.
    rows = await search_documents(query="beta", limit=50, current_user=user_a, db=async_db_session)
    assert rows == []


@pytest.mark.anyio
async def test_get_index_status_scopes_by_user(async_db_session, user_a, user_b, sample_docs):
    doc_a, _ = sample_docs
    job_id = IndexingJobStore.create(doc_id=str(doc_a.id), config_id="cfg-1", user_id=str(user_a.id))
    unscoped_job_id = IndexingJobStore.create(doc_id=str(doc_a.id), config_id="cfg-2")
    try:
        owner_view = await get_index_status(job_id=job_id, current_user=user_a, db=async_db_session)
        assert owner_view["job_id"] == job_id

        with pytest.raises(HTTPException) as exc:
            await get_index_status(job_id=job_id, current_user=user_b, db=async_db_session)
        assert exc.value.status_code == 404

        fallback_owner = await get_index_status(job_id=unscoped_job_id, current_user=user_a, db=async_db_session)
        assert fallback_owner["job_id"] == unscoped_job_id

        with pytest.raises(HTTPException) as exc2:
            await get_index_status(job_id=unscoped_job_id, current_user=user_b, db=async_db_session)
        assert exc2.value.status_code == 404
    finally:
        IndexingJobStore._jobs.pop(job_id, None)
        IndexingJobStore._jobs.pop(unscoped_job_id, None)
