# 🔬 RAG Lab – Retrieval-Augmented Generation Experimentation Platform

> A comprehensive experimentation platform for optimizing and tuning Retrieval-Augmented Generation (RAG) pipelines. Compare chunking strategies, embeddings, retrievers, and LLM configurations all in one place.

---

## 🎯 Problem & Solution

### The Problem
Building production-grade RAG systems is complex and unintuitive. Teams face critical challenges:
- **Too many variables**: How do you choose between semantic chunking vs. fixed-size chunking? Which embedding model performs best? Sparse vs. dense vs. hybrid retrieval?
- **No experimentation tools**: Testing different configurations requires manual coding, making A/B comparisons time-consuming and error-prone
- **Black-box pipelines**: Limited visibility into retrieval quality, chunk relevance, and performance bottlenecks
- **Config management**: Saving, comparing, and exporting configurations is ad-hoc

### The Solution
**RAG Lab** is an interactive experimentation platform that:
✅ Allows you to configure and test RAG pipelines visually  
✅ Compares multiple configurations side-by-side on the same query  
✅ Provides real-time chunk previews and performance metrics  
✅ Supports multiple chunking strategies, embedders, retrievers, and LLMs  
✅ Exports/imports configurations for reproducibility  
✅ Helps you find the optimal RAG setup for your documents  

---

## 🚀 Key Features

### 1. **Document Upload & Processing**
- Upload PDF, TXT, DOCX, and other document formats
- Automatic text extraction and preprocessing
- Support for large documents with efficient processing

### 2. **Configurable RAG Pipeline**
Customize every component of your RAG stack:

**Chunking Strategies:**
- `semantic` – Chunks based on semantic similarity
- `fixed_size` – Fixed token/character-length chunks with overlap
- `chapter_based` – Splits on document structure (chapters, sections)
- `recursive` – Hierarchical splitting for nested structure
- `regex` – Custom regex-based splitting

**Embedding Models:**
- Google Embeddings
- HuggingFace API Embeddings
- NVIDIA Embeddings
- Local HuggingFace embeddings

**Retrieval Methods:**
- `dense` – Vector similarity search (semantic)
- `sparse` – BM25/TF-IDF keyword matching
- `hybrid` – Combines dense + sparse for best of both worlds

**LLM Providers:**
- Google Gemini (with configurable model variants)
- Extensible for additional providers

**Memory Types:**
- `buffer_memory` – Standard sliding window memory
- `summary_memory` – Summarizes older messages to preserve context

**Vector Stores:**
- ChromaDB – Lightweight, embedded vector database
- FAISS – Scalable similarity search
- Extensible for additional vector stores

### 3. **Chunk Visualization & Preview**
- See exactly how your document is chunked before running queries
- Visualize chunk boundaries and metadata
- Understand chunking strategy impact in real-time

### 4. **Configuration Comparison**
- Test the same query across multiple RAG configurations
- Side-by-side comparison of:
  - Retrieved chunks
  - Similarity scores
  - LLM responses
  - Performance metrics (retrieval time, embedding time, etc.)
- Identify which configuration works best for your use case

### 5. **Performance Analytics**
Track performance breakdown:
- **Chunking Time** – How long document processing takes
- **Embedding Time** – Vector generation latency
- **Retrieval Time** – Database query performance
- **LLM Time** – Model inference latency
- **Total Time** – End-to-end pipeline latency

### 6. **Configuration Management**
- Save configurations to database
- Export to JSON for sharing/backup
- Import previously saved configurations
- Default presets for quick setup

---

## 🏗️ Architecture

