from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.app.api.router import api_router
from backend.app.config import get_settings, validate_runtime_settings
from backend.app.logging_config import configure_logging
from backend.app.rate_limit import limiter
from backend.app.services.face_analyzer import get_face_app


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.debug)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        runtime_settings = get_settings()
        validate_runtime_settings(runtime_settings)

        if runtime_settings.warmup_face_model:
            print("Warming up InsightFace model...", flush=True)
            get_face_app()
            print("InsightFace model is ready.", flush=True)
        yield

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/healthz", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
