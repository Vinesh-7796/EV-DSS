# EV-DSS

**Electric Vehicle Diagnostic Support System**

An AI-powered diagnostic platform that helps automotive engineers troubleshoot electric vehicle faults. EV-DSS combines a local large language model with a hybrid retrieval engine to analyze fault codes, cross-reference engineering documentation, and produce structured diagnostic reports — all running on-premise with no cloud dependency.

---

## Overview

Electric vehicle diagnostics involve complex, interconnected systems — battery management, thermal management, CAN bus communication, power electronics — where a single fault code can have dozens of root causes spread across multiple technical documents.

EV-DSS solves this by:

- **Ingesting** engineering PDFs, spreadsheets, DBC files, and schematics into a searchable knowledge base.
- **Retrieving** relevant evidence using a hybrid approach: vector similarity search, SQL lookup, and knowledge graph traversal.
- **Reasoning** over the retrieved context with a local LLM to produce structured diagnostic reports.
- **Validating** the output against the source documents to catch hallucinations and unsupported claims.

**Typical workflow:** A technician describes a vehicle symptom or fault code. The system retrieves relevant technical documentation, passes it as context to the reasoning engine, and returns a structured report with possible causes, inspection steps, recommended actions, confidence scores, and cited sources.

**Intended users:** Automotive diagnostic engineers, service technicians, and engineering teams working with electric vehicles.

---

## Features

- AI-assisted fault diagnosis powered by local LLMs (Ollama)
- Hybrid retrieval combining vector search, SQL queries, knowledge graph traversal, and document search
- Automatic ingestion and indexing of PDF, Excel, DBC, and image files
- Structured diagnostic reports with fault summary, causes, inspection steps, and recommended actions
- Confidence scoring with evidence coverage, citation validity, and consistency checks
- Citation validation against source documents
- Hallucination detection
- Safety warnings for high-voltage systems
- Conversation history with diagnostic report archival
- Analytics dashboard with response time trends, query statistics, and system metrics
- Model management interface for switching and downloading LLMs
- Real-time WebSocket streaming for progressive response delivery
- Document management with automatic file watching and re-indexing
- Dark-themed professional engineering UI

---

## Overall System Architecture

![Overall System Architecture](flowcharts/Screenshot%202026-07-01%20142948.png)

The system is split into two layers. The **Application Layer** (`backend/`) is a FastAPI server that exposes REST and WebSocket endpoints, handles authentication, request routing, and serves as the orchestration hub. The **AI Core** (`ev-ddss/`) contains all reasoning, retrieval, validation, and ingestion logic — it is called by the Application Layer but has no web dependencies of its own. The **Frontend** (`frontend/`) is a React SPA that communicates with the backend via HTTP and WebSocket. An **Ollama** instance runs locally to serve LLM inference, and **Qdrant** provides vector storage for semantic search.

---

## Document Ingestion Pipeline

![Document Ingestion Pipeline](flowcharts/Screenshot%202026-07-01%20142959.png)

The ingestion pipeline processes raw engineering documents into a format optimized for retrieval:

1. **Discovery** — A file watcher monitors the `data/raw/` directory for new or modified files. Supported formats include PDF, Excel (`.xlsx`), DBC, PNG, and JPG.

2. **Parsing** — Each file type has a dedicated parser. PDFs are processed with PyMuPDF, spreadsheets with OpenPyXL, and images with Pillow. Parsers extract text content, tables, and metadata.

3. **Chunking** — Extracted content is split into semantically meaningful chunks of configurable size with overlap, preserving section boundaries where possible.

4. **Embedding** — Chunks are converted to vector embeddings using `sentence-transformers` (default model: `all-MiniLM-L6-v2`).

5. **Storage** — Processed data is stored as structured JSON files containing chunks, metadata, and a relationship graph. Vector embeddings are indexed in Qdrant for similarity search.

6. **Graph Extraction** — Entity relationships are extracted from the documents and stored as a knowledge graph for traversal-based retrieval.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite 6, Vitest |
| **Application Layer** | Python 3.12+, FastAPI, Uvicorn, WebSockets |
| **AI Core** | Python, sentence-transformers, PyMuPDF, OpenPyXL, Pillow |
| **LLM Runtime** | Ollama (local), supports any Ollama-compatible model |
| **Vector Database** | Qdrant |
| **Configuration** | Pydantic Settings, YAML, environment variables |
| **Validation** | Custom multi-stage validation engine |
| **Testing** | pytest, pytest-asyncio, pytest-cov, Vitest, Testing Library |
| **Linting** | Ruff, mypy |
| **Platform** | Windows (primary), cross-platform Python |

---

## Project Structure

