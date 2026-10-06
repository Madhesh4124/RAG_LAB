---
title: RAG Lab
emoji: 🔬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🔬 RAG Lab

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2%2B-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.0%2B-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4%2B-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**RAG Lab** is a full-stack, multi-tenant engineering platform for designing, benchmarking, tuning, and evaluating **Retrieval-Augmented Generation (RAG)** pipelines across complex documents (PDFs, Markdown, text).

Unlike toy RAG implementations, RAG Lab provides an end-to-end experimentation and evaluation suite:
* **Hybrid Search**: Linear convex fusion ($\alpha \cdot \text{dense} + (1-\alpha) \cdot \text{sparse}$) combining dense vector embeddings (ChromaDB) and disk-cached BM25 sparse keyword indices.
* **Document Extraction**: Dual-engine PDF parsing (`pdfplumber` + `pypdf`) preserving tabular layouts as Markdown and extracting diagrams/figures for CLIP multimodal indexing.
* **Model Orchestration**: Generation via **NVIDIA NIM** (`nemotron-3.5-lightning-30b-a3b`) with chain-of-thought suppression, cascading fallbacks (Gemini 2.5 Flash), and ultra-fast evaluation via **Groq** (`gpt-oss-120b`).
* **Side-by-Side Comparison Lab**: Stage up to 4 arbitrary pipeline configurations simultaneously, running parallel retrieval benchmarks with sub-2s response latencies.
* **On-Demand LLM-as-a-Judge**: Decoupled deep evaluation (Faithfulness, Answer Relevancy, Context Recall) executed lazily upon tab selection to eliminate backend worker timeouts.
* **Production Security**: Multi-tenant database isolation, signed HttpOnly cookies + cross-origin Bearer token auth, database-backed rate limiting, and React 19 error boundaries.

---

## 📸 Overview & Operational Modes

RAG Lab features three core workspaces accessible from the **Mode Selection** dashboard:

```
                                 ┌───────────────────────────────────┐
                                 │       Select Workspace Mode       │
                                 └─────────────────┬─────────────────┘
                                                   │
         ┌─────────────────────────────────────────┼────────────────────────────────────────┐
         ▼                                         ▼                                        ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌───────────────────────────────┐
│     ⚡ Quick Chat             │ │    🛠️ Custom Pipeline          │ │     ⚖️ Comparison Lab         │
│ Instant QA with automated     │ │ 5-step granular wizard:       │ │ Benchmark up to 4 RAG configs │
│ "Best-Preset" embeddings &    │ │ chunk sizes, overlap, vector  │ │ in parallel side-by-side with │
│ streaming SSE responses.      │ │ stores & reranker models.     │ │ response & latency diffs.     │
└───────────────────────────────┘ └───────────────────────────────┘ └───────────────────────────────┘
```

1. **⚡ Quick Chat (`/chat`)**: Rapid document Q&A. Upload single or multi-document sets, automatically initialize best-preset embeddings, and stream responses token-by-token with real-time SSE, interactive citation cards, and session history.
2. **🛠️ Custom Pipeline Architect (`/setup`)**: 5-step wizard to configure and fine-tune every layer:
   - **Chunking**: Fixed-size, Recursive Character, Semantic, Regex, and Sentence-Window (with window expansion).
   - **Embedding**: NVIDIA (`nvidia/nemotron-3-embed-1b`), Hugging Face (`all-MiniLM-L6-v2`), or Google Gemini.
   - **Vector Store & Hybrid Retrieval**: ChromaDB with cosine distance + Rank-BM25 sparse retriever with tunable $\alpha$ fusion weight.
   - **Rerankers**: BAAI BGE-Reranker-v2-m3 via Hugging Face API or local cross-encoders.
   - **Generation**: NVIDIA Nemotron-3.5, Gemini 2.5 Flash, or Groq with customizable temperature and max turns.
