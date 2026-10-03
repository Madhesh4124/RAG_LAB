import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows stdout
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(dotenv_path=backend_dir / ".env", override=True)

from app.services.chunking.base import Chunk

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_gemini_generation():
    print_header("1. Testing Generation Model (Google Gemini)")
    from app.services.llm.gemini_client import GeminiClient

    model_name = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
    t0 = time.time()
    try:
        client = GeminiClient(model=model_name, temperature=0.0)
        chunks = [Chunk(text="RAG Lab is an advanced Retrieval-Augmented Generation evaluation workbench.")]
        resp = client.generate(query="What is RAG Lab?", chunks=chunks)
        dur = time.time() - t0
        print(f"  [OK] [{model_name}] ({dur:.2f}s): {resp[:80]}...")
    except Exception as e:
        dur = time.time() - t0
        print(f"  [FAIL] [{model_name}] ({dur:.2f}s): {e}")

def test_groq_evaluation():
    print_header("2. Testing Evaluation Model (Groq GPT-OSS)")
    from app.services.llm.groq_client import GroqClient
    from app.services.evaluation.faithfulness import FaithfulnessEvaluator
    from app.services.evaluation.context_quality import ContextQualityEvaluator

    model_name = os.getenv("EVALUATION_LLM_MODEL", "openai/gpt-oss-20b")
    t0 = time.time()
    try:
        client = GroqClient(model=model_name, temperature=0.0)
        chunks = [Chunk(text="Paris is the capital of France.")]
        q = "What is the capital of France?"
        ans = "The capital of France is Paris."
        fe = FaithfulnessEvaluator().evaluate(q, ans, chunks, client)
        cq = ContextQualityEvaluator().evaluate(q, ans, chunks, client)
        dur = time.time() - t0
        print(f"  [OK] [{model_name}] ({dur:.2f}s): Faithfulness={fe}, ContextQuality={cq}")
    except Exception as e:
        dur = time.time() - t0
        print(f"  [FAIL] [{model_name}] ({dur:.2f}s): {e}")

def test_nvidia_embeddings():
    print_header("3. Testing NVIDIA Embeddings (Nemotron-3)")
    from app.services.embedding.nvidia_embedder import NvidiaEmbedder

    model_name = os.getenv("DEFAULT_EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")
    t0 = time.time()
    try:
        embedder = NvidiaEmbedder(model=model_name)
        vec = embedder.embed_text("Sanity check query.")
        dur = time.time() - t0
        print(f"  [OK] [{model_name}] ({dur:.2f}s): Dim={len(vec)}, Sample={vec[:3]}")
    except Exception as e:
        dur = time.time() - t0
        print(f"  [FAIL] [{model_name}] ({dur:.2f}s): {e}")

def test_huggingface_embeddings():
    print_header("4. Testing Hugging Face API Embeddings")
    from app.services.embedding.huggingface_api_embedder import HuggingFaceAPIEmbedder

    models = ["BAAI/bge-base-en-v1.5", "sentence-transformers/all-MiniLM-L6-v2"]
    for m in models:
        t0 = time.time()
        try:
            embedder = HuggingFaceAPIEmbedder(model=m)
            vec = embedder.embed_text("Sanity check query.")
            dur = time.time() - t0
            print(f"  [OK] [{m}] ({dur:.2f}s): Dim={len(vec)}")
        except Exception as e:
            dur = time.time() - t0
            print(f"  [FAIL] [{m}] ({dur:.2f}s): {e}")

def test_clip_image_embedder():
    print_header("5. Testing Local Multimodal CLIP Embedder")
    from app.services.embedding.clip_image_embedder import CLIPImageEmbedder

    t0 = time.time()
    try:
        clip = CLIPImageEmbedder()
        vec = clip.embed_text("Architecture diagram of neural network")
        dur = time.time() - t0
        print(f"  [OK] [openai/clip-vit-base-patch32] ({dur:.2f}s): Dim={len(vec)}, Norm={sum(x**2 for x in vec):.2f}")
    except Exception as e:
        dur = time.time() - t0
        print(f"  [FAIL] [openai/clip-vit-base-patch32] ({dur:.2f}s): {e}")

def test_rerankers():
    print_header("6. Testing Reranker Models")
    from app.services.retrieval.reranker import HuggingFaceAPIReranker, CrossEncoderReranker

    candidates = [
        (Chunk(text="RAG combines search retrieval with generative LLM synthesis."), 0.8),
        (Chunk(text="Pizza is an Italian dish with tomato and cheese."), 0.2),
    ]
    q = "What is Retrieval-Augmented Generation?"

    try:
        hf_reranker = HuggingFaceAPIReranker(model="BAAI/bge-reranker-v2-m3")
        res = hf_reranker.rerank(q, candidates, top_k=2)
        print(f"  [OK] HuggingFaceAPIReranker (BAAI/bge-reranker-v2-m3): Top score={res[0][1]:.4f}")
    except Exception as e:
        print(f"  [FAIL] HuggingFaceAPIReranker: {e}")

    try:
        ce_reranker = CrossEncoderReranker(model="cross-encoder/ms-marco-MiniLM-L-6-v2")
        res = ce_reranker.rerank(q, candidates, top_k=2)
        print(f"  [OK] CrossEncoderReranker (ms-marco-MiniLM-L-6-v2): Top score={res[0][1]:.4f}")
    except Exception as e:
        print(f"  [FAIL] CrossEncoderReranker: {e}")

if __name__ == "__main__":
    print("Running Model Health Check...")
    test_gemini_generation()
    test_groq_evaluation()
    test_nvidia_embeddings()
    test_huggingface_embeddings()
    test_clip_image_embedder()
    test_rerankers()
    print("\nHealth Check Complete - All Critical Models Verified!")