### Backend (FastAPI)
```
backend/
├── app/
│   ├── api/                    # REST API endpoints
│   │   ├── documents.py        # Upload, retrieve, preview chunks
│   │   ├── chat.py             # Query & RAG pipeline execution
│   │   ├── config.py           # Configuration CRUD + import/export
│   │   ├── compare.py          # Multi-config comparison
│   │   └── analysis.py         # Metrics & performance analysis
│   ├── services/               # Core RAG pipeline logic
│   │   ├── rag_pipeline.py     # Main RAG orchestration
│   │   ├── pipeline_factory.py # Create pipelines from config
│   │   ├── chunking/           # Text chunking strategies
│   │   ├── embedding/          # Embedding providers
│   │   ├── retrieval/          # Retrieval implementations
│   │   ├── vectorstore/        # Vector database adapters
│   │   ├── llm/                # LLM client implementations
│   │   └── memory/             # Context memory management
│   ├── models/                 # SQLAlchemy database models
│   ├── database.py             # SQLAlchemy setup
│   └── main.py                 # FastAPI app initialization
└── requirements.txt
```

### Frontend (Vite + React)
```
frontend/
├── src/
│   ├── pages/                  # Main application pages
│   │   ├── Setup.jsx           # Document upload + config wizard
│   │   ├── Preview.jsx         # Chunk visualization
│   │   └── Compare.jsx         # Multi-config comparison
│   ├── components/
│   │   ├── config/             # Configuration wizard flow
│   │   ├── upload/             # Document upload UI
│   │   ├── preview/            # Chunk visualization
│   │   └── comparison/         # Config comparison UI
│   ├── hooks/                  # React custom hooks
│   ├── services/               # API client
│   └── main.jsx
└── vite.config.js
```

### Data Storage
- **Database**: SQLite (default, upgradeable to PostgreSQL)
- **Vector Store**: ChromaDB (embedded) or FAISS
- **Documents**: Stored in database
- **Configurations**: JSON stored in database for versioning

---

## 🎨 UI/UX Features & Future Ideas

### Current Features
1. **Setup Page**
   - Drag-and-drop document upload
   - Step-by-step configuration wizard
   - Real-time validation and error handling

2. **Preview Page**
   - Visual chunking visualization with boxes/cards
   - Chunk metadata display (size, similarity, position)
   - Search highlighting in chunks
   - Query-to-chunk relevance scoring

3. **Compare Page**
   - Multi-config selection
   - Side-by-side result display
   - Query input with live comparison
   - Performance metrics comparison table

### 💡 Future UI Enhancements

#### Analytics Dashboard
- **Pipeline Performance Graph** - Visualize latency breakdown (chunking, embedding, retrieval, LLM times)
- **Chunk Distribution Chart** - Histogram of chunk sizes, word counts
- **Retrieval Quality Heatmap** - Show how many top-k results had high similarity scores
- **Configuration Performance Leaderboard** - Rank all saved configs by metrics

#### Advanced Visualization
- **Chunk Dependency Graph** - Show how chunks relate to each other (for chapter-based splitting)
- **Embedding Space Visualization** - 2D/3D UMAP/TSNE projection of embedded chunks
- **Query-Chunk Similarity Matrix** - Heatmap showing similarity scores for all retrieved chunks
- **Retrieval Pipeline Flow Diagram** - Visual representation of how documents flow through the pipeline

#### Experimentation Features
- **A/B Testing Mode** - Run same queries 100x and compare statistical significance
- **Parameter Search Assistant** - Suggest optimal chunk_size, top_k, etc. based on initial runs
- **Batch Query Testing** - Upload multiple queries and compare all configs at once
- **Dataset Management** - Save multiple documents and run cross-document tests

#### UX Improvements
- **Configuration Templates** - Pre-built templates for common use cases (legal docs, technical papers, news articles)
- **Dark Mode** - Reduce eye strain for extended experimentation sessions
- **Real-time Streaming Responses** - Chat responses stream to UI in real-time
- **Search History** - Recent queries with result bookmarking
- **Query Suggestions** - AI-powered query suggestions based on document content

#### Export & Sharing
- **PDF Report Generation** - Generate shareable comparison reports with charts
- **Configuration Share Links** - Share configs via short URLs
- **Result Snapshots** - Pin important query results for team discussion
- **Markdown Export** - Export results as markdown for including in documentation

#### Admin/Team Features
- **User Authentication** - Multi-user support with individual workspaces
- **Shared Document Library** - Team document repository
- **Configuration Library** - Curated list of best-performing configs
- **Audit Logs** - Track who ran which experiments and when
- **Team Collaboration** - Real-time collaborative testing sessions

