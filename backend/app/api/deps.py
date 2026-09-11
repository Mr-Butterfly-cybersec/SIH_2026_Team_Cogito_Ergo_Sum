"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.engine import ScenarioEngine, get_engine

EngineDep = Annotated[ScenarioEngine, Depends(get_engine)]