```
EV-DSS/
├── backend/              Application Layer — FastAPI server, routes, middleware, WebSocket
├── ev-ddss/              AI Core — reasoning, retrieval, validation, ingestion, configuration
│   ├── config/           Settings management (YAML + env vars)
│   ├── retrieval/        Hybrid retrieval engine (vector, SQL, graph, document search)
│   ├── reasoning/        LLM orchestration, prompt templates, intent classification
│   ├── validation/       Confidence scoring, hallucination detection, citation checks
│   ├── ingestion/        Document parsers, chunking, embedding, indexing pipeline
│   └── data/             Raw documents, processed stores, embeddings, cache
├── frontend/             React SPA — chat, diagnostics, documents, models, analytics
├── data/                 Runtime data directory (knowledge base, raw files)
├── flowcharts/           Architecture and flow diagrams
├── docs/                 Project documentation and maintenance guides
├── Reports/              Auto-generated diagnostic reports
└── start.bat             One-click launcher (starts Ollama, backend, and frontend)
```

---

## Runtime Diagnostic Pipeline

When a user submits a diagnostic query, the following pipeline executes:

1. **Query Preprocessing** — The input text is cleaned and an intent classifier determines the query type (fault diagnosis, component lookup, etc.).

2. **Hybrid Retrieval** — The query is executed against multiple retrieval strategies simultaneously:
   - **Vector Search** — Semantic similarity against the Qdrant index
   - **SQL Lookup** — Structured queries against the relational store
   - **Graph Traversal** — Relationship-based lookup via the knowledge graph
   - **Document Search** — Direct text search across ingested files

3. **Context Assembly** — Results from all retrieval strategies are merged, deduplicated, and ranked by relevance score. A token budget optimizer selects the most relevant evidence within the model's context window.

4. **Prompt Generation** — A structured prompt is assembled with the retrieved context, safety rules, and system instructions using Jinja2 templates.

5. **LLM Reasoning** — The assembled prompt is sent to the local Ollama instance. Responses are streamed back via WebSocket for progressive rendering.

6. **Response Parsing** — The raw LLM output is parsed into a structured `DiagnosticResult` containing problem summary, possible causes, inspection steps, recommended actions, and related components.

7. **Validation** — The parsed output goes through multi-stage validation:
   - Citation validation against source documents
   - Evidence coverage scoring
   - Consistency checking between response sections
   - Hallucination detection
   - Safety rule enforcement

8. **Report Generation** — A confidence score is computed from the validation results. The final diagnostic report is assembled with all metadata and saved for history.

---

## Screenshots

### Chat Interface

<!-- Add screenshot here -->

### Analytics Dashboard

<!-- Add screenshot here -->

### Diagnostic History

<!-- Add screenshot here -->

---

## Installation

### Prerequisites

- Python 3.12 or later
- Node.js 18 or later
- [Ollama](https://ollama.ai) installed locally
- (Optional) Qdrant for vector search — `docker run -p 6333:6333 qdrant/qdrant`

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/EV-DSS.git
cd EV-DSS

# Install backend dependencies
cd ev-ddss
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..

# Download a model via Ollama
ollama pull qwen3:8b

# Place engineering documents in the knowledge base
# Supported: PDF, XLSX, DBC, PNG, JPG
copy C:\path\to\documents\* data\knowledge\
```

### Running

```bash
# One-click launcher (recommended)
start.bat
```

Or start services individually:

```bash
# Start Ollama
ollama serve

# Start backend (port 8080)
cd backend
python -m uvicorn app:create_app --host 0.0.0.0 --port 8080 --factory

# Start frontend (port 5173)
cd frontend
npm run dev
```

The application opens at **http://localhost:5173**. API documentation is available at **http://localhost:8080/docs**.

---

## Current Capabilities

- Full diagnostic pipeline from natural language query to structured report
- PDF, Excel, DBC, and image document ingestion with automatic file watching
- Hybrid retrieval with vector similarity, SQL, graph, and document search
- Multi-stage output validation with confidence scoring
- Local LLM inference via Ollama with model switching
- Conversation-based diagnostic sessions with history persistence
- Diagnostic report generation and archival
- Analytics dashboard with response time monitoring and query statistics
- Real-time streaming responses over WebSocket
- Document management with re-indexing and deletion
- Safety warning system for high-voltage procedures

---

## Future Roadmap

- [ ] Continuous document indexing with change detection
- [ ] Improved Qdrant semantic search integration
- [ ] Model Manager — performance benchmarking across installed models
- [ ] Multi-model ensemble reasoning
- [ ] Docker Compose deployment for all services
- [ ] Automated document ingestion from cloud storage
- [ ] Enhanced analytics with exportable reports
- [ ] Role-based access control
- [ ] Multi-language support for international service teams
- [ ] Offline-first mode with full local operation

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

```
MIT License

Copyright (c) 2026 Vinesh | EV-DDSS Team
```
