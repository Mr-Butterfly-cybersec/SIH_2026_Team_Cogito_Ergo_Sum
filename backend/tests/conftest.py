"""Shared fixtures (all offline — no network)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ingestion.base import HttpClient
from app.models import Base
from tests.helpers import build_http, load_fixture


@pytest.fixture
def make_http() -> Callable[..., HttpClient]:
    return build_http


@pytest.fixture
def nvd_payload() -> dict[str, Any]:
    return load_fixture("nvd_cve_44228.json")


@pytest.fixture
def epss_payload() -> dict[str, Any]:
    return load_fixture("epss_response.json")


@pytest.fixture
def kev_payload() -> dict[str, Any]:
    return load_fixture("kev_catalog.json")


@pytest.fixture
def attack_bundle() -> dict[str, Any]:
    return load_fixture("attack_bundle.json")


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """An in-memory SQLite session (portable thanks to the JSON/JSONB variant).

    Foreign keys are enforced so the tests catch insert-ordering bugs that PostgreSQL
    would reject.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:  # pragma: no cover
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
