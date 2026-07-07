"""EV-DDSS Application Layer -- FastAPI Backend.

This is the orchestration layer that exposes the AI Core through
production-quality REST and WebSocket endpoints.  It contains NO AI
logic -- all reasoning stays inside the existing ev-ddss modules.
"""

import sys
import pathlib

# Ensure ev-ddss is importable
_project_root = pathlib.Path(__file__).resolve().parent.parent / "ev-ddss"
_project_root_str = str(_project_root)
if _project_root_str not in sys.path:
    sys.path.insert(0, _project_root_str)

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.health import router as health_router
from routes.chat import router as chat_router
from routes.diagnostics import router as diagnostics_router
from routes.documents import router as documents_router
from routes.configuration import router as configuration_router
from websocket.chat_socket import router as ws_router
from middleware.logging import LoggingMiddleware
from middleware.request_id import RequestIDMiddleware
from middleware.exception_handler import register_exception_handlers
from config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print(f"EV-DDSS Application Layer starting — v{settings.application.version}")
    yield
    print("EV-DDSS Application Layer shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.application.name} — API",
        version=settings.application.version,
        description="EV Diagnostic Decision Support System — Application Layer",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router, prefix="", tags=["health"])
    app.include_router(chat_router, prefix="/chat", tags=["chat"])
    app.include_router(diagnostics_router, prefix="/diagnostics", tags=["diagnostics"])
    app.include_router(documents_router, prefix="/documents", tags=["documents"])
    app.include_router(configuration_router, prefix="", tags=["configuration"])
    app.include_router(ws_router, prefix="", tags=["websocket"])

    @app.get("/")
    def root():
        return {
            "application": settings.application.name,
            "version": settings.application.version,
            "layer": "application",
            "status": "running",
        }

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:create_app",
        host=settings.application.host,
        port=settings.application.port,
        reload=settings.application.debug,
        log_level="info",
        factory=True,
    )
