"""
FastAPI application for Client Core Service (Sole State Owner, Outbox, Approvals).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import (
    approvals_router,
    clients_router,
    conv_router,
    health_router,
    leads_router,
    lifecycle_router,
    outbox_router,
    prop_router,
)
from src.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Client Core Service CRM API",
        description="Centralized business data repository, sole lifecycle state authority, outbox dispatcher, and human approval queue.",
        version="0.2.0",
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

    app.include_router(health_router)
    app.include_router(leads_router)
    app.include_router(clients_router)
    app.include_router(conv_router)
    app.include_router(prop_router)
    app.include_router(lifecycle_router)
    app.include_router(outbox_router)
    app.include_router(approvals_router)

    @app.get("/", tags=["Root"])
    def root() -> dict[str, str]:
        return {
            "service": "Client Core Service",
            "version": "0.2.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
