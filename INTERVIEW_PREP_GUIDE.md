# 🔬 RAG Lab: Comprehensive System Architecture, Design Decisions & Technical Interview Handbook

> **Project Reference**: `RAG_LAB`  
> **Tech Stack**: Python 3.10+ • FastAPI • LangChain • ChromaDB • Rank-BM25 • NVIDIA NIM • Groq • React 19 • Vite • Tailwind CSS  
> **Target Audience**: Full-Stack AI Engineers, ML Platform Engineers, Applied AI Candidates, Technical Interviewers

---

## 📑 Table of Contents

1. [Executive Summary & High-Level Architecture](#1-executive-summary--high-level-architecture)
2. [System Internals, Data Models & Algorithmic Foundations](#2-system-internals-data-models--algorithmic-foundations)
   - [2.1 Relational Database Schema & Data Modeling](#21-relational-database-schema--data-modeling)
   - [2.2 Dynamic Pipeline Factory & Config Fingerprinting](#22-dynamic-pipeline-factory--config-fingerprinting)
   - [2.3 Mathematical & Algorithmic Formulation Reference](#23-mathematical--algorithmic-formulation-reference)
   - [2.4 System Failure Modes & Multi-Tier Resilience Matrix](#24-system-failure-modes--multi-tier-resilience-matrix)
3. [Deep Architectural Breakdown & Decision Comparison Matrices](#3-deep-architectural-breakdown--decision-comparison-matrices)
   - [3.1 Document Ingestion & Layout-Preserving Extraction](#31-document-ingestion--layout-preserving-extraction)
   - [3.2 Chunking Strategies & Boundary Optimization](#32-chunking-strategies--boundary-optimization)
   - [3.3 Embedding Models & Vector Spaces](#33-embedding-models--vector-spaces)
   - [3.4 Vector Storage & Persistence Engine](#34-vector-storage--persistence-engine)
   - [3.5 Retrieval Strategies: Hybrid Convex Search & MMR](#35-retrieval-strategies-hybrid-convex-search--mmr)
   - [3.6 Two-Stage Retrieval & Cross-Encoder Reranking](#36-two-stage-retrieval--cross-encoder-reranking)
   - [3.7 LLM Generation, Orchestration & Reasoning Control](#37-llm-generation-orchestration--reasoning-control)
   - [3.8 Evaluation System: Real-Time Heuristics & Decoupled LLM-as-a-Judge](#38-evaluation-system-real-time-heuristics--decoupled-llm-as-a-judge)
   - [3.9 Multi-Tenancy, Security & Cross-Origin Auth](#39-multi-tenancy-security--cross-origin-auth)
   - [3.10 Frontend Architecture & Real-Time SSE Streaming](#310-frontend-architecture--real-time-sse-streaming)
4. [Engineering War Stories & Production Bottlenecks Solved](#4-engineering-war-stories--production-bottlenecks-solved)
5. [Complete Step-by-Step Execution Walkthroughs](#5-complete-step-by-step-execution-walkthroughs)
   - [5.1 Document Upload & Multi-Stage Indexing Pipeline](#51-document-upload--multi-stage-indexing-pipeline)
   - [5.2 Real-Time SSE Streaming Query Execution](#52-real-time-sse-streaming-query-execution)
   - [5.3 Parallel Multi-Configuration Benchmarking Lab](#53-parallel-multi-configuration-benchmarking-lab)
   - [5.4 On-Demand Decoupled Evaluation Lifecycle](#54-on-demand-decoupled-evaluation-lifecycle)
6. [The 25 Ultimate Technical Interview Questions & Answers](#6-the-25-ultimate-technical-interview-questions--answers)
   - [Category 1: RAG Architecture & System Design](#category-1-rag-architecture--system-design)
   - [Category 2: Information Retrieval, Indexing & Math](#category-2-information-retrieval-indexing--math)
   - [Category 3: Production Latency, Scalability & Concurrency](#category-3-production-latency-scalability--concurrency)
   - [Category 4: LLMs, Reasoning Control & Evaluation Rigor](#category-4-llms-reasoning-control--evaluation-rigor)
   - [Category 5: Security, Multi-Tenancy & Edge Cases](#category-5-security-multi-tenancy--edge-cases)

---

## 1. Executive Summary & High-Level Architecture

### What is RAG Lab?
Most developers follow introductory tutorials that implement a "Toy RAG" application: load a PDF with a basic wrapper, split text by naive 500-character windows, embed into an in-memory vector store with default OpenAI embeddings, query top-3 nearest neighbors via raw cosine distance, and stuff them blindly into a prompt.

In production, **Toy RAG fails catastrophically**:
* Tables and financial spreadsheets get scrambled into meaningless sentence fragments.
* Generic queries ("Summarize the main revenue takeaways") fail because vector similarity searches for local semantic matches rather than global thematic overviews.
* Lexical keywords (acronyms, model numbers, IDs like `TX-9021`) are missed entirely by dense vector search.
* Large context windows trigger the "Lost-in-the-Middle" phenomenon, increasing latency and cost without improving answer quality.
* Evaluators running inline with user queries cause backend thread starvation and gateway timeouts.

**RAG Lab** is a full-stack, multi-tenant engineering platform engineered to **design, benchmark, tune, and evaluate** industrial-grade Retrieval-Augmented Generation pipelines. It provides an interactive laboratory where engineers can swap, inspect, and benchmark every component of the RAG lifecycle side-by-side.

```
                              ┌────────────────────────────────────────────────────────┐
                              │           React 19 / Vite SPA Frontend (Vercel)        │
                              └───────────────────────────┬────────────────────────────┘
                                                          │ HTTP / SSE / Bearer Auth
                                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Application Server (AsyncIO / Gunicorn / Uvicorn)                                                    │
│                                                                                                              │
│  ┌──────────────────────────────────┐  ┌─────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │ Security & Identity Engine       │  │ Database-Backed Rate Limiting   │  │ Pipeline Factory & Manager  │  │
│  │ • itsdangerous signed cookies    │  │ • Sliding 1-hr DB window        │  │ • Dynamic instantiation     │  │
│  │ • Cross-origin Bearer tokens     │  │ • 15 LLM / 50 Embed / 100 Search│  │ • Process-safe caching      │  │
│  └──────────────────────────────────┘  └─────────────────────────────────┘  └─────────────────────────────┘  │
│                                                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Multi-Stage Ingestion & Layout Preservation Worker                                                     │  │
│  │ • Dual-Engine PDF Extractor: pdfplumber (table grid detection) + pypdf (high-speed text extraction)    │  │
│  │ • Markdown Table Reconstruct: multi-level column preservation + GitHub-flavored markdown formatting    │  │
│  │ • Multimodal Image Extractor: figures saved to disk + embedded via local CLIP into sibling collections │  │
│  │ • BackgroundTasks Worker: asynchronous job polling via IndexingJobStore (zero request blocking)        │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                              │
│  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │ Chunking & Windowing Layer      │   │ Embedding & Vector Layer        │  │ Retrieval & Fusion Layer    │  │
│  │ • Fixed-Size & Overlap          │   │ • NVIDIA Nemotron-3-Embed-1B    │  │ • Dense ChromaDB (Cosine)   │  │
│  │ • Recursive Separators          │   │ • HuggingFace all-MiniLM-L6-v2  │  │ • Sparse Disk-Cached BM25   │  │
│  │ • Semantic Centroid-Drift       │   │ • Local CLIP Image Embeddings   │  │ • Convex Fusion (α·D + (1-α)·S││
│  │ • Sentence-Window (Context Exp) │   │ • Batched Sequential Scheduling │  │ • Maximal Marginal Relevance │ │
│  │ • Chapter Heading Anchors       │   │ • ChromaDB Multi-Tenant Namesp. │  │ • Nemotron-3.5-Rerank-8B    │  │
│  └─────────────────────────────────┘   └─────────────────────────────────┘  └─────────────────────────────┘  │
│                                                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  ┌─────────────────────────────┐ │
│  │ Model Orchestration & Generation (Streaming SSE)                      │  │ Evaluation Suite            │ │
│  │ • NVIDIA Nemotron-3.5-Lightning-30B (enable_thinking=False)           │  │ • 0ms Heuristics: P@K, R@K, │ │
│  │ • Groq GPT-OSS-120B / LLaMA-3.3-70B (Fast fallback & judge)           │  │   HitRate, MRR, NDCG, Div   │ │
│  │ • Google Gemini 2.5 Flash Integration                                 │  │ • Lazy LLM Judge:           │ │
│  │ • Dual-Mode Routing: Local Factoid vs Global Document-Level Summary   │  │   Faithfulness, Relevancy,  │ │
│  │ • Streaming SSE with immediate metadata emission                      │  │   Context Recall via Groq   │ │
│  └───────────────────────────────────────────────────────────────────────┘  └─────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. System Internals, Data Models & Algorithmic Foundations

This section details the internal data models, the dynamic component assembly pattern, mathematical formulas, and the system resilience matrix.

### 2.1 Relational Database Schema & Data Modeling

The platform operates on SQLite (configured with Write-Ahead Logging `WAL` mode and 5000ms busy timeouts) or PostgreSQL, orchestrated via **SQLAlchemy Asyncio** and **Alembic** migrations. The schema balances relational isolation with document-level flexibility:

```
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│              User               │ 1       * │            Document             │
│  - id: UUID (PK)                ├───────────► - id: UUID (PK)                 │
│  - email: String (Unique)       │           │ - user_id: UUID (FK -> User.id) │
│  - password_hash: String        │           │ - filename: String              │
│  - is_admin: Boolean            │           │ - file_type: String (pdf/txt)   │
│  - created_at: DateTime (UTC)   │           │ - file_size: Integer (Bytes)    │
└────────────────┬────────────────┘           │ - content: Text (pdf://UUID ptr)│
                 │ 1                          │ - content_sha256: String(64)    │
                 │                            │ - upload_date: DateTime (UTC)   │
                 │                            └────────────────┬────────────────┘
                 │                                             │ 1
                 │                                             │ *
                 │                            ┌────────────────▼────────────────┐
                 │                            │              Chunk              │
                 │                            │ - id: UUID (PK)                 │
                 │                            │ - document_id: UUID (FK)        │
                 │                            │ - content: Text                 │
                 │                            │ - chunk_index: Integer          │
                 │                            │ - chunk_strategy: String        │
                 │                            │ - metadata: JSON                │
                 │                            └─────────────────────────────────┘
                 │
                 ├────────────────────────────┐
                 │ 1                          │ 1
                 ▼ *                          ▼ *
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│            RAGConfig            │  │           ChatMessage           │
│ - id: UUID (PK)                 │  │ - id: UUID (PK)                 │
│ - user_id: UUID (FK -> User.id) │  │ - user_id: UUID (FK -> User.id) │
│ - name: String                  │  │ - document_id: UUID (FK)        │
│ - config_json: JSON             │  │ - config_id: UUID (FK)          │
│ - is_active: Boolean            │  │ - role: String (user/assistant) │
│ - created_at: DateTime (UTC)    │  │ - content: Text                 │
└─────────────────────────────────┘  │ - retrieved_chunks: JSON        │
                                     │ - timestamp: DateTime (UTC)     │
                                     └────────────────┬────────────────┘
                                                      │ 1
                                                      │ 1
                                     ┌────────────────▼────────────────┐
                                     │             Metrics             │
                                     │ - id: UUID (PK)                 │
                                     │ - message_id: UUID (FK)         │
                                     │ - chunking_time_ms: Float       │
                                     │ - embedding_time_ms: Float      │
                                     │ - retrieval_time_ms: Float      │
                                     │ - reranking_time_ms: Float      │
                                     │ - llm_time_ms: Float            │
                                     │ - total_time_ms: Float          │
                                     │ - avg_similarity: Float         │
                                     │ - token_count: Integer          │
                                     └─────────────────────────────────┘
```

#### Key Data Modeling Decisions:
1. **Pointer Decoupling for File Storage (`pdf://{uuid}`)**: Storing multi-megabyte binary PDFs directly as Base64 in database columns degrades query performance and increases memory usage. PDFs are saved to disk (`uploads/{uuid}.pdf`), and the database stores a lightweight URI pointer (`pdf://{uuid}`).
2. **Hybrid Relational + JSON Columns**: Core entity identities (`user_id`, `document_id`, `config_id`) use indexed relational foreign keys to guarantee multi-tenant boundary checks. Dynamic payloads—such as pipeline configurations (`config_json`) and retrieved citations with scores (`retrieved_chunks`)—are stored as JSON to allow parameter customization without requiring schema migrations.
3. **Observability via Dedicated `Metrics` Entity**: Every assistant message links to a `Metrics` record populated by `PipelineTimer`. This enables tracking latency regressions per user, document size, or pipeline component over time.
4. **Independent `RateLimitEvent` Table**: To enforce sliding-window rate limits across asynchronous workers, call timestamps are recorded in a separate table (`rate_limit_events`) and pruned periodically using database queries.

---

### 2.2 Dynamic Pipeline Factory & Config Fingerprinting

The system uses the **Abstract Factory Pattern** (`PipelineFactory`) to instantiate pipelines dynamically from nested JSON configurations without hardcoded conditional logic:

```python
# Pipeline configuration schema structure
{
  "chunker":     {"type": "sentence_window", "window_size": 5, "max_chunk_size": 150},
  "embedder":    {"provider": "nvidia", "model": "nvidia/nemotron-3-embed-1b"},
  "vectorstore": {"type": "chroma", "collection_name": "user_..._rag_cfg_..."},
  "retriever":   {"type": "hybrid", "alpha": 0.7, "top_k": 5, "similarity_threshold": 0.35},
  "reranker":    {"enabled": True, "provider": "nvidia", "model": "nvidia/nemotron-3.5-rerank-8b"},
  "llm":         {"provider": "nvidia", "model": "nvidia/nemotron-3.5-lightning-30b-a3b"},
  "memory":      {"type": "buffer", "max_turns": 6}
}
```

#### Deterministic Cache Fingerprinting
To determine whether an indexed vector collection can be reused or must be rebuilt, the pipeline computes a **SHA-256 Config Fingerprint**:

$$\text{Fingerprint} = \text{SHA256}\Big(\text{JSON}_{\text{sorted\_keys}}(\text{chunker\_config}) \Big)[:16]$$

$$\text{ContentHash} = \text{SHA256}\Big(\text{Fingerprint} \parallel \text{Text}\Big)$$

If the user changes `chunk_size` from `512` to `256`, the fingerprint changes automatically, triggering re-chunking and re-embedding while avoiding redundant indexing when configurations match.

#### Process-Safe Pipeline Caching (`PipelineManager`)
Instantiating embedding models, tokenizers, and database clients on every message adds unnecessary latency. `PipelineManager` caches pipeline instances using a composite key:

$$\text{CacheKey} = \text{user\_id} \mathbin{\Vert} \text{config\_id}$$

This ensures that active pipeline instances are reused across sequential chat turns while keeping different users and configurations strictly isolated.

---

### 2.3 Mathematical & Algorithmic Formulation Reference

#### 1. Okapi BM25 Lexical Ranking
BM25 scores document chunk $D$ against query $Q$ with terms $q_1, \dots, q_n$:

$$\text{Score}(D, Q) = \sum_{i=1}^n \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$

$$\text{IDF}(q_i) = \ln \left( \frac{N - n(q_i) + 0.5}{n(q_i) + 0.5} + 1 \right)$$

* $f(q_i, D)$: Raw term frequency of word $q_i$ in chunk $D$.
* $|D|$ and $\text{avgdl}$: Chunk character length and average chunk length across the corpus.
* $k_1 = 1.5$: Term frequency saturation parameter (limits the score boost from repeating terms).
* $b = 0.75$: Document length penalization parameter.

#### 2. Linear Convex Hybrid Fusion
Combines dense semantic vector scores and sparse BM25 scores:

$$S_{\text{hybrid}} = \alpha \cdot S_{\text{dense}} + (1 - \alpha) \cdot S_{\text{sparse}}$$

* $S_{\text{dense}} = 1.0 - \text{CosineDistance} \in [0, 1]$ (or distance normalized via $\frac{1}{1 + d}$).
* $S_{\text{sparse}} = \frac{\text{BM25Score} - \min(\text{BM25})}{\max(\text{BM25}) - \min(\text{BM25}) + \epsilon} \in [0, 1]$.
* $\alpha = 0.7$: Tunable convex weight (70% dense conceptual, 30% sparse lexical).

#### 3. Maximal Marginal Relevance (MMR)
Balances query relevance against redundancy with already-selected documents:

$$\text{MMR}(Q, R, S) = \arg\max_{D_i \in R \setminus S} \left[ \lambda \cdot \text{Sim}_1(D_i, Q) - (1 - \lambda) \max_{D_j \in S} \text{Sim}_2(D_i, D_j) \right]$$

* $R$: Candidate set of retrieved chunks.
* $S$: Set of already selected chunks.
* $\lambda = 0.5$: Equal weighting between query relevance and candidate diversity.

#### 4. Semantic Centroid Drift & Incremental Update
In `SemanticChunker`, sentences are grouped into a chunk as long as cosine similarity against the chunk centroid remains above $\tau_{\text{sim}} = 0.7$. When sentence vector $v_{n}$ is added, the centroid $C_n$ updates incrementally without recomputing prior vectors:

$$C_n = \frac{n \cdot C_{n-1} + v_n}{n + 1}$$

$$\text{CosineSim}(v_{\text{next}}, C_n) = \frac{v_{\text{next}} \cdot C_n}{\|v_{\text{next}}\|_2 \, \|C_n\|_2}$$

* **Hard Split Threshold** ($\tau_{\text{hard}} = 0.4$): If $\text{Sim} < \tau_{\text{hard}}$, forces an immediate chunk split regardless of minimum chunk size limits.
* **Smoothing Margin** ($\epsilon = 0.05$): Eliminates split jitter when sentence similarity fluctuates near threshold boundaries.

#### 5. Information Retrieval & Evaluation Metrics Formulas
* **Precision@K**: Proportion of top-$K$ retrieved chunks that are relevant:
  $$\text{Precision@K} = \frac{\sum_{i=1}^K \text{rel}_i}{K}$$
* **Recall@K**: Proportion of total relevant candidates retrieved in top-$K$:
  $$\text{Recall@K} = \frac{\sum_{i=1}^K \text{rel}_i}{\sum_{j=1}^{M} \text{rel}_j} \quad (M = \text{total candidate pool size})$$
* **Hit Rate@K**: Binary indicator of whether at least one relevant chunk was retrieved:
  $$\text{Hit Rate@K} = \mathbb{I}\left(\sum_{i=1}^K \text{rel}_i > 0\right)$$
* **Reciprocal Rank (MRR)**: Reciprocal of the rank position of the first relevant chunk:
  $$\text{RR} = \frac{1}{\min \{i \mid \text{rel}_i = 1\}}$$
* **Mean Average Precision (MAP)**:
  $$\text{AP} = \frac{1}{\sum_{j=1}^M \text{rel}_j} \sum_{k=1}^K \text{Precision@k} \cdot \text{rel}_k$$
* **Normalized Discounted Cumulative Gain (NDCG@K)**:
  $$\text{DCG@K} = \sum_{i=1}^K \frac{\text{rel}_i}{\log_2(i + 1)}, \quad \text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$
* **Vector Diversity Score**: Measures informational spread across retrieved chunks:
  $$\text{Diversity} = 1.0 - \left( \frac{\frac{2}{K(K-1)} \sum_{i=1}^{K-1} \sum_{j=i+1}^K \text{CosineSim}(v_i, v_j) + 1.0}{2.0} \right)$$

---

### 2.4 System Failure Modes & Multi-Tier Resilience Matrix

In production, external APIs and local processes experience failures. The table below outlines how RAG Lab handles each failure condition:

| Subsystem | Potential Failure Mode | Root Cause | System Resilience & Fallback Strategy |
| :--- | :--- | :--- | :--- |
| **Ingestion** | Corrupted / Password-protected PDF | Malformed binary headers or missing credentials | Validates magic bytes (`%PDF-`) during upload; returns clean `400 Bad Request` before persisting. |
| **Ingestion** | Text layer missing (Scanned PDF) | Document consists entirely of images | Quality gate (`_pypdf_text_quality_ok`) detects insufficient text (<500 chars) and falls back to OCR via `pytesseract`. |
| **Chunking** | Oversized sentence segments | Malformed text lacking punctuation marks | Bounded sub-splitter (`SEMANTIC_MAX_SEGMENT_CHARS=2000`) forces character-length splits to prevent embedding token limit overflow. |
| **Embedding** | Remote API Gateway Timeout / 502 / 429 | NVIDIA NIM or Hugging Face rate limits / downtime | Exponential backoff retry loop (`max_retries=3`, $2^{\text{attempt}}$ sleep); falls back to secondary provider. |
| **Vector Store** | In-memory BM25 index lost | Worker container restart or process reboot | Automatically reconstructs BM25 index in $<5\text{ms}$ from persistent `{persist_dir}/bm25_{collection}.json`. |
| **Retrieval** | Similarity threshold excludes all chunks | Filter threshold too strict for given query | Safety fallback: if thresholding produces empty results, the system retains the top-$k$ unfiltered matches so the LLM still receives context. |
| **Reranking** | External Reranker API failure | Hugging Face inference router unavailable | Logs a warning and falls back to Stage-1 hybrid vector similarity scores without failing the request. |
| **LLM Generation** | Primary model reasoning hang / token leak | Nemotron-3.5 generating excessive thinking tokens | Supplies `enable_thinking: False`, enforces reasoning budget, and runs `_clean_answer_text()` regex sanitization. |
| **LLM Generation** | Primary LLM fails or hits API quota | Out of quota on NVIDIA NIM key | Cascading fallback: automatically invokes Groq (`openai/gpt-oss-120b`), then Gemini 2.5 Flash, then returns deterministic chunk excerpts. |
| **Evaluation** | Gateway timeout on multi-config comparison | Synchronous LLM judge calls taking >60s | Decouples deep evaluation behind `POST /compare/evaluate`; returns instant mathematical metrics in 0ms. |
| **Authentication** | Cross-origin third-party cookies blocked | Safari ITP or Chrome cookie restrictions | Dual-mode auth: checks `Authorization: Bearer <token>` header first, falling back to signed `HttpOnly` cookies. |
| **Database** | SQLite `database is locked` error | Concurrent write attempts across async tasks | Enables `PRAGMA journal_mode=WAL` with `busy_timeout=5000` and enforces short-lived session lifecycles. |

---

## 3. Deep Architectural Breakdown & Decision Comparison Matrices

### 3.1 Document Ingestion & Layout-Preserving Extraction

#### How It Works Under The Hood
When a document is uploaded via `POST /api/documents/upload`:
1. **Size & Security Validation**: Verifies file size against `MAX_UPLOAD_SIZE_MB` (default 50MB) and checks magic bytes (`b"%PDF-"`) to prevent malicious MIME-type spoofing.
2. **Storage Decoupling**: Large PDF binaries are saved to disk via `FileStorage` under an isolated UUID key (e.g., `uploads/{uuid}.pdf`), and stored in the database as a lightweight pointer (`pdf://{uuid}`). This prevents database bloat and memory exhaustion.
3. **Dual-Engine Extraction (`PDFStructureLoader` & `FileProcessor`)**:
   - `pdfplumber` analyzes page layouts, extracting table bounding boxes.
   - Cells are extracted, cleaned, and converted into Pandas DataFrames.
   - Multi-tier headers (common in scientific benchmark papers, e.g., metric names above CN/EN columns) are forward-filled and normalized.
   - The table is serialized into clean GitHub-flavored Markdown (`| Header 1 | Header 2 |\n| --- | --- |`).
   - Non-table text is extracted while preserving page boundaries and line breaks.
   - `pypdf` acts as a high-speed fallback if `pdfplumber` encounters parsing errors or complex encodings.
4. **Multimodal Visual Grounding (`PDFImageLoader` & `pypdf`)**:
   - **`pypdf` Detection**: When processing the PDF bytes, `PDFImageLoader` inspects `page.images` via `pypdf.PdfReader`. `pypdf` extracts raw image stream objects and binary data from the underlying PDF XObjects.
   - **Quality Filtering**: Uses PIL to check image geometry (`width`, `height`). Images smaller than $64 \times 64$ pixels (decorative spacers, tiny bullets, or logos) are skipped to avoid indexing visual noise.
   - **Caption Association**: Scans surrounding page text using regex patterns (e.g., `^(figure|fig\.|chart|diagram)\s*[\d.:]`) to capture relevant figure labels.
   - **Storage URI Decoupling**: Extracted images are saved to disk via `FileStorage` with unique keys, and assigned chunk text in the format:
     ```text
     [Figure 1 (Page 2)] Architecture diagram from system.pdf page 2
     image://{storage_key}
     ```
   - **Dual-Layer Indexing Strategy (`rag_pipeline.py`)**:
     * **Layer 1: Text-Based Grounding (Always Active)**: Regardless of CLIP configuration, the image chunk with its caption and figure title is indexed into the **primary text ChromaDB collection and BM25 index**. Textual queries (e.g., *"Show me Figure 1 on architecture"*) retrieve the image chunk using standard text embedders (Nemotron/MiniLM) and display the figure preview in the UI.
     * **Layer 2: True Multimodal CLIP Embedding (`PDF_IMAGE_INDEXING_ENABLED=true`)**: If enabled in `.env`, the pipeline activates `CLIPImageEmbedder` (`openai/clip-vit-base-patch32`). It loads the saved image bytes from disk using the `image://` URI and embeds the actual pixel data into a dedicated **sibling collection** (`{collection_name}_images`). Visual similarity queries project text queries directly into the joint visual-textual CLIP latent space, retrieving diagrams even when text captions are sparse or absent.

#### Thorough Comparison Matrix: Document Extraction Strategies

| Strategy | Speed / Latency | Table Integrity | Multimodal Support | Memory / Compute | Production Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dual-Engine (`pdfplumber` + `pypdf`)** *(Chosen)* | **Balanced** (~100–300ms/page) | **High** (Extracts table grids to clean Markdown) | **Yes** (Direct image extraction to CLIP) | **Moderate** (Pure Python, no heavy weights) | **Optimal balance of layout fidelity, table retention, and operational simplicity.** |
| **PyPDF / PyPDF2 Only** | **Ultra-Fast** (~20ms/page) | **None / Destroyed** (Merges cell text into inline strings) | Minimal (Extracts raw image streams without context) | Very Low | Unsuitable for financial, scientific, or tabular business documents. |
| **Unstructured / PyMuPDF4LLM** | Moderate (~400ms/page) | Good (Heuristic table detection) | Moderate | High (Heavier external C dependencies) | Strong alternative, but introduces complex system-level C++ library dependencies. |
| **OCR-Only (Tesseract / EasyOCR)** | **Very Slow** (~2–5s/page) | Poor to Fair (No native grid understanding) | None (Converts images to raw text) | High CPU/GPU | Necessary for scanned PDFs, but excessive overhead for digital vector PDFs. |
| **Vision-LLM Parsing (Nougat / ColPali / GPT-4o-V)** | **Extremely Slow** (>5s/page) | **Exceptional** (Perfect visual layout preservation) | Native | Very High ($$$ API cost or heavy GPU memory) | Cost-prohibitive for high-throughput multi-tenant indexing pipelines. |

---

### 3.2 Chunking Strategies & Boundary Optimization

A core strength of RAG Lab is supporting **six distinct chunking strategies**, allowing engineers to analyze chunking behavior under identical queries.

```
1. Fixed-Size:       [----- Chunk 1 -----]
                               [----- Chunk 2 -----]  (Constant character length + overlap)

2. Recursive:        [Paragraph 1]
                     [Paragraph 2 -----------------------------------]
                     (Splits on \n\n, then \n, then punctuation regex, then words)

3. Semantic:         [Sentence A. Sentence B.]  ---> [Cosine Sim Drops < 0.7] ---> [Sentence C. Sentence D.]
                     (Monitors semantic distance from rolling centroid vector)

4. Sentence-Window:  Index: [Center Sentence B]
                     Context expansion during generation: [Sentence A] + [Sentence B] + [Sentence C]
```

#### Detailed Strategy Breakdown:
1. **Fixed-Size Chunking (`FixedSizeChunker`)**: Splits by absolute character count (e.g., 512 chars) with fixed character overlap (e.g., 50 chars). 
   - *Pros*: Predictable vector memory footprint, zero computational overhead.
   - *Cons*: Cuts words, mid-sentence phrases, and breaks contextual ideas across chunk boundaries.
2. **Recursive Character Chunking (`RecursiveChunker`)**: Hierarchically splits using ordered separators: `["\n\n", "\n", r"(?<=[.!?])\s+", " "]`. If a segment exceeds `chunk_size`, it drops to the next granular separator. Includes whitespace-snapping overlap to prevent word truncation.
   - *Pros*: Preserves paragraphs and natural sentence boundaries.
   - *Cons*: Variable chunk sizes; can create undersized fragments if punctuation is dense.
3. **Semantic Chunking (`SemanticChunker`)**: Splits text into sentences, computes embeddings, and evaluates semantic drift. A chunk expands as long as the cosine similarity of incoming sentences against the **running chunk centroid** remains above `similarity_threshold` (e.g., 0.7). Supports `hard_split_threshold` (e.g., 0.4) for abrupt topic transitions and `smoothing_margin` (0.05) to eliminate edge jitter.
   - *Pros*: Every chunk represents an isolated, coherent semantic concept.
   - *Cons*: High indexing latency and cost (requires embedding every individual sentence during ingestion).
4. **Sentence-Window Chunking (`SentenceWindowChunker`)** *(The "Best-Preset" Winner)*: Indexes individual, small sentences (capped at 150 characters) as the search unit. However, each chunk stores a context window of $k$ surrounding sentences (`window_size=3` or `5`) in `chunk.metadata["window_text"]`.
   - *Pros*: Solves the fundamental RAG dilemma: **small chunks maximize retrieval precision** (no irrelevant noise in the vector), while **large chunks maximize LLM generation coherence** (the LLM receives full surrounding context).
   - *Cons*: Larger metadata memory footprint.
5. **Chapter/Section-Based Chunking (`ChapterChunker`)**: Splits on Markdown/document headers (`#`, `##`, `Chapter \d+`). Preserves entire thematic sections (up to `max_chunk_size=1024`).
   - *Pros*: Keeps end-to-end procedural steps intact.
   - *Cons*: Ineffective on documents without structural headers.
6. **Regex Chunking (`RegexChunker`)**: User-defined regular expressions (e.g., splitting on double line breaks, JSON boundaries, or log timestamps).
   - *Pros*: Ideal for semi-structured text and domain-specific log formats.

#### Thorough Comparison Matrix: Chunking Strategies

| Strategy | Indexing Speed | Retrieval Precision | Generation Grounding | Compute Cost | Best Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sentence-Window** *(Best Preset)* | **High** (Splits fast, single embed pass) | **Exceptional** (Pinpoints exact sentence) | **Exceptional** (Expanded window provides context) | Low | **General QA, Contracts, Legal & Compliance.** |
| **Recursive Character** | **Very High** | Moderate | Good | Very Low | Standard articles, blogs, markdown documentation. |
| **Semantic Centroid** | **Low** (Requires sentence-level embeddings) | High | High | High (Many embed calls) | Highly conceptual documents with shifting topics. |
| **Fixed-Size** | **Instantaneous** | Low to Moderate | Fair (Frequent chopped context) | None | Baseline benchmarking, low-resource environments. |
| **Chapter-Based** | High | Low (Chunks can be broad) | High (Full section context) | Very Low | Textbooks, manuals, API reference specifications. |

---

### 3.3 Embedding Models & Vector Spaces

RAG Lab supports heterogeneous embedding backends:
1. **Google Gemini Embeddings (`models/gemini-embedding-001`)** *(High-Dimension Preset)*:
   - 3072-dimensional rich dense vectors powered by Google DeepMind's Gemini embedding architecture via `langchain-google-genai`.
   - Generous free tier (up to 1,500 Requests Per Minute), providing immense semantic capacity and granular cluster separation for complex academic and technical documents.
2. **NVIDIA NIM (`nvidia/nemotron-3-embed-1b`)** *(Primary Enterprise Preset)*:
   - Modern 1-Billion parameter dense embedding model hosted on NVIDIA NIM high-performance microservices.
   - 1024-dimensional semantic representation with state-of-the-art MTEB retrieval performance.
   - Includes automatic retry handling with exponential backoff for gateway hiccups (502/429).
3. **Hugging Face (`sentence-transformers/all-MiniLM-L6-v2`) with In-Memory CPU Fallback**:
   - 384-dimensional dense vectors.
   - **402 Payment / Credit Resilience**: Attempts serverless inference via Hugging Face Inference API first. If Hugging Face returns `402 Payment Required` (serverless credits exhausted), the system transparently and seamlessly fails over to an in-memory local CPU `HuggingFaceEmbeddings` pipeline using `sentence-transformers`. This eliminates pipeline downtime and ensures zero-cost operation even with depleted cloud credits.
4. **Local CLIP (`openai/clip-vit-base-patch32`)**:
   - 512-dimensional shared multimodal vector space.
   - Projects both textual user queries and extracted visual images into the same vector space, enabling queries like *"Show me the architecture diagram"* to retrieve visual image chunks.

#### Batching & Concurrency Safeguard:
In `rag_pipeline.py`, page chunking is executed concurrently across CPU threads (`ThreadPoolExecutor(max_workers=3)`), but **all embedding calls are batched sequentially after chunking**. This architectural decision prevents saturating embedding API rate limits with simultaneous parallel bursts.

#### Thorough Comparison Matrix: Embedding Solutions

| Model / Provider | Dimensions | Local RAM Needed | Latency per 100 Chunks | MTEB Retrieval Rank | Production Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Gemini (`gemini-embedding-001`)** *(Deep Semantic)* | 3072 | 0 MB (Cloud API) | ~110ms | Top Tier | **Exceptional semantic resolution; generous 1500 RPM free tier.** |
| **NVIDIA Nemotron-3-Embed-1B** *(Chosen Enterprise)* | 1024 | 0 MB (Cloud NIM) | ~120ms | Top Tier | **Production standard for accuracy and enterprise semantic depth.** |
| **HF all-MiniLM-L6-v2** *(Chosen Fast / Local)* | 384 | 0 MB (API) / ~120MB (Local Fallback) | ~90ms | Moderate | **Optimal lightweight fallback; transparent CPU fallback survives 402 errors.** |
| **OpenAI text-embedding-3-small** | 1536 | 0 MB (API) | ~180ms | High | Commercial dependency; proprietary closed-source weights. |
| **Local BGE-Large / E5-Mistral** | 1024 / 4096 | 4 GB – 14 GB GPU | ~400ms (CPU) | Top Tier | Severe container memory overhead; crashes on small cloud instances. |

---

### 3.4 Vector Storage & Persistence Engine

#### Why ChromaDB?
RAG Lab implements `ChromaStore` wrapping `chromadb.PersistentClient`:
* **Zero External Dependencies**: Runs embedded in-process using SQLite metadata storage and local HNSW vector indices, eliminating the need to maintain an external vector database cluster during development and demonstration.
* **Namespace Isolation**: Dynamically creates isolated collections per user and configuration: `user_{user_id}_rag_cfg_{config_id}`.
* **Storage Protection**: The database files (`rag_lab.db`) and Chroma persistence directories are explicitly segregated to ensure vector index resets (`/compare/clear-chromadb`) never delete relational user accounts or chat histories.

#### Thorough Comparison Matrix: Vector Stores

| Vector Database | Architecture | Operational Complexity | Memory Footprint | Multi-Tenancy Mechanism | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ChromaDB (Embedded)** *(Chosen)* | Embedded In-Process (SQLite + HNSW) | **Zero** (Local directory) | Low (~100MB) | Discrete collection names | **Ideal for full-stack labs, local dev, and self-contained instances.** |
| **Qdrant (Embedded/Service)** | Rust binary / Client-Server | Low to Medium | Low to Moderate | Namespaced payload filtering | Supported as an alternate backend; excellent performance at scale. |
| **Pinecone** | Managed Cloud SaaS | Zero (Hosted) | Zero (Remote) | Namespaces | Vendor lock-in, recurring monthly costs, egress latency. |
| **Pgvector (PostgreSQL)** | Relational Extension (IVFFlat/HNSW) | Moderate (Requires Postgres instance) | Shared with DB | Row-level tenant partitioning | Excellent for unified relational+vector architectures at enterprise scale. |
| **FAISS (In-Memory)** | C++ Library Wrapper | Low | In-Memory (Volatile) | Manual index management | Lacks native persistence, metadata filtering, and CRUD update capabilities. |

---

### 3.5 Retrieval Strategies: Hybrid Convex Search & MMR

#### 1. Linear Convex Hybrid Fusion
Dense vector retrieval excels at conceptual similarity, but frequently fails on exact keywords, part numbers, and acronyms. Sparse search (BM25) excels at exact lexical matching, but fails at understanding synonyms.

RAG Lab combines both using **Linear Convex Fusion**:

$$S_{\text{hybrid}} = \alpha \cdot S_{\text{dense}} + (1 - \alpha) \cdot S_{\text{sparse}}$$

Where:
* $S_{\text{dense}}$ is the normalized cosine similarity score $[0, 1]$ from ChromaDB.
* $S_{\text{sparse}}$ is the normalized BM25 score $[0, 1]$ calculated across tokenized document chunks.
* $\alpha$ is the tunable balance parameter (default `0.7`). An $\alpha=0.7$ gives 70% weight to semantic conceptual meaning and 30% weight to exact keyword overlap.

```
Query: "Nemotron 3.5 latency benchmarks"
    │
    ├───> Dense Retriever (ChromaDB) ────> Score: 0.88 ───x 0.7 ───┐
    │                                                               ├───> Combined Score: 0.892 (Rank 1)
    └───> Sparse Retriever (BM25)     ────> Score: 0.92 ───x 0.3 ───┘
```

#### 2. Persistent BM25 Corpus Caching
A classic flaw in naive BM25 implementations is that the inverted index is held purely in RAM. When the backend server restarts, BM25 loses all chunks, requiring documents to be re-parsed.  
**RAG Lab Engineering Fix**: The tokenized BM25 corpus is serialized to `{CHROMA_PERSIST_DIR}/bm25_{collection_name}.json`. Upon server restart or pipeline initialization, the cache is instantly loaded from disk in $<5\text{ms}$.

#### 3. Maximal Marginal Relevance (MMR)
When enabled, MMR eliminates redundant chunks by balancing query relevance with candidate diversity:

$$\text{MMR} = \arg\max_{d_i \in R \setminus S} \left[ \lambda \cdot \text{Sim}_1(d_i, q) - (1 - \lambda) \max_{d_j \in S} \text{Sim}_2(d_i, d_j) \right]$$

Where $\lambda$ (default `0.5`) controls the penalty for selecting chunks that are near-duplicates of already selected chunks.

#### Thorough Comparison Matrix: Retrieval Fusion Strategies

| Retrieval Method | Keyword Accuracy | Synonym Handling | Latency Overhead | Cold Start Handling | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Convex Hybrid Search ($\alpha$-Weighted)** *(Chosen)* | **High** | **High** | Very Low (~10ms) | Instant (via persistent BM25 cache) | **Best production trade-off; allows granular tuning between semantic and lexical priority.** |
| **Dense Only** | Poor (Misses exact IDs) | High | Minimal (~15ms) | Instant | Fails in legal, technical, medical, and financial domains. |
| **Sparse (BM25 Only)** | High | None | Negligible (~3ms) | Requires tokenized corpus | Fails when users paraphrase concepts without using exact keywords. |
| **Reciprocal Rank Fusion (RRF)** | High | High | Low | Instant | Discards raw similarity confidence scores; treats rank 1 identically whether similarity is 0.99 or 0.51. |

---

### 3.6 Two-Stage Retrieval & Cross-Encoder Reranking

#### The Architecture of Two-Stage Retrieval
1. **Stage 1 (Bi-Encoder / Hybrid Retrieval)**: Fast, candidate generation. Retrieves $k_{\text{candidate}} = \max(2 \cdot \text{top\_k}, 6)$ chunks from ChromaDB and BM25. Bi-encoders process the query and document independently, making them fast but unable to model deep token-level cross-interactions.
2. **Stage 2 (Cross-Encoder Reranking)**: Precision reranking. Feeds the query and retrieved candidates together into a single cross-encoder model (`nvidia/nemotron-3.5-rerank-8b` via NVIDIA NIM, or local `cross-encoder/ms-marco-MiniLM-L-6-v2`). The cross-attention mechanism attends across every query token and document token simultaneously, generating a high-precision relevance score. The top $k$ items are returned.

#### Production Optimization & Candidate Gating:
If the candidate pool contains fewer than `min_candidates` (default 3), reranking is skipped to avoid unnecessary API network calls when candidate set quality is already unambiguous.

---

### 3.7 LLM Generation, Orchestration & Reasoning Control

#### 1. Generation Engine
* **Primary LLM**: **NVIDIA NIM** (`nvidia/nemotron-3.5-lightning-30b-a3b`). High speed, state-of-the-art context synthesis.
* **Evaluation & Fallback LLM**: **Groq API** (`openai/gpt-oss-120b` or `llama-3.3-70b-versatile`). Ultra-fast LPU inference (500+ tokens/sec).
* **Secondary Fallback**: **Google Gemini 2.5 Flash** via LangChain.

#### 2. The Nemotron Reasoning Suppression Architecture
Modern frontier models (e.g., Nemotron, DeepSeek R1, OpenAI o1/o3) generate extensive chain-of-thought "thinking" tokens before emitting the final answer. In RAG pipelines, this causes severe issues:
* **Latency Blowout**: Latency increases from 1.5 seconds to 30–60+ seconds.
* **Worker Timeouts**: Gunicorn and Uvicorn sync worker timeouts fire, dropping client connections.
* **UI Pollution**: Internal scratchpads and raw thoughts leak into the user's answer box.

**RAG Lab implements a Three-Layer Defense against Thinking Token Leakage**:
1. **API Parameter Suppression**: In `nvidia_client.py` and `compare_runner.py`, generation requests pass:
   ```python
   model_kwargs={"chat_template_kwargs": {"enable_thinking": False}}
   ```
2. **System Prompt Guardrails**: System instructions explicitly enforce:
   ```text
   CRITICAL: Do NOT output internal thoughts, reasoning steps, or "Here's a thinking process".
   Output ONLY the final, direct answer concisely.
   ```
3. **Resilient Regex Sanitizer (`_clean_answer_text`)**:
   ```python
   # Layer A: Strip explicit XML think blocks
   cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()

   # Layer B: Strip "Here's a thinking process:" preambles and capture conclusion
   if "Here's a thinking process:" in cleaned:
       m = re.search(r"(?:(?:Therefore|Final Answer:?|Conclusion:?)\s*[:\n]+)([\s\S]+)$", cleaned)
       if m: return m.group(1).strip()
   ```

#### 3. Dual-Mode Routing: Local Factoid vs Global Overview
Queries are classified via `classify_query(query)`:
* **Local Mode (Default)**: Questions like *"What was the Q3 operating margin?"* trigger hybrid retrieval and extract top-$k$ specific chunks.
* **Global Mode**: Questions like *"Summarize this document"* or *"What are the key takeaways?"* trigger document-level summarization. Summaries are cached in the `document_summaries` database table to eliminate redundant LLM calls on repeated broad queries.

---

### 3.8 Evaluation System: Real-Time Heuristics & Decoupled LLM-as-a-Judge

RAG Lab measures retrieval and generation quality using two decoupled tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: Instant Heuristic Evaluation (Calculated in 0ms, Zero LLM Overhead)            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Precision@K: Fraction of retrieved chunks judged relevant.                           │
│ • Recall@K: Fraction of total available relevant chunks retrieved.                     │
│ • Hit Rate@K: Binary indicator (1.0 if at least one relevant chunk is retrieved).      │
│ • Reciprocal Rank (MRR): 1 / rank of first relevant chunk.                             │
│ • Average Precision (MAP): Mean precision across all relevant rank positions.          │
│ • NDCG@K: Normalized Discounted Cumulative Gain accounting for position decay.         │
│ • Diversity Score: Pairwise cosine distance across retrieved chunk embedding vectors.  │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
               User clicks "Evaluation" Tab in Comparison Lab
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: On-Demand Decoupled LLM-as-a-Judge (Executed via Groq in Sub-Second JSON)      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Faithfulness (0.0 – 1.0): Groundedness of generated answer in retrieved chunks.      │
│ • Answer Relevancy (0.0 – 1.0): Direct responsiveness of answer to the user query.     │
│ • Context Recall (0.0 – 1.0): Coverage of query-essential facts by retrieved chunks.  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### The Single-Prompt Unified Evaluation Architecture
Earlier versions invoked the evaluator LLM multiple times sequentially: once for Faithfulness, once for Relevancy, and once for each chunk judgment. This required 5–8 LLM calls per configuration (up to 32 LLM calls for 4 configs), causing worker timeouts.

**RAG Lab consolidated this into a single unified JSON prompt** executed via Groq `gpt-oss-120b` with `response_format={"type": "json_object"}`:

```json
{
  "retrieved_relevance": [true, true, false, true],
  "candidate_relevance": [true, true, false, true, false, true],
  "faithfulness": 0.95,
  "answer_relevancy": 0.90,
  "context_recall": 0.85
}
```
*Result*: A single sub-second Groq call returns all heuristic judgments and qualitative metrics simultaneously.

#### Thorough Comparison Matrix: Evaluation Approaches

| Framework / Method | Latency | Cost | Failure Modes | Production Suitability |
| :--- | :--- | :--- | :--- | :--- |
| **RAG Lab Decoupled Architecture** *(Chosen)* | **<2s initial, ~800ms eval** | **Extremely Low** (Free Groq tier) | Graceful fallback to lexical heuristics | **Ideal for interactive user interfaces and benchmarking.** |
| **Inline Ragas Framework** | 45s – 120s | High (Multiple OpenAI calls) | Gateway timeouts, rate-limit crashes | Great for offline batch testing; unviable for real-time interactive web apps. |
| **Traditional Lexical Metrics (BLEU/ROUGE)** | Instant | Zero | Incapable of evaluating semantic factual grounding | Completely inadequate for assessing hallucinations in generative RAG. |

---

### 3.9 Multi-Tenancy, Security & Cross-Origin Auth

#### 1. Dual-Mode Authentication (Signed Cookies + Bearer Tokens)
RAG Lab supports both same-origin and cross-origin architectures (e.g., React frontend on Vercel connecting to FastAPI backend on Hugging Face Spaces):
* **Signed HttpOnly Cookies (`itsdangerous`)**: Cryptographically signs session cookies using `URLSafeTimedSerializer` with SHA-256 HMAC salt. Protects against client-side XSS token theft.
* **Bearer Authorization Header Fallback**: Because third-party browsers (Safari ITP, Chrome Privacy Sandbox) frequently block cross-site `Set-Cookie` headers between different domains, the authentication layer inspects the `Authorization: Bearer <token>` header if no cookie is present.
* **Password Hashing**: Industry-standard `bcrypt` with dynamic salt generation.

#### 2. Multi-Tenant Relational Isolation
All SQL models (`Document`, `RAGConfig`, `ChatMessage`, `EvaluationReport`) enforce foreign-key ownership via `user_id`:
```python
selected_stmt = select(Document).where(
    Document.id == document_id, 
    Document.user_id == current_user.id
)
```
No user can access, query, or delete another user's documents, vectors, or chat histories.

#### 3. Database-Backed Sliding-Window Rate Limiter
In-memory rate limiters (e.g., Python dictionaries or `slowapi`) fail when running multiple worker processes because state is not shared across processes.  
**RAG Lab's Solution**: `DatabaseRateLimiter` queries a persistent `rate_limit_events` table within a sliding 1-hour window:
* **LLM Calls**: 15 requests / hour
* **Embedding Calls**: 50 requests / hour
* **Retrieval Calls**: 100 requests / hour

---

### 3.10 Frontend Architecture & Real-Time SSE Streaming

#### 1. Real-Time Server-Sent Events (SSE) Protocol
Instead of waiting 3–8 seconds for an entire generation to finish, `/api/chat/stream` emits fine-grained SSE event packets:
1. `type: "status"`: Emits immediate indexing/retrieval status messages (*"Retrieving relevant chunks..."*).
2. `type: "metadata"`: Emits full retrieved chunk data, similarity scores, and image URLs **before generation begins**. The UI renders interactive citation cards and figure previews instantly.
3. `type: "token"`: Emits generated words token-by-token for smooth, typing-style rendering.
4. `type: "done"`: Emits the persisted `message_id`, unlocking interactive evaluation tools in the drawer.

#### 2. React 19 Error Boundary Resilience
A root `ErrorBoundary` component intercepts unhandled React runtime errors, displaying contextual recovery options rather than crashing into a blank white screen.

---

## 4. Engineering War Stories & Production Bottlenecks Solved

These real scenarios provide concrete examples to share when interviewers ask: *"Tell me about a difficult technical bug you solved."*

### War Story 1: The Multi-Config Gateway Timeout Crisis
* **The Symptom**: When running 4 configurations in `/compare/run`, Hugging Face Spaces and Vercel threw `504 Gateway Timeout` errors. Backend logs revealed Uvicorn worker timeouts after 60 seconds.
* **The Root Cause**: `/compare/run` executed generation and 32 separate LLM judge calls sequentially inside a single request. 4 configurations $\times$ 8 evaluations per config overwhelmed the worker thread.
* **The Engineering Fix**:
  1. Decoupled evaluation from `/compare/run`. The comparison query computes instant lexical/mathematical metrics in 0ms and returns the answer in $<2\text{s}$.
  2. Gated deep evaluation behind a separate endpoint: `POST /compare/evaluate`. It triggers lazily **only when the user clicks the "Evaluation" tab**.
  3. Consolidated evaluation into a single unified JSON prompt executed on Groq's high-speed LPU infrastructure.

### War Story 2: The Nemotron Internal Thought Leak
* **The Symptom**: Switching generation to NVIDIA Nemotron-3.5 improved answer quality, but answer cards were cluttered with internal thinking monologues:
  ```text
  Here's a thinking process:
  1. Analyze user request...
  2. Inspect chunk 1...
  Final Answer: The operating revenue was $15.2M.
  ```
  Additionally, generation latency spiked to over 30 seconds.
* **The Root Cause**: Reasoning models allocate hundreds of tokens to internal chain-of-thought scratchpads before emitting the user-facing text.
* **The Engineering Fix**:
  1. Passed `chat_template_kwargs={"enable_thinking": False}` directly to NVIDIA NIM endpoints.
  2. Added defensive system prompts instructing the model to output final answers directly.
  3. Built `_clean_answer_text()`, a regex sanitizer that scrubs `<think>...</think>` tags and strips thought preambles, extracting only the verified conclusion.

### War Story 3: Cross-Origin Cookie Rejection in Distributed Cloud Deployments
* **The Symptom**: When the React frontend was deployed on Vercel (`https://raglab.vercel.app`) and the backend on Hugging Face Spaces (`https://madhesh-rag-lab.hf.space`), login succeeded but every subsequent request returned `401 Unauthorized`.
* **The Root Cause**: Modern browsers block cross-domain third-party cookies by default unless configured with `SameSite=None; Secure`. However, when running on `http://localhost`, `SameSite=None` without `Secure` is rejected by browsers.
* **The Engineering Fix**:
  1. Implemented environment-aware cookie configuration (`_cookie_settings()` in `auth.py`). It sets `SameSite=Lax` for local HTTP and `SameSite=None; Secure=True` for HTTPS production environments.
  2. Updated the frontend API client (`api.js`) to store the returned session token in memory and attach it as a standard `Authorization: Bearer <token>` header on every request, providing reliable authentication across domains.

### War Story 4: The In-Memory BM25 Corpus Wipe
* **The Symptom**: After restarting the backend container, dense retrieval worked normally, but hybrid search performance degraded, and logs warned: `BM25 has no indexed chunks — falling back to dense-only retrieval`.
* **The Root Cause**: ChromaDB persisted vectors to disk, but `rank-bm25` held its inverted word index in volatile Python memory.
* **The Engineering Fix**:
  Engineered disk serialization in `sparse_retriever.py`. Following indexing, the tokenized corpus is saved to `{CHROMA_PERSIST_DIR}/bm25_{collection_name}.json`. During initialization, the file is read and the BM25 index is reconstructed in $<5\text{ms}$ without requiring document re-extraction.

### War Story 5: Table Corruption in Financial and Scientific PDFs
* **The Symptom**: In benchmark evaluation papers, queries asking for specific model metrics returned hallucinations or incorrect numbers.
* **The Root Cause**: Traditional PDF loaders extract text streams in reading order, flattening tables into continuous strings. Two-tier headers (e.g., metric name above language columns) merged into unparsable tokens.
* **The Engineering Fix**:
  Constructed `pdf_table_extractor.py` using `pdfplumber`. It isolates table grid lines, loads cells into a DataFrame, forward-fills multi-tier hierarchical headers, and serializes the grid into a Markdown table. During chunking, Markdown tables are preserved as indivisible units.

---

## 5. Complete Step-by-Step Execution Walkthroughs

### 5.1 Document Upload & Multi-Stage Indexing Pipeline
```
[User Selects PDF] 
       │
       ▼
[POST /api/documents/upload]
       │
       ├── 1. Verify Magic Bytes (%PDF-) & File Size (<50MB)
       ├── 2. Save raw bytes to disk (uploads/{uuid}.pdf) -> Pointer: pdf://{uuid}
       ├── 3. Extract text pages via PDFStructureLoader (pypdf + pdfplumber)
       ├── 4. Detect tables -> Reconstruct as GitHub Markdown
       ├── 5. Extract images -> Save to disk (image://{key})
       └── 6. Insert Document row in SQLite/Postgres scoped to user_id
```

### 5.2 Real-Time SSE Streaming Query Execution
```
[User Types Query: "What were the Q3 margins?"]
       │
       ▼
[POST /api/chat/stream]
       │
       ├── 1. Verify Rate Limit (DatabaseRateLimiter: 15 LLM calls/hr)
       ├── 2. Query Classifier -> Determine "local" vs "global" summary
       ├── 3. Hybrid Retrieval:
       │      ├── Dense Search: ChromaDB vector cosine distance
       │      ├── Sparse Search: BM25 disk-cached inverted index
       │      └── Linear Convex Fusion: Score = 0.7·Dense + 0.3·Sparse
       ├── 4. Cross-Encoder Reranking: Nemotron-3.5-Rerank-8B scores top candidates
       ├── 5. Emit SSE Event: {"type": "metadata", "chunks": [...]} (Citations appear in UI)
       ├── 6. NVIDIA Nemotron-3.5 Generation (enable_thinking=False):
       │      └── Emit SSE Events: {"type": "token", "content": "The..."}
       ├── 7. Persist User & Assistant ChatMessage rows + Record PipelineTimer metrics
       └── 8. Emit SSE Event: {"type": "done", "message_id": "..."}
```

### 5.3 Parallel Multi-Configuration Benchmarking Lab
```
[User Stages Config A (Fixed) and Config B (Sentence-Window)]
       │
       ▼
[POST /compare/run]
       │
       ├── Validate: 1 to 4 configurations staged
       ├── asyncio.gather(*[run_single_config(cfg) for cfg in configs]):
       │      ├── Execute hybrid search across config-specific Chroma collections
       │      ├── Measure latency using PipelineTimer (chunk, embed, retrieve, llm)
       │      ├── Execute generation via cached LLM client
       │      ├── Clean thought traces via regex sanitizer
       │      └── Compute 0ms instant heuristic metrics (P@K, R@K, Hit Rate, MRR, NDCG)
       └── Return CompareResponse in <2 seconds (Zero worker timeouts)
```

### 5.4 On-Demand Decoupled Evaluation Lifecycle
```
[User clicks "Evaluation" tab in Comparison Lab]
       │
       ▼
[POST /compare/evaluate]
       │
       ├── Check if results already contain deep evaluations (Skip if present)
       ├── Run evaluate_comparison_results concurrently:
       │      └── Execute single unified JSON prompt on Groq GPT-OSS-120B:
       │             ├── Evaluate Faithfulness (Answer grounded in retrieved chunks)
       │             ├── Evaluate Answer Relevancy (Answer addresses question)
       │             └── Evaluate Context Recall (Chunks cover necessary information)
       └── Update UI with side-by-side metric leader badges (Grounding Leader, Speed Leader)
```

---

## 6. The 25 Ultimate Technical Interview Questions & Answers

Use these questions and model answers to prepare for technical interviews.

---

### Category 1: RAG Architecture & System Design

#### Q1: Walk me through the architecture of your RAG platform. What problem does it solve?
> **Answer**:  
> RAG Lab is an engineering platform designed to systematically benchmark and optimize RAG pipelines. Traditional RAG systems suffer from three common issues: table structure loss during ingestion, inability to balance keyword versus semantic retrieval, and worker timeouts caused by synchronous evaluation.  
> 
> The platform is built around a modular architecture:
> 1. **Ingestion**: A dual-engine pipeline (`pdfplumber` + `pypdf`) preserves tables as Markdown and extracts figures for multimodal CLIP indexing.
> 2. **Chunking**: Supports six strategies, highlighted by a Sentence-Window chunker that decouples retrieval precision from generation context.
> 3. **Retrieval**: Uses linear convex hybrid search combining dense ChromaDB embeddings with disk-cached BM25, followed by cross-encoder reranking.
> 4. **Generation**: Powered by NVIDIA Nemotron-3.5 with thinking suppression and Groq fallbacks.
> 5. **Evaluation**: Features an on-demand, decoupled evaluation architecture that calculates instant heuristics in 0ms and runs deep LLM-as-a-judge metrics via Groq upon tab selection.

---

#### Q2: Why did you choose Sentence-Window chunking as your "Best Preset" default over standard recursive character chunking?
> **Answer**:  
> Standard chunking creates a fundamental tradeoff: **small chunks (100–200 characters) maximize retrieval precision** because vector embeddings represent a single, focused semantic thought without dilution. However, small chunks starve the LLM of necessary context during generation. Conversely, **large chunks (1000+ characters) provide ample context for generation**, but dilute vector similarity and introduce irrelevant noise.  
> 
> Sentence-Window chunking resolves this conflict:
> - **Index Phase**: Individual sentences (capped at 150 characters) are embedded and stored as the retrievable unit.
> - **Generation Phase**: When a sentence chunk is retrieved, the pipeline accesses `chunk.metadata["window_text"]`, which expands the context to include $k$ surrounding sentences ($k=3$ or $5$).  
> The vector search operates with high precision, while the LLM receives the full surrounding context needed for coherent generation.

---

#### Q3: What is the "Lost-in-the-Middle" problem in RAG, and how does your architecture address it?
> **Answer**:  
> The "Lost-in-the-Middle" phenomenon (Liu et al.) describes the tendency of language models to recall information placed at the very beginning or end of long context prompts much more effectively than information located in the middle.  
> 
> RAG Lab mitigates this through three strategies:
> 1. **Cross-Encoder Reranking**: Re-orders candidate chunks so that the most relevant chunks are placed at the top of the context window.
> 2. **Context Compaction**: `_build_context()` limits context to the top-8 chunks or 12,000 characters, filtering out marginal content that dilutes attention.
> 3. **Structured Context Delimiters**: Chunks are injected with clear headers (e.g., `[Chunk 1]`, `[Figure 1 (Page 2)]`), helping the attention mechanism anchor specific factual references.

---

#### Q4: How does your system handle broad summarization queries versus specific factoid queries?
> **Answer**:  
> Standard vector similarity struggles with broad queries like *"Summarize this document"* because nearest-neighbor search looks for specific passage matches rather than global themes.  
> 
> RAG Lab uses a **Query Classifier**:
> - If classified as **Local**: The query executes standard hybrid retrieval and returns top-$k$ passages.
> - If classified as **Global**: The pipeline routes to `SummaryService`. It retrieves high-centrality anchor chunks or loads a pre-computed document overview from the `document_summaries` table. This approach delivers comprehensive document summaries without requiring full-document context stuffing.

---

#### Q5: Why did you implement a side-by-side comparison lab rather than relying solely on automated offline evaluations?
> **Answer**:  
> Automated aggregate metrics (e.g., Mean Reciprocal Rank, Average Precision) are valuable across large test suites, but they obscure qualitative nuances that engineers need to evaluate when tuning pipelines.  
> 
> The Comparison Lab allows engineers to stage up to four configurations simultaneously and run identical queries to observe:
> - Retrieval differences (e.g., how Sentence-Window compares to Fixed-Size on a specific table).
> - Latency breakdowns across each pipeline stage (`PipelineTimer`).
> - Qualitative answer differences side-by-side.  
> This empirical feedback loop helps teams dial in chunk sizes, similarity thresholds, and $\alpha$ fusion weights with high confidence.

---

### Category 2: Information Retrieval, Indexing & Math

#### Q6: Explain the mathematics behind your Hybrid Search. Why linear convex combination over Reciprocal Rank Fusion (RRF)?
> **Answer**:  
> RAG Lab calculates hybrid retrieval using Linear Convex Fusion:  
> 
> $$S_{\text{hybrid}} = \alpha \cdot S_{\text{dense}} + (1 - \alpha) \cdot S_{\text{sparse}}$$  
> 
> Where $S_{\text{dense}}$ is normalized cosine similarity, $S_{\text{sparse}}$ is min-max normalized BM25 score, and $\alpha \in [0, 1]$ (default 0.7).  
> 
> While Reciprocal Rank Fusion (RRF) is popular in search engines ($S_{\text{RRF}} = \sum \frac{1}{60 + \text{rank}}$), it discards raw similarity margins. For example, if a vector match has a high similarity score of 0.98, RRF treats it identically to a weak match of 0.51 if both happen to be ranked first. Linear convex combination preserves these relative score margins, allowing genuine semantic confidence to influence the final ranking.

---

#### Q7: How does BM25 work, and why does it complement dense vector embeddings?
> **Answer**:  
> BM25 (Best Matching 25) is a probabilistic bag-of-words ranking algorithm that scores documents based on query term frequency ($TF$) and inverse document frequency ($IDF$), normalized by document length:  
> 
> $$\text{Score}(D, Q) = \sum_{q \in Q} IDF(q) \cdot \frac{TF(q, D) \cdot (k_1 + 1)}{TF(q, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$  
> 
> Dense embeddings map words into continuous latent spaces. They excel at identifying conceptual synonyms (e.g., mapping "canine" to "dog"), but struggle with exact token matches like part numbers, error codes (`ERR-404`), or acronyms. BM25 directly scores exact lexical overlap, ensuring domain-specific keywords and identifiers are retrieved reliably.

---

#### Q8: What is Maximal Marginal Relevance (MMR), and when should it be used over standard similarity search?
> **Answer**:  
> Standard vector retrieval returns the top-$k$ nearest neighbors. If a document discusses the same topic across multiple paragraphs, the top results often contain near-duplicate information, wasting context window budget.  
> 
> MMR solves this by balancing relevance to the query with diversity among selected chunks:  
> 
> $$\text{MMR} = \arg\max_{d_i \in R \setminus S} \left[ \lambda \cdot \text{Sim}_1(d_i, q) - (1 - \lambda) \max_{d_j \in S} \text{Sim}_2(d_i, d_j) \right]$$  
> 
> By setting $\lambda=0.5$, MMR penalizes chunks that are too similar to already-selected chunks, maximizing informational diversity across the retrieved context.

---

#### Q9: What is the difference between a Bi-Encoder and a Cross-Encoder? Why not use Cross-Encoders for initial retrieval?
> **Answer**:  
> - **Bi-Encoder**: Processes the query and document independently into fixed-dimensional vectors ($u = f(q)$, $v = f(d)$). Similarity is computed via dot product or cosine distance. Because document embeddings can be pre-computed and indexed into an HNSW graph, search across millions of documents executes in milliseconds. However, it cannot model token-level interactions between the query and text.
> - **Cross-Encoder**: Feeds the query and document together into a transformer ($[CLS] + q + [SEP] + d$). Full cross-attention attends across every query token and document token simultaneously. This yields higher relevance accuracy, but requires running a forward pass on every document pair at query time.  
> Running a cross-encoder across thousands of documents is computationally infeasible. We use a **two-stage architecture**: the Bi-Encoder/Hybrid search rapidly generates a candidate pool ($k=10$), and the Cross-Encoder reranks only those top candidates.

---

#### Q10: How do you handle PDF table extraction without scrambling layout structure?
> **Answer**:  
> Traditional text extractors parse characters sequentially based on coordinates, which flattens table columns into continuous strings and destroys structural relationships.  
> 
> RAG Lab uses a specialized pipeline:
> 1. `pdfplumber` analyzes table line geometry to identify cell boundaries.
> 2. Cell text is extracted into rectangular grids and converted to Pandas DataFrames.
> 3. Two-tier or hierarchical headers (e.g., metric names above language columns) are detected and forward-filled.
> 4. Clean Markdown tables are constructed (`| Metric | CN | EN |\n|---|---|---|`).  
> Ingesting tables as Markdown preserves row-column relationships so LLMs can reason over tabular data accurately.

---

#### Q10B: How does multimodal visual retrieval work in RAG Lab? Does `pypdf` trigger this, and what is the dual-layer indexing strategy?
> **Answer**:  
> Yes, `pypdf` is the primary engine that detects and extracts raw image objects from the PDF document structure.  
> 
> Here is how the complete multimodal lifecycle works:
> 1. **Detection & Extraction (`PDFImageLoader`)**: `pypdf.PdfReader` inspects `page.images` across every page, extracting raw binary streams from the PDF's internal XObjects.
> 2. **Noise Filtering**: PIL checks image dimensions. Decorative icons, spacers, and tiny logos under $64 \times 64$ pixels are discarded to avoid vector store noise.
> 3. **Caption Matching**: The page text is regex-scanned to associate surrounding figure titles (e.g., `Figure 1: Architecture Overview`).
> 4. **Dual-Layer Indexing Strategy**:
>    - **Layer 1: Text-Based Grounding (Always Active)**: The image chunk (containing caption, title, and storage URI `image://{key}`) is indexed into the **primary text ChromaDB collection and BM25 index**. Text queries like *"What does Figure 1 describe?"* immediately match the caption and retrieve the figure preview in the UI without requiring GPU vision models.
>    - **Layer 2: True Multimodal CLIP Embedding (`PDF_IMAGE_INDEXING_ENABLED=true`)**: If multimodal indexing is enabled, the actual image pixels are embedded using local CLIP (`openai/clip-vit-base-patch32`) into a dedicated **sibling collection** (`{collection}_images`). A user query (e.g., *"neural network diagram"*) is projected into CLIP's joint visual-textual latent space, allowing the system to retrieve diagrams based on visual features even when text captions are absent.

---

### Category 3: Production Latency, Scalability & Concurrency

#### Q11: How did you resolve the gateway timeout issue in the Comparison Lab when staging multiple pipelines?
> **Answer**:  
> Running 4 pipelines in parallel originally triggered 60-second gateway timeouts because each pipeline executed retrieval, generation, and multiple deep LLM evaluation calls sequentially inside one request.  
> 
> We resolved this through three architectural changes:
> 1. **Decoupled Evaluation**: `/compare/run` computes instant mathematical metrics (Precision@K, Recall@K, Hit Rate, MRR, NDCG) in 0ms and returns the answer in $<2\text{s}$.
> 2. **Lazy On-Demand Evaluation**: Deep LLM-as-a-judge metrics are moved behind `POST /compare/evaluate`, which executes only when the user selects the "Evaluation" tab.
> 3. **Unified Evaluation Prompting**: Replaced multiple sequential judge calls with a single unified JSON prompt executed on Groq's high-speed inference engine.

---

#### Q12: Why did you choose Server-Sent Events (SSE) over WebSockets or standard REST for streaming chat answers?
> **Answer**:  
> - **Standard REST**: Buffers the entire generated response on the server, forcing the user to wait 3–8 seconds before seeing any text.
> - **WebSockets**: Bi-directional communication is unnecessary for chat responses, introduces stateful connection overhead, and complicates load balancing across reverse proxies and serverless environments.
> - **Server-Sent Events (SSE)** *(Chosen)*: Operates over standard HTTP, supports automatic reconnection, and bypasses proxy firewall restrictions. It allows the server to stream:
>   1. Immediate status updates (`type: status`).
>   2. Retrieved chunk metadata and image URLs (`type: metadata`), rendering citations before generation starts.
>   3. Streamed generation tokens (`type: token`) for smooth, real-time rendering.

---

#### Q13: How is latency instrumented across your pipeline? What bottlenecks did your measurements expose?
> **Answer**:  
> RAG Lab uses `PipelineTimer` to record execution timestamps across every stage:
> - `chunking_time_ms`
> - `embedding_time_ms`
> - `retrieval_time_ms`
> - `reranking_time_ms`
> - `llm_time_ms`
> - `total_time_ms`  
> 
> This instrumentation exposed two major production bottlenecks:
> 1. **Cross-Encoder API Latency**: Reranking 20 candidates via external APIs added 1.2 seconds of overhead. We introduced candidate gating (`min_candidates=3`) to skip reranking when candidate quality was already clear.
> 2. **Reasoning Token Latency**: Unconstrained reasoning models spent up to 30 seconds generating chain-of-thought tokens. Disabling thinking mode reduced generation latency from 30s to 1.4s.

---

#### Q14: How does your system prevent worker thread starvation during document indexing?
> **Answer**:  
> Large document ingestion (extracting text, parsing tables, running CLIP image models, and computing embeddings) is computationally heavy and blocks the main event loop if executed synchronously.  
> 
> We implemented asynchronous background jobs:
> 1. When a user requests indexing, `POST /api/chat/prepare` registers a unique job ID via `IndexingJobStore` and schedules execution on FastAPI's `BackgroundTasks` queue.
> 2. The endpoint returns an immediate `202 Accepted` response with the job ID.
> 3. The frontend polls `GET /api/documents/index-status/{job_id}`, updating progress indicators without holding an HTTP connection open or blocking other requests.

---

#### Q15: Why is persistent caching necessary for BM25, and how did you implement it?
> **Answer**:  
> In standard implementations, BM25 indices reside purely in Python process memory. When a container restarts or scales horizontally, the index is lost, and the system falls back to dense-only search until documents are re-indexed.  
> 
> To solve this, `sparse_retriever.py` serializes the tokenized corpus to `{CHROMA_PERSIST_DIR}/bm25_{collection_name}.json`. During pipeline initialization, the system checks for this file and reconstructs the BM25 index in $<5\text{ms}$, ensuring zero loss of hybrid retrieval capabilities across server restarts.

---

### Category 4: LLMs, Reasoning Control & Evaluation Rigor

#### Q16: How do you prevent reasoning models (like Nemotron or DeepSeek) from leaking internal chain-of-thought tokens into user answers?
> **Answer**:  
> Reasoning models use internal scratchpads that inflate latency and clutter user interfaces. We use a three-tier suppression strategy:
> 1. **Model Kwargs**: Pass `{"chat_template_kwargs": {"enable_thinking": False}}` directly in the API payload.
> 2. **System Prompts**: Enforce strict formatting instructions: *"Do NOT output internal thoughts, reasoning steps, or 'Here's a thinking process'. Output ONLY the final answer."*
> 3. **Regex Sanitization**: A post-processing utility (`_clean_answer_text`) uses regular expressions to strip `<think>...</think>` tags and catch "Here's a thinking process:" preambles, returning only the final verified conclusion.

---

#### Q17: How do you measure Faithfulness without relying on human annotations?
> **Answer**:  
> Faithfulness measures whether the generated answer is strictly grounded in the retrieved context, guarding against hallucinations.  
> 
> We evaluate this through an automated LLM-as-a-judge prompt:
> 1. The evaluator receives the retrieved context chunks and the generated answer.
> 2. The model breaks the answer down into individual factual claims.
> 3. It verifies whether each claim can be directly inferred from the context.
> 4. The score is computed as:  
>    $$\text{Faithfulness} = \frac{\text{Number of Context-Supported Claims}}{\text{Total Claims in Answer}}$$  
> If an evaluator is unavailable, the system falls back to a lexical overlap heuristic comparing token co-occurrence between the answer and context.

---

#### Q18: What is Answer Relevancy, and how does it differ from Faithfulness?
> **Answer**:  
> - **Faithfulness** measures **factual consistency with context** (ensuring the model doesn't hallucinate facts outside the provided documents). An answer can be completely faithful while entirely irrelevant (e.g., Question: *"What was Tesla's revenue?"* -> Answer: *"Tesla makes electric cars."* The statement is grounded, but does not answer the question).
> - **Answer Relevancy** measures **responsiveness to the user query**. It assesses whether the generated response directly addresses what was asked, without introducing incomplete explanations or tangents.

---

#### Q19: Why use Groq for evaluation instead of running the primary generation model as its own judge?
> **Answer**:  
> 1. **Latency**: Groq's LPU architecture delivers inference speeds exceeding 500 tokens/second, completing deep multi-dimensional evaluations in under one second.
> 2. **Self-Enhancement Bias**: Using the same model to both generate and evaluate an answer introduces self-preference bias, where models consistently rate their own outputs higher than those of other models. Using an independent model (Groq `gpt-oss-120b`) ensures objective evaluation.
> 3. **Structured Output**: Groq reliably adheres to strict JSON schemas (`response_format={"type": "json_object"}`), preventing JSON parsing errors in the evaluation pipeline.

---

#### Q20: How does your evaluation system compute Recall@K without ground-truth labeled benchmark datasets?
> **Answer**:  
> In open-ended production RAG where human-annotated ground truth is unavailable, standard recall cannot be computed against a known universal answer key.  
> 
> RAG Lab uses a **Judged Candidate Pool Approach**:
> 1. The system evaluates the broader candidate pool of retrieved chunks ($k=10$ or $20$).
> 2. The evaluator LLM (or heuristic fallback) labels each candidate chunk as relevant or non-relevant to the query.
> 3. `Recall@K` is then calculated as the proportion of total relevant candidate chunks that successfully made it into the top-$k$ context window:  
>    $$\text{Recall@K} = \frac{\text{Relevant Chunks in Top K}}{\text{Total Relevant Chunks in Candidate Pool}}$$  
> This measures whether the retrieval and reranking stages successfully surfaced the best available context into the top-$k$ positions.

---

### Category 5: Security, Multi-Tenancy & Edge Cases

#### Q21: How do you achieve true multi-tenancy and data isolation in ChromaDB and SQLite?
> **Answer**:  
> Multi-tenancy is enforced across every layer of the platform:
> 1. **Relational Database**: All SQL entities (`Document`, `RAGConfig`, `ChatMessage`, `EvaluationReport`) include a foreign-key relationship to `user_id`. Queries enforce ownership checks: `where(Document.id == doc_id, Document.user_id == current_user.id)`.
> 2. **ChromaDB Vector Store**: Vector collections are partitioned by user ID and configuration ID: `user_{user_id}_rag_cfg_{config_id}`.
> 3. **Filesystem**: Document binaries are stored under user-scoped UUIDs, preventing directory traversal attacks or unauthorized file access.

---

#### Q22: Why did you implement a dual-mode authentication scheme (Cookies + Bearer Header)?
> **Answer**:  
> When the frontend and backend are deployed across different domains (e.g., frontend on Vercel and backend on Hugging Face Spaces), modern browser security policies (Safari ITP, Chrome third-party cookie restrictions) often block cross-site `Set-Cookie` headers.  
> 
> To ensure reliable authentication:
> 1. The backend issues cryptographically signed `HttpOnly` session cookies using `itsdangerous`.
> 2. On login, the backend also returns the session token in the JSON response payload.
> 3. The frontend stores this token and includes it as an `Authorization: Bearer <token>` header on subsequent requests.
> 4. `get_current_user()` checks the `Authorization` header first, falling back to the session cookie if the header is absent. This ensures seamless operation in both local and distributed cloud deployments.

---

#### Q23: Why is database-backed rate limiting superior to in-memory rate limiting (like slowapi) in production?
> **Answer**:  
> In-memory rate limiters track request counters within the memory space of a single Python process. In production environments where FastAPI runs with multiple worker processes (e.g., `uvicorn --workers 4` or Gunicorn), request counters are not shared across workers. A user could exceed their rate limit by hitting different worker processes.  
> 
> RAG Lab's `DatabaseRateLimiter` queries a persistent `rate_limit_events` table in SQLite/PostgreSQL, evaluating request counts within a sliding 1-hour window. This ensures consistent, accurate rate limits across all worker processes.

---

#### Q24: What happens if an uploaded PDF is corrupt or contains scanned images without selectable text?
> **Answer**:  
> The ingestion pipeline uses a layered fallback approach:
> 1. `FileProcessor` validates magic bytes (`%PDF-`) to confirm the file is a valid PDF.
> 2. If `PDFStructureLoader` fails to extract selectable text using `pdfplumber`, it falls back to `pypdf`.
> 3. If extracted text volume falls below quality thresholds (`_pypdf_text_quality_ok`), the system marks the document for OCR processing via `pytesseract` and extracts embedded image figures using `PDFImageLoader`.
> 4. If text extraction fails entirely, the error is caught gracefully, allowing the user to inspect the failure without crashing backend workers.

---

#### Q25: How did you prevent SQLite database lock errors and async concurrency issues when running under high load?
> **Answer**:  
> SQLite can encounter `database is locked` errors during concurrent writes in async applications. We resolved this through four database configurations:
> 1. **WAL Mode**: Enabled Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), allowing concurrent readers without blocking writers.
> 2. **Busy Timeout**: Configured `PRAGMA busy_timeout=5000;`, allowing queries to wait up to 5 seconds for write locks to clear before failing.
> 3. **Scoped Sessions**: Endpoints create short-lived database sessions (`async with AsyncSessionLocal() as db`) rather than sharing long-lived connections across async tasks.
> 4. **Greenlet Isolation**: Primary user attributes (like `admin_user.id`) are accessed synchronously before `await` calls, preventing SQLAlchemy `MissingGreenlet` exceptions during async execution.

---

## 7. Quick Reference: System Configuration Cheatsheet

| Parameter | Recommended Default | Purpose |
| :--- | :--- | :--- |
| `chunk_strategy` | `sentence_window` | Maximizes retrieval precision while preserving generation context |
| `window_size` | `5` | Includes center sentence + 2 prior sentences + 2 subsequent sentences |
| `max_chunk_size` | `150` | Maximum character length for retrievable sentence units |
| `embedding_provider` | `nvidia` | NVIDIA AI Endpoints (`nvidia/nemotron-3-embed-1b`) |
| `retrieval_type` | `hybrid` | Combines dense vector search and sparse BM25 |
| `alpha` | `0.7` | 70% weight to dense semantic similarity, 30% weight to BM25 keyword matching |
| `reranker_enabled` | `True` | NVIDIA `nemotron-3.5-rerank-8b` cross-encoder reranking |
| `top_k` | `4` | Final number of chunks delivered to generation context |
| `rerank_fetch_k` | `6` to `8` | Candidate pool size retrieved prior to reranking |
| `llm_provider` | `nvidia` | NVIDIA NIM (`nemotron-3.5-lightning-30b-a3b`) |
| `evaluator_llm` | `groq` | Groq LPU (`openai/gpt-oss-120b` JSON Mode) |
| `enable_thinking` | `False` | Suppresses reasoning tokens to maintain $<2\text{s}$ generation latency |

---
*Created as part of the RAG Lab production engineering documentation. All metrics, architectural patterns, and code implementations reference the active `RAG_LAB` codebase.*