3. **⚖️ Comparison Lab (`/compare`)**: Stage up to 4 configurations simultaneously. Run identical queries to inspect answer differences, retrieval overlap, similarity distributions, and per-stage latency decompositions.
4. **📊 Evaluation Drawer**: Slide-out evaluation panel computing instant heuristic metrics (Precision@K, Recall@K, Hit Rate, Average Similarity) and on-demand deep LLM-as-a-Judge metrics (Faithfulness, Answer Relevancy, Context Recall).

---

## 🏗️ Architecture

```
[ User Browser / React 19 Frontend (Vercel) ]
                │
                │ HTTP / Server-Sent Events (SSE)
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FastAPI Backend Application (AsyncIO / Hugging Face Spaces)            │
│                                                                        │
│ ┌────────────────────────┐  ┌────────────────────────────────────────┐ │
│ │ Security & Auth Engine │  │ Database-Backed Rate Limiting Guard     │ │
│ │ • Signed session token │  │ • Rolling 1-hr window on LLM,           │ │
│ │ • Bcrypt hash storage  │  │   embedding, and retrieval calls        │ │
│ └────────────────────────┘  └────────────────────────────────────────┘ │
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Multi-Stage Document Ingestion & Chunking Worker                   │ │
│ │ • Dual-engine PDF extraction (pdfplumber table-preservation)       │ │
│ │ • CLIP image extraction & multimodal visual citation indexing      │ │
│ │ • BackgroundTasks queue with job polling (zero UI blocking)        │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ ┌────────────────────────┐  ┌────────────────────────────────────────┐ │
│ │ Vector & Sparse Stores │  │ LLM Orchestration & Evaluation Engine  │ │
│ │ • ChromaDB (Persistent)│  │ • Generation: NVIDIA Nemotron-3.5       │ │
│ │ • Disk-Cached BM25     │  │ • Evaluation: Groq (GPT-OSS-120B JSON)  │ │
│ └────────────────────────┘  └────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features & Innovations

* **Table Extraction & Markdown Formatting**: PDF tables are detected, structured, and serialized as clean GitHub-flavored Markdown tables, ensuring financial, scientific, and benchmark tables remain intact during chunking.
* **Multimodal Visual Retrieval**: PDF diagrams, charts, and figures are extracted, persisted to disk, and embedded using CLIP into sibling vector collections for visual grounding.
* **Instant Comparison & Lazy Evaluation**: `/compare/run` executes in parallel via `asyncio.gather` in $\sim 1\text{--}3\text{s}$ using instant lexical/mathematical metrics. Deep LLM evaluations (Faithfulness, Relevancy) run lazily on demand when switching to the **Evaluation** tab via `POST /compare/evaluate`.
* **Zero Chain-of-Thought Leakage**: Explicit system role isolation and template kwargs (`{"enable_thinking": False}`) coupled with regex sanitizers ensure reasoning tokens from reasoning models (e.g., Nemotron) never leak into generated answers.
* **Persistent BM25 Caching**: BM25 tokenized corpora are persisted to `{CHROMA_PERSIST_DIR}/bm25_{collection_name}.json` on disk, allowing instant recovery across server restarts without re-extracting documents.
* **Latency Decomposition**: `PipelineTimer` instruments every execution phase into explicit milliseconds:
  - `chunking_time_ms`
  - `embedding_time_ms`
  - `retrieval_time_ms`
  - `reranking_time_ms`
  - `llm_time_ms`
  - `total_time_ms`
* **Enterprise Security & Multi-Tenancy**:
  - Full relational isolation via `user_id` foreign keys on all SQL entities (`Document`, `RAGConfig`, `ChatMessage`, `EvaluationReport`).
  - Cryptographically signed session tokens (`itsdangerous`) with `HttpOnly`, `SameSite`, and `Secure` cookie options, plus Bearer token support for cross-origin deployments.
  - Database-backed rate limiting across workers (15 LLM calls/hr, 50 embedding calls/hr, 100 retrieval calls/hr).
* **React 19 Frontend Resilience**:
  - Full Vite 8 + React 19 single-page architecture.
  - Root `ErrorBoundary` component ensuring runtime render failures display graceful recovery actions instead of blank/black screens.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (AsyncIO, Pydantic v2, Gunicorn + Uvicorn)
- **Database**: SQLite (WAL mode, single-worker safety) / PostgreSQL with SQLAlchemy & Alembic
- **Vector Storage**: ChromaDB (`chromadb`)
- **Sparse Retrieval**: Rank-BM25 with disk-persisted corpus caches
- **LLM Integrations**: NVIDIA NIM (`ChatNVIDIA`), Groq API (`ChatGroq`), Google Gemini (`ChatGoogleGenerativeAI`)
- **Document Extractors**: `pdfplumber`, `pypdf`, `Pillow`, `pdf2image`, `pytesseract`

### Frontend
- **Framework**: React 19 + Vite 8
- **Styling**: Tailwind CSS 3.4 (Zinc & amber terminal theme)
- **Routing**: React Router DOM v7
- **Networking**: Axios & Native Fetch with Server-Sent Events (SSE) streaming
- **Icons**: Custom SVG icon suite (`Icons.jsx`)
- **Testing**: Vitest + React Testing Library + jsdom

---

## ⚡ Quick Start (Local Development)

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**

---

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/Madhesh4124/RAG_LAB.git
cd RAG_LAB/backend

# Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux / macOS / Git Bash:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `backend/.env` with your API keys:
```env
AUTH_SECRET_KEY=generate-a-secure-random-string
FRONTEND_URL=http://localhost:5173
COOKIE_SECURE=false
COOKIE_SAMESITE=lax