#### Advanced RAG Tuning
- **Cost Estimator** - Show API costs for queries on different models/configs
- **Token Counter** - Preview token usage before executing queries
- **Latency Predictor** - Estimate query latency based on doc size and config
- **Optimal k-finder** - Algorithm to determine best top_k value automatically

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** – High-performance async web framework
- **SQLAlchemy** – ORM for database management
- **ChromaDB** – Vector database
- **LangChain** – RAG pipeline orchestration patterns
- **Google GenAI** – Gemini LLM integration
- **HuggingFace Transformers** – Embedding models
- **FAISS** – Scalable similarity search

### Frontend
- **React 18** – UI framework
- **Vite** – Lightning-fast bundler
- **Tailwind CSS** – Utility-first styling
- **React Router** – Client-side routing
- **Axios** – HTTP client

### DevOps
- **Docker** – Containerization
- **SQLite** – Default database (PostgreSQL ready)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows
# or: source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# Set up environment variables
export GOOGLE_API_KEY="your-key-here"
# or for HuggingFace:
export HUGGINGFACE_API_KEY="your-key-here"

# Run the server
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` – the frontend will connect to the backend at `http://localhost:8000`

---

## 💾 Database Schema

### Core Models
- **Document** – Stores uploaded documents
- **RAGConfig** – Saves pipeline configurations
- **ChatMessage** – Conversation history
- **Metrics** – Performance metrics for each query
- **Chunk** – Indexed chunks for retrieval

---

## 📊 Example Workflow

1. **Upload Document** → `Setup` page: Upload your PDF/document
2. **Configure Pipeline** → Select chunking, embedder, retriever, LLM
3. **Preview Chunks** → `Preview` page: Visualize how document is split
4. **Save Configuration** → Store config for future experiments
5. **Compare Configs** → Run same query on multiple configs to find best one
6. **Analyze Results** → Check performance metrics and chunk relevance
7. **Export Config** → Save winning configuration for production

---

## 🔧 Configuration Example

```json
{
  "name": "Semantic + Gemini",
  "chunker": {
    "type": "semantic",
    "max_chunk_size": 512,
    "overlap": 100
  },
  "embedder": {
    "type": "google_embeddings",
    "model": "models/embedding-001"
  },
  "retriever": {
    "type": "dense",
    "top_k": 5,
    "similarity_threshold": 0.7
  },
  "llm": {
    "type": "gemini",
    "model": "gemini-pro"
  },
  "memory": {
    "type": "buffer_memory",
    "max_tokens": 2000
  }
}
```

---

## 🐛 Known Limitations & Roadmap

### Current Limitations
- Chat interface UI not yet implemented (backend ready)
- Single-threaded query processing
- Limited to single-user per instance

### Roadmap
- [ ] Multi-user support with authentication
- [ ] Streaming chat responses
- [ ] Additional LLM providers (OpenAI, Anthropic, Ollama)
- [ ] Advanced retrieval methods (ColBERT, DistilBERT)
- [ ] Web crawler for dynamic content
- [ ] Real-time collaboration
- [ ] Mobile app

---

## 📝 Contributing

Contributions welcome! Please:
1. Create a feature branch (`git checkout -b feature/your-feature`)
2. Make your changes with clear commits
3. Open a PR with a description of changes

---

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ChromaDB Guide](https://docs.trychroma.com/)
- [React Documentation](https://react.dev/)
- [Retrieval-Augmented Generation (RAG) Papers](https://arxiv.org/search/?query=rag&searchtype=all)

---

## 📄 License

MIT License – Feel free to use and modify!

---

## 🎓 About RAG

**Retrieval-Augmented Generation (RAG)** combines the power of large language models with retrieval systems:
1. **Retrieve** relevant documents/chunks from a knowledge base
2. **Augment** the prompt with retrieved context
3. **Generate** accurate responses using the LLM

This approach reduces hallucinations and grounds LLM responses in factual data.

---

**Built with ❤️ for AI/ML engineers.**
