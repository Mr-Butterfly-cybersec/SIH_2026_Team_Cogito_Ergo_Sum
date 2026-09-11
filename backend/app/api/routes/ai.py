"""AI endpoint: ask a question, get an answer grounded in engine results.

The response always carries the raw tool calls, so the prose can be checked against the
numbers the engine actually produced.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ai.service import AiService
from app.ai.tools import build_tools
from app.api.deps import EngineDep
from app.api.schemas import (
    AiStatusResponse,
    AiToolModel,
    AskRequest,
    AskResponse,
)

router = APIRouter(tags=["ai"])


def _service(engine: EngineDep) -> AiService:
    from app.ai.service import get_ai_service

    service = get_ai_service()
    if service.engine is not engine:  # pragma: no cover - singleton shares the engine
        service = AiService(engine, service.settings, router=service.router)
    return service


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, engine: EngineDep) -> AskResponse:
    """Ask a natural-language question. The LLM selects tools; the engine produces numbers."""
    service = _service(engine)
    try:
        return AskResponse(**service.ask(request.question).to_dict())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ai/tools", response_model=list[AiToolModel])
def list_tools(engine: EngineDep) -> list[AiToolModel]:
    """The read-only tools the model is allowed to call."""
    return [AiToolModel(**tool.to_dict()) for tool in build_tools(engine)]


@router.get("/ai/status", response_model=AiStatusResponse)
def ai_status(engine: EngineDep) -> AiStatusResponse:
    """Provider chain and whether the deterministic fallback is in use."""
    return AiStatusResponse(**_service(engine).provider_status())
