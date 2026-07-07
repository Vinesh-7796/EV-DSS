# EV Diagnostic Decision Support System (EV-DDSS)

An enterprise-grade, AI-powered diagnostic decision support system for electric vehicle service and repair. Analyzes service manuals, wiring schematics, diagnostic databases, and fault codes to provide intelligent troubleshooting guidance.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EV-DDSS Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Ingestion │  │  Vector  │  │    LLM    │  │  Frontend│  │
│  │ PDF/Excel  │  │   Store  │  │  Inference│  │  (React) │  │
│  │ /Schematic │  │ (Qdrant) │  │  (Local)  │  │          │  │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│        │              │              │              │       │
│  ┌─────┴──────────────┴──────────────┴──────────────┴───┐  │
│  │                     FastAPI Backend                    │ │
│  │                PostgreSQL + SQLAlchemy                 │ │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component     | Technology                          |
|---------------|-------------------------------------|
| Backend       | Python 3.12+, FastAPI, Uvicorn      |
| Database      | PostgreSQL, SQLAlchemy 2.0          |
| Vector Store  | Qdrant                              |
| LLM           | Local (Ollama / llama.cpp) *future* |
| Embeddings    | ONNX / Sentence Transformers *future*|
| Frontend      | React (planned)                     |
| Logging       | Loguru                              |
| Config        | YAML + Environment Variables        |

## Project Structure

```
ev-ddss/
├── backend/                  # Python backend package
│   ├── __init__.py
│   ├── logger.py             # Loguru logging configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py         # Health check endpoints
│   │   ├── router.py         # API route aggregation
│   │   └── server.py         # FastAPI application factory
│   ├── ingestion/            # *future* - file parsers
│   ├── retrieval/            # *future* - RAG retrieval
│   ├── llm/                  # *future* - LLM integration
│   └── validation/           # *future* - output validation
│
├── config/                   # Configuration system
│   ├── __init__.py
│   ├── config.py             # Pydantic Settings loader
│   └── config.yaml           # Default configuration
│
├── database/                 # Database layer
│   ├── __init__.py
│   ├── base.py               # SQLAlchemy declarative base
│   ├── connection.py         # PostgreSQL connection manager
│   ├── models.py             # ORM models (placeholder)
│   ├── qdrant.py             # Qdrant connection manager
│   └── session.py            # FastAPI session dependency
│
├── data/                     # Data storage
│   ├── raw/                  # Raw input files
│   ├── processed/            # Parsed/extracted data
│   ├── embeddings/           # Generated embeddings
│   ├── images/               # Image data
│   └── cache/                # Cached responses
│
├── ingestion/                # *future* - ingestion pipelines
├── retrieval/                # *future* - retrieval pipelines
├── llm/                      # *future* - LLM integration
├── validation/               # *future* - validation pipelines
├── api/                      # *future* - additional API routes
│
├── scripts/                  # Developer utilities
│   ├── setup.sh              # Environment setup (Unix)
│   ├── setup.ps1             # Environment setup (Windows)
│   ├── run.sh                # Run server (Unix)
│   └── run.ps1               # Run server (Windows)
│
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures
│   ├── test_api.py           # FastAPI endpoint tests
│   ├── test_config.py        # Configuration tests
│   ├── test_database.py      # Database manager tests
│   ├── test_logging.py       # Logging tests
│   └── test_qdrant.py        # Qdrant manager tests
│
├── logs/                     # Application logs (gitignored)
├── docs/                     # Documentation
├── output/                   # Generated output
│
├── .env.example              # Environment variable template
├── .gitignore
├── LICENSE
├── main.py                   # Application entry point
├── pyproject.toml
├── requirements.txt          # Production dependencies
└── requirements-dev.txt      # Development dependencies
```

## Installation

### Prerequisites

- **Python 3.12+**
- **PostgreSQL 16+** (optional for Phase 0)
- **Qdrant** (optional for Phase 0)
- **Git**

### Windows

```powershell
# Clone the repository
git clone <repository-url> ev-ddss
cd ev-ddss

# Run the setup script
.\scripts\setup.ps1 -Dev

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

### Unix/Linux/macOS

```bash
# Clone the repository
git clone <repository-url> ev-ddss
cd ev-ddss

# Run the setup script
chmod +x scripts/setup.sh
./scripts/setup.sh --dev

# Activate the virtual environment
source .venv/bin/activate
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the values in `.env`:

   ```env
   # Required for database connectivity
   DATABASE_URL=postgresql://user:password@localhost:5432/ev_ddss

   # Required for Qdrant connectivity
   QDRANT_URL=http://localhost:6333

   # Application settings
   LOG_LEVEL=INFO
   APP_HOST=0.0.0.0
   APP_PORT=8000
   ```

Configuration is resolved in this order:
1. Default values in `config/config.yaml`
2. Environment variables (using `${VAR:-default}` syntax)
3. `.env` file overrides

## Running

### Start the Server

```bash
python main.py
```

Expected output:
```
────────────────────────────────────────
  EV Diagnostic Decision Support System
  Version 0.1.0

  Python      3.12.x
  Host        0.0.0.0:8000
  Debug       False
────────────────────────────────────────

  Configuration  [✓]  Loaded
  Logger         [✓]  Initialized
  Database       [✓]  Connected
  Qdrant         [✓]  Connected
  FastAPI        [✓]  Started

  Environment Ready
────────────────────────────────────────
```

### Verify Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "application": {
    "name": "EV-DDSS",
    "version": "0.1.0",
    "debug": false
  },
  "database": "connected",
  "qdrant": "connected",
  "configuration": "loaded",
  "version": "0.1.0"
}
```

### API Documentation

When running in debug mode, interactive API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
python main.py test
# or
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov=config --cov=database -v
```

## Development Roadmap

### Phase 0 — Foundation (Current)
- [x] Project structure and packaging
- [x] Configuration system (YAML + env vars)
- [x] Enterprise logging (Loguru)
- [x] PostgreSQL database connectivity
- [x] Qdrant vector store connectivity
- [x] Health check API endpoints
- [x] Test suite with pytest
- [x] Developer scripts

### Phase 1 — Ingestion
- [ ] PDF parser (service manual)
- [ ] Excel parser (engineering database)
- [ ] Schematic OCR (component labels)
- [ ] Entity resolution (aliases, cross-references)
- [ ] Text chunking and segmentation

### Phase 2 — Retrieval
- [ ] Embedding generation
- [ ] Qdrant collection management
- [ ] Hybrid search (vector + SQL + keyword)
- [ ] Multi-hop query decomposition

### Phase 3 — LLM Integration
- [ ] Local LLM serving (Ollama / llama.cpp)
- [ ] Prompt engineering and templates
- [ ] Structured output parsing
- [ ] Diagnostic reasoning chain

### Phase 4 — Frontend
- [ ] React application
- [ ] Query interface
- [ ] Results visualization
- [ ] Schematic viewer with highlights

### Phase 5 — Production
- [ ] Authentication and authorization
- [ ] Audit logging
- [ ] Performance optimization
- [ ] Deployment (Docker, Kubernetes)
- [ ] Monitoring and alerting

## License

MIT License — see [LICENSE](LICENSE).
