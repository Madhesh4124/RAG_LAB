---
title: RAG Lab
emoji: 🔬
colorFrom: blue
colorTo: indigo
sdk: docker
sdk_version: latest
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

**RAG Lab** is a full-stack, multi-tenant engineering platform for building, tuning, evaluating, and benchmarking **Retrieval-Augmented Generation (RAG)** pipelines across real-world documents.

Unlike toy RAG implementations, RAG Lab provides a full experimentation suite: hybrid search (BM25 sparse + dense vector embeddings), async background indexing, side-by-side pipeline comparison, automated best-preset tuning, evaluation metrics (Faithfulness & Answer Relevancy), and multi-tenant session authentication.

---

## 📸 Overview & Operational Modes

RAG Lab features three distinct operational workspaces accessible from the **Mode Selection** dashboard:

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

1. **⚡ Quick Chat (`/chat`)**: Rapid document Q&A. Select or upload PDF/TXT documents, automatically configure best-practice embedding presets, and chat with real-time Server-Sent Events (SSE) token streaming, citation inspectors, and session history.
2. **🛠️ Custom Pipeline Architect (`/setup`)**: Complete step-by-step wizard for tuning:
   - Chunking strategies: Fixed size, Recursive, Semantic, Chapter-based, Regex, and Sentence-window.
   - Embedding providers: NVIDIA (`nvidia/nemotron-3-embed-1b`), Hugging Face, Google.
   - Vector stores & Hybrid search: Dense embeddings + BM25 keyword matching with MMR (Maximal Marginal Relevance).
   - Custom rerankers & LLM parameters (Gemini, Groq LLaMA 3.3).
3. **⚖️ Comparison Lab (`/compare`)**: Stage up to 4 pipeline configurations simultaneously. Run identical queries to inspect retrieval diffs, similarity score distributions, latency profiles, and token metrics.
4. **📊 Evaluation & Metrics Drawer**: Slide-out evaluation panel computing both fast statistical metrics (Precision@K, Recall@K, MRR, nDCG, Hit Rate) and deep LLM-as-a-Judge metrics (Faithfulness, Answer Relevancy, Context Precision).

---

## 🏗️ Architecture

```
[ User Browser / React 19 Frontend ]
                │
                │ HTTP Requests / SSE Streaming (with HttpOnly Session Cookie)
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FastAPI Backend Application (AsyncIO)                                  │
│                                                                        │
│ ┌────────────────────────┐  ┌────────────────────────────────────────┐ │
│ │ Security & Auth Engine │  │ Rate Limiting & Scope Guard             │ │
│ │ • Signed session token │  │ • Rolling 1-hr window on LLM,           │ │
│ │ • Bcrypt hash storage  │  │   embedding, and retrieval calls        │ │
│ └────────────────────────┘  └────────────────────────────────────────┘ │
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Asynchronous Document Ingestion & Chunking Worker                  │ │
│ │ • PyPDF / Text / OCR / Image extractors                            │ │
│ │ • BackgroundTasks queue with job polling (zero UI blocking)        │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ ┌────────────────────────┐  ┌────────────────────────────────────────┐ │
│ │ Vector & Sparse Stores │  │ LLM & Retrieval Engine                 │ │
│ │ • ChromaDB (Persistent)│  │ • Gemini 2.5 Flash / Groq LLaMA 3.3     │ │
│ │ • BM25 In-Memory Cache │  │ • Hybrid Reranking & Context Assembly   │ │
│ └────────────────────────┘  └────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

* **Multi-Format Ingestion**: Supports `.pdf` and `.txt` files with intelligent multi-page extraction, table handling, and optional OCR / CLIP image embeddings.
* **Non-Blocking Background Indexing**: Asynchronous job queue (`IndexingJobStore`) returns an immediate `job_id` and reports progress percentages, eliminating HTTP timeouts during large document indexing.
* **Hybrid Search Engine**: Integrates ChromaDB dense embeddings with a cached BM25 sparse keyword retriever, balancing semantic nuance with exact keyword matching.
* **Automated Best-Preset Selection**: Heuristically selects optimal chunk sizes, overlaps, and models based on uploaded document metrics and character density.
* **LLM-as-a-Judge Evaluation Suite**:
  * **Faithfulness**: Validates whether answers are derived strictly from retrieved context (hallucination detection).
  * **Answer Relevancy**: Penalizes redundant or off-topic responses.
  * **Context Precision & Recall**: Evaluates retrieval rank quality and coverage.
* **Enterprise Security & Rate Limiting**:
  * Cryptographically signed `HttpOnly` session cookies with auto-detecting local/cloud security flags.
  * Per-user hourly rate limiting on LLMs (15/hr), embeddings (50/hr), and retrieval calls (100/hr) with automated email alerts on threshold breach.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (AsyncIO, Pydantic v2)
- **Database**: SQLite (local) / PostgreSQL with SQLAlchemy & Alembic migrations
- **Vector Storage**: ChromaDB (`chromadb`)
- **Sparse Retrieval**: Rank-BM25
- **LLM Integrations**: Google Gemini API (`gemini-2.5-flash`), Groq API (`llama-3.3-70b-versatile`)
- **Document Processing**: `pypdf`, `pdfplumber`, `pdf2image`, `pytesseract`

### Frontend
- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS (Dark zinc & amber design system)
- **Routing**: React Router DOM v7
- **Networking**: Axios & Native Fetch with Server-Sent Events (SSE)
- **Icons**: Lucide-inspired SVG icon system

---

## ⚡ Quick Start (Local Development)

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**

---

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/your-username/rag-lab.git
cd rag-lab/backend

# Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
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

# Providers (Provide at least one)
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
NVIDIA_API_KEY=your_nvidia_api_key
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

The platform is pre-seeded with quick-access demo accounts for local testing:

| Username / Email | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `sample` / `sample@local` | `sample` | User | Default standard user with pre-loaded demo sessions |


*(You can also click the **"Fill demo"** button on the `/login` screen to populate credentials instantly).*

---

## 🐳 Running with Docker Compose

You can spin up the full stack in a containerized environment:

```bash
docker compose up --build
```

The frontend will be exposed on port `5173` and the backend on port `8000`.

---

## 📡 API Reference Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate user & issue signed session cookie |
| `GET` | `/api/auth/me` | Fetch active user profile and role |
| `POST` | `/api/documents/upload` | Upload `.pdf` or `.txt` document |
| `GET` | `/api/documents/list` | List uploaded user documents |
| `GET` | `/api/documents/index-status/{job_id}` | Poll background indexing job progress |
| `POST` | `/api/config/best-preset/apply` | Automatically configure and apply best preset |
| `POST` | `/api/chat/prepare` | Queue document background indexing for chat |
| `POST` | `/api/chat/stream` | Real-time SSE streaming answer generation |
| `GET` | `/api/chat/history/{doc_id}` | Retrieve persisted document conversation history |
| `POST` | `/compare/run` | Execute multi-config parallel benchmark query |
| `POST` | `/api/evaluation/report` | Compute statistical & LLM-as-a-judge quality metrics |

---

## 🧪 Testing

```bash
# Run backend test suite
cd backend
pytest

# Run frontend tests
cd ../frontend
npm test
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
