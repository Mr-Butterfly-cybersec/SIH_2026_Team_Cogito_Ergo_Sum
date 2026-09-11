"""Health and readiness endpoints."""

from fastapi import APIRouter, Response, status

from app import __version__
from app.config import get_settings
from app.db import check_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the API process is up. Does not touch the database."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
    }


@router.get("/health/db")
async def health_db(response: Response) -> dict[str, str]:
    """Readiness: the database is reachable."""
    ok = await check_db()
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"database": "ok" if ok else "unavailable"}
