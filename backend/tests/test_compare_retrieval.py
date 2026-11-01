import pytest
from app.compare.schemas import RAGConfig
from app.compare.utils import derive_config_signature
from app.compare.compare_runner import _retrieve_compare_candidates
from langchain_core.documents import Document


def test_rag_config_retrieval_parameters():
    config = RAGConfig(
        name="Hybrid Config",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=6,
        threshold=0.45,
        retrieval_type="hybrid",
        alpha=0.8,
        reranker_enabled=True,
        reranker_model="BAAI/bge-reranker-base",
    )
    assert config.retrieval_type == "hybrid"
    assert config.alpha == 0.8
    assert config.top_k == 6
    assert config.threshold == 0.45
    assert config.reranker_enabled is True
    assert config.reranker_model == "BAAI/bge-reranker-base"


def test_rag_config_signature_sensitivity():
    c1 = RAGConfig(
        name="Config 1",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        retrieval_type="dense",
    )
    c2 = RAGConfig(
        name="Config 2",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        retrieval_type="hybrid",
        alpha=0.4,
    )
    sig1 = derive_config_signature(c1)
    sig2 = derive_config_signature(c2)
    assert sig1 != sig2


class DummyVectorStore:
    def __init__(self, docs_and_scores):
        self.docs_and_scores = docs_and_scores

    def similarity_search_with_score(self, query, k):
        return self.docs_and_scores[:k]

    def max_marginal_relevance_search(self, query, k, fetch_k, lambda_mult=0.5):
        return [doc for doc, _ in self.docs_and_scores[:k]]

    def get(self):
        return {
            "documents": [d.page_content for d, _ in self.docs_and_scores],
            "metadatas": [d.metadata for d, _ in self.docs_and_scores],
            "ids": [f"chunk_{i}" for i in range(len(self.docs_and_scores))],
        }


def test_retrieve_compare_candidates_strategies():
    test_docs = [
        (Document(page_content="Machine learning enables AI applications.", metadata={"id": "1"}), 0.2), # distance 0.2 -> similarity 0.8
        (Document(page_content="Deep neural networks require substantial computing power.", metadata={"id": "2"}), 0.4), # distance 0.4 -> similarity 0.6
        (Document(page_content="Cooking recipes for Italian pasta dishes.", metadata={"id": "3"}), 0.9), # distance 0.9 -> similarity 0.1
    ]
    vs = DummyVectorStore(test_docs)

    # 1. Dense retrieval
    dense_cfg = RAGConfig(
        name="Dense Test",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=2,
        threshold=0.5,
        retrieval_type="dense",
    )
    candidates, filtered = _retrieve_compare_candidates("machine learning", dense_cfg, vs, user_scope="test_user")
    assert len(candidates) >= 2
    assert len(filtered) <= 2
    assert "Machine learning" in filtered[0][0].page_content

    # 2. MMR retrieval
    mmr_cfg = RAGConfig(
        name="MMR Test",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=2,
        threshold=0.5,
        retrieval_type="mmr",
        lambda_mult=0.7,
    )
    candidates_mmr, filtered_mmr = _retrieve_compare_candidates("AI networks", mmr_cfg, vs, user_scope="test_user")
    assert len(filtered_mmr) <= 2

    # 3. Hybrid retrieval
    hybrid_cfg = RAGConfig(
        name="Hybrid Test",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=2,
        threshold=0.3,
        retrieval_type="hybrid",
        alpha=0.6,
    )
    candidates_hyb, filtered_hyb = _retrieve_compare_candidates("pasta cooking", hybrid_cfg, vs, user_scope="test_user")
    assert len(filtered_hyb) > 0

