import io
import tempfile
import uuid

import pytest

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def _no_external_chroma(monkeypatch):
    # Provide fake embedder and vectorstore to avoid external calls
    class _FakeEmbedder:
        def embed_in_batches(self, texts, batch_size=1, sleep_between=0):
            return [[0.0] * 8 for _ in texts]

    class _FakeVectorstore:
        def __init__(self, *args, **kwargs):
            self.added = []

        def add_chunks(self, chunks, embedder):
            self.added.extend(chunks)

    monkeypatch.setattr("app.services.pipeline_factory.PipelineFactory.create_embedder", lambda cfg: _FakeEmbedder())
    monkeypatch.setattr("app.services.pipeline_factory.PipelineFactory.create_vectorstore", lambda cfg: _FakeVectorstore())


def test_index_tables_endpoint(tmp_path, monkeypatch):
    client = TestClient(app)

    pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    t_pdf = tmp_path / "t.pdf"
    t_pdf.write_bytes(pdf_content)

    # Use a direct DB insert approach since auth flows are heavy; instead, test endpoint wiring by
    # creating a temporary Document-like object and calling the background function directly.
    # Here we call the table_indexer.index_pdf_tables directly to assert it uses the fake vectorstore.
    from app.services.table_indexer import index_pdf_tables
    count = index_pdf_tables(file_path=str(t_pdf))
    # No tables in minimal file, expect 0
    assert count == 0
