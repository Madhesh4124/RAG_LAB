from app.api.documents import list_documents, search_documents


def test_list_documents_scopes_by_user(db_session, user_a, user_b, sample_docs):
    rows_a = list_documents(skip=0, limit=50, current_user=user_a, db=db_session)
    rows_b = list_documents(skip=0, limit=50, current_user=user_b, db=db_session)

    assert len(rows_a) == 1
    assert rows_a[0].filename == "alpha.txt"

    assert len(rows_b) == 1
    assert rows_b[0].filename == "beta.txt"


def test_search_documents_scopes_by_user(db_session, user_a, user_b, sample_docs):
    # user_a should not be able to discover user_b docs via search.
    rows = search_documents(query="beta", limit=50, current_user=user_a, db=db_session)
    assert rows == []
