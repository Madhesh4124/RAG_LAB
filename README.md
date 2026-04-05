# RAG Lab

RAG Lab is a full-stack playground for building, tuning, and comparing Retrieval-Augmented Generation (RAG) pipelines on your own documents.

It includes:
- A FastAPI backend for document processing, indexing, chat, evaluation, and metrics.
- A React + Vite frontend with a guided setup wizard, chunk preview, compare mode, and chat UI.

## What Is Implemented Today

### Core workflow
1. Upload a document (`.pdf` or `.txt`).
2. Configure a pipeline in a step-by-step wizard.
3. Save config and preview generated chunks.
4. Chat with streaming responses.
5. Compare multiple retrieval/indexing configs side-by-side.
6. Score/evaluate responses and inspect performance metrics.

### Setup wizard
- 5-step flow: Upload, Chunking, Embedding, Retrieval, LLM & Memory.
- Presets: `fast`, `balanced`, `accurate`, `recursive`, `chapter`, `sentence_window`.
- Chunking strategies in UI:
  - `fixed_size`
  - `recursive`
  - `semantic`
  - `chapter_based`
  - `regex`
  - `sentence_window`
- Embedding providers in UI:
  - NVIDIA
  - Hugging Face
- Retrieval modes:
  - `dense`
  - `sparse`
  - `hybrid`
  - `mmr`
- Reranker toggle and model selection (Hugging Face API reranker).
- LLM selection is fixed to Gemma in UI (`gemma-4-26b-a4b-it`).
- Memory modes:
  - `none`
  - `buffer`
  - `summary`

### Chunk preview
- Visualizes chunks for a selected document + saved config.
- Shows chunk order, ranges, and overlap metadata.

### Chat
- Streaming chat endpoint (`/api/chat/stream`) with status, metadata, token stream, done events.
- Stores user/assistant messages.
- Stores timing/quality metrics per assistant message.
- Auto-evaluation hook for faithfulness/relevancy/context metrics (best-effort).
- System reset endpoint to clear cache/history/vector storage.

### Compare mode
- Uses dedicated compare module endpoints (`/compare/index`, `/compare/run`, `/compare/clear-chromadb`).
- Supports staging up to 4 configs.
- Supports all compare chunking strategies and chunk hyperparameters.
- Supports embedding provider/model selection in compare config modal (NVIDIA + Hugging Face model sets).
- Per-config indexing status in cards and staging panel.
- Staging panel shows a filling progress bar while a config is indexing.

### Evaluation and analytics
- Message-level evaluation endpoint with:
  - `faithfulness`
  - `answer_relevancy`
  - `context_precision`
  - `context_recall`
- Analysis endpoint includes:
  - ranked chunks
  - score distribution
  - chunk diversity
  - timing breakdown
- Metrics summary endpoint returns:
  - per-config aggregates
  - per-query rows

## Project Structure

```text
RAG_LAB/
  backend/
    app/
      api/                # /api routes (documents, chat, config, analysis, evaluation, metrics, legacy compare)
      compare/            # dedicated compare module routes/services (/compare/*)
      services/           # chunking, embedding, retrieval, memory, llm, pipeline
      models/             # SQLAlchemy models
      utils/              # file processing, serialization, timing
      main.py
    requirements.txt
  frontend/
    src/
      pages/              # Setup, Preview, Compare, Chat
      components/         # config wizard, compare UI, chat UI, preview UI
      hooks/
      services/api.js
    package.json
  README.md
```

## Backend API (Current)

### Health
- `GET /`
- `GET /health`

### Documents (`/api/documents`)
- `POST /upload`
- `GET /{doc_id}`
- `GET /{doc_id}/chunks?config_id=...`
- `DELETE /{doc_id}`

### Config (`/api/config`)
- `POST /`
- `GET /list`
- `GET /{config_id}`
- `GET /{config_id}/export`
- `POST /import`

### Chat (`/api/chat`)
- `POST /`
- `POST /stream`
- `GET /history/{doc_id}`
- `POST /reset`

### Analysis / Evaluation / Metrics
- `GET /api/analysis/{message_id}`
- `POST /api/evaluation/score`
- `POST /api/evaluation/faithfulness` (alias)
- `GET /api/metrics/summary?document_id=...`

### Compare module (`/compare`)
- `POST /index`
- `POST /run`
- `POST /clear-chromadb`

Note: a legacy compare route also exists at `/api/compare`, but the current Compare page uses `/compare/*`.

## Data and Persistence

- Relational data: SQLite via SQLAlchemy models.
- Vector storage: Chroma persisted under project directories (compare flow uses its own store).
- Stored entities include documents, configs, chat messages, evaluations, and metrics.

## Environment Variables

Set only what you need for selected providers/features.

### Common
- `CHROMA_PERSIST_DIR` (optional)

### LLM
- `GOOGLE_API_KEY` or `GEMINI_API_KEY` (Gemma via Google GenAI)

### Embeddings
- `NVIDIA_API_KEY` (NVIDIA embeddings)
- `HUGGINGFACE_API_KEY` (Hugging Face Inference API fallback/client)
- `GOOGLE_API_KEY` (if Google embedding provider is used in backend configs)

### Analysis (optional)
- `ANALYSIS_CONFIDENCE_THRESHOLD` (default `0.5`)

## Local Development

## Prerequisites
- Python 3.10+
- Node.js 18+
- npm

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# or .venv\Scripts\activate     # Windows PowerShell/CMD
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend default URL: `http://localhost:8000`

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`

If needed, set `VITE_API_URL` in the frontend environment to point to your backend.

## API Rate Limiting

RAG Lab implements per-user rate limiting to prevent API quota exhaustion:

### Limits (1-hour rolling window)

| Feature | Limit | Configurable Via |
|---------|-------|-----------------|
| LLM Calls | 15 per hour | `MAX_LLM_CALLS_PER_HOUR` |
| Embedding Calls | 50 per hour | `MAX_EMBEDDING_CALLS_PER_HOUR` |
| Retrieval Calls | 100 per hour | `MAX_RETRIEVAL_CALLS_PER_HOUR` |

- **LLM Calls**: Each chat query counts as 1 call (~1 call every 4 minutes at default limit)
- **Embedding Calls**: Document indexing and embedding operations
- **Retrieval Calls**: Vector store search operations

When rate limit is exceeded, users receive a `429 Too Many Requests` error and must wait for the 1-hour window to reset.

## Notes and Practical Tips

- First run for new Hugging Face models can be slow due to model resolution and warm-up logs.
- `307` redirects and some `404` checks in model hub logs are usually normal during model discovery.
- Compare indexing is config-specific; run `Run & Save Configs` before querying compare results.
- For large documents and semantic chunking, indexing time can be noticeably higher than fixed-size chunking.

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy
- Chroma
- LangChain ecosystem components
- Google GenAI integration

### Frontend
- React
- Vite
- Tailwind CSS
- React Router
- Axios

## License

MIT