# LLM & Embedding Providers
NVIDIA_API_KEY=your_nvidia_api_key
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
HUGGINGFACE_API_KEY=your_huggingface_api_key
```

Run the backend server:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Backend API will be live at `http://127.0.0.1:8000` (Swagger docs at `http://127.0.0.1:8000/docs`).

---

### 2. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Frontend will be live at `http://localhost:5173`.

---

### 3. Demo Credentials

The platform is pre-seeded with quick-access demo accounts for testing:

| Username / Email | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `sample` / `sample@local` | `sample` | User | Default standard user with pre-loaded demo sessions |

*(You can also click the **"Fill demo"** button on the `/login` screen to populate credentials instantly).*

---

## 🐳 Running with Docker

You can run the containerized backend directly:

```bash
docker build -t rag-lab-backend .
docker run -p 7860:7860 --env-file backend/.env rag-lab-backend
```

Or spin up the full stack via Docker Compose:
```bash
docker compose up --build
```

---

## 📡 Key API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/signup` | Register new user account |
| `POST` | `/api/auth/login` | Authenticate user & issue signed session cookie / bearer token |
| `GET` | `/api/auth/me` | Fetch active user profile and role |
| `POST` | `/api/documents/upload` | Upload `.pdf` or `.txt` document |
| `GET` | `/api/documents/list` | List user's isolated documents |
| `GET` | `/api/documents/index-status/{job_id}` | Poll background indexing job progress |
| `POST` | `/api/config/best-preset/apply` | Automatically configure and apply best preset |
| `POST` | `/api/chat/prepare` | Queue document background indexing for chat session |
| `POST` | `/api/chat/stream` | Real-time SSE streaming answer generation |
| `GET` | `/api/chat/history/{doc_id}` | Retrieve persisted document conversation history |
| `POST` | `/compare/run` | Execute fast parallel multi-config comparison query |
| `POST` | `/compare/evaluate` | Run lazy on-demand LLM-as-a-judge evaluation across configs |
| `POST` | `/compare/clear-chromadb` | Reset comparison collections to free storage space |

---

## 🧪 Testing

```bash
# Run backend test suite
cd backend
python -m pytest

# Run frontend test suite
cd ../frontend
npm test
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
