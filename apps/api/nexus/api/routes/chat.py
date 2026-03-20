"""Chat routes — AI-powered OSINT conversational analyst."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from nexus.dependencies import get_neo4j, get_pg_pool
from nexus.knowledge.neo4j_client import Neo4jClient
from nexus.services.chat_engine import ChatEngine

logger = structlog.get_logger()
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    context: dict[str, Any] | None = None
    session_id: str = Field(default="default", max_length=100)
    execute_action: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    context_used: dict[str, Any] = Field(default_factory=dict)


async def _execute_action(
    action: dict[str, Any], driver: Any,
) -> dict[str, Any]:
    """Execute a chat-triggered action (collection, investigation, etc.)."""
    action_type = action.get("type", "")
    params = action.get("params", {})

    if action_type == "TRIGGER_COLLECTION":
        try:
            from nexus.services.collection_manager import CollectionManager
            manager = CollectionManager()
            int_type = params.get("int_type", "CYBINT").lower()
            result = await manager.start_collection(
                int_type=int_type,
                query=params.get("query", ""),
                scan_type=params.get("scan_type", "basic"),
            )
            return {
                "response": f"Collection started: {int_type.upper()} scan for '{params.get('query', '')}'. Job ID: {result.get('job_id', 'N/A')}",
                "entities": [],
                "actions": [],
                "context_used": {"action_executed": action_type},
            }
        except Exception as exc:
            logger.warning("chat.action.collection_failed", error=str(exc))
            return {
                "response": f"Collection trigger failed: {exc}. Ensure the collection service is running.",
                "entities": [],
                "actions": [],
                "context_used": {"action_executed": action_type, "error": str(exc)},
            }

    elif action_type == "CREATE_INVESTIGATION":
        try:
            from nexus.services.investigation_runner import InvestigationRunner
            client = Neo4jClient(driver)
            runner = InvestigationRunner(client)
            result = await runner.create_and_execute(
                query=params.get("query", ""),
                target_ints=params.get("target_ints", ["CYBINT"]),
            )
            return {
                "response": f"Investigation created and queued: '{params.get('query', '')}'. ID: {result.get('id', 'N/A')}",
                "entities": [],
                "actions": [],
                "context_used": {"action_executed": action_type},
            }
        except Exception as exc:
            logger.warning("chat.action.investigation_failed", error=str(exc))
            return {
                "response": f"Investigation creation failed: {exc}",
                "entities": [],
                "actions": [],
                "context_used": {"action_executed": action_type, "error": str(exc)},
            }

    return {
        "response": f"Unknown action type: {action_type}",
        "entities": [],
        "actions": [],
        "context_used": {"action_executed": action_type},
    }


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    driver=Depends(get_neo4j),
    pg_pool=Depends(get_pg_pool),
) -> ChatResponse:
    """Send a message to the NEXUS AI analyst and get a RAG-powered response."""
    # Handle execute_action requests
    if request.execute_action:
        try:
            result = await _execute_action(request.execute_action, driver)
            return ChatResponse(**result)
        except Exception as exc:
            logger.error("chat.action_failed", error=str(exc))
            raise HTTPException(status_code=500, detail=f"Action execution failed: {exc}")

    try:
        client = Neo4jClient(driver)
        engine = ChatEngine(client, pg_pool=pg_pool)
        result = await engine.process_message(request.message, request.context, request.session_id)
        return ChatResponse(**result)
    except Exception as exc:
        logger.error("chat.failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Chat service temporarily unavailable")
