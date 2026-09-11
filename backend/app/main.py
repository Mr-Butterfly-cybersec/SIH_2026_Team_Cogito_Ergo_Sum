"""FastAPI application factory."""

import math
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import API_V1_PREFIX, API_V1_ROUTERS, health
from app.config import get_settings


def _json_safe(value: Any) -> Any:
    """Replace non-finite floats with a string, recursively.

    A request body of bare ``NaN`` / ``Infinity`` is accepted by Python's json parser but
    is not valid JSON. Pydantic rejects it, and FastAPI's default 422 handler then tries to
    *echo the offending value back* — which fails, because ``nan`` cannot be serialised.
    The error path itself raises, turning what should be a clean 422 into a 500. Sanitising
    the payload keeps the fault where it belongs: with the client.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from app.db import engine

    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="Cyber risk quantification and investment optimization API",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": _json_safe(exc.errors())})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    for router in API_V1_ROUTERS:
        app.include_router(router, prefix=API_V1_PREFIX)

    return app


app = create_app()
