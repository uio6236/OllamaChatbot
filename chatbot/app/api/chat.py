"""내부 상담 API."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generation
from app.core.security import require_internal_token
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import InternalErrorResponse
from app.services.chat_service import ChatService
from app.services.generation import GenerationService, within_request_limit

router = APIRouter(
    dependencies=[Depends(require_internal_token)],
    responses={code: {"model": InternalErrorResponse} for code in (401, 422, 500, 503)},
)


@router.post("/internal/chat-responses", response_model=ChatResponse)
async def create_chat_response(
    request: ChatRequest, generation: GenerationService = Depends(get_generation)
):
    return await within_request_limit(
        ChatService(generation).respond(request), generation.settings.request_timeout
    )
