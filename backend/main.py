"""FastAPI application factory for the Nium conversion prototype.

Run: uvicorn backend.main:create_app --factory --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import errors as api_errors
from backend.api.accounts.routes import router as accounts_router
from backend.api.config.routes import router as config_router
from backend.api.conversions.routes import router as conversions_router
from backend.api.demo.routes import router as demo_router
from backend.api.internal.routes import router as internal_router
from backend.api.quotes.routes import router as quotes_router
from backend.api.transactions.routes import router as transactions_router
from backend.config.settings import Settings, load_settings
from backend.container import Container
from backend.db.database import Database
from backend.domain.support import SystemClock
from backend.seed.seed import initialise


def create_app(settings: Settings | None = None, clock: object | None = None) -> FastAPI:
    if not logging.getLogger("wallet").handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    settings = settings or load_settings()
    clock = clock or SystemClock()
    db = Database(settings.database_url)
    initialise(db, settings, clock)
    container = Container(settings=settings, db=db, clock=clock)
    # Crash recovery: no request is in flight at startup, so any RESERVED transaction is stuck.
    container.conversions().reconcile(older_than_seconds=0)

    app = FastAPI(title="Nium Wallet Conversion Prototype", version="0.1.0")
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Idempotent-Replayed"],
    )
    api_errors.install(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in (accounts_router, config_router, quotes_router, conversions_router, transactions_router,
                   internal_router):
        app.include_router(router)
    if settings.demo_mode:
        app.include_router(demo_router)
    return app
