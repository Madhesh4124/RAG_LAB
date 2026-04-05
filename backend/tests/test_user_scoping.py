from app.api.documents import list_documents, search_documents


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
