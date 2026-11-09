"""내부 최초 안내 API."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generation
from app.core.security import require_internal_token
from app.schemas.common import InternalErrorResponse
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.generation import GenerationService, within_request_limit
from app.services.recommendation_service import RecommendationService

router = APIRouter(
    dependencies=[Depends(require_internal_token)],
    responses={code: {"model": InternalErrorResponse} for code in (401, 422, 500, 503)},
)


@router.post("/internal/recommendations", response_model=RecommendationResponse)
async def create_recommendations(
    request: RecommendationRequest,
    generation: GenerationService = Depends(get_generation),
):
    return await within_request_limit(
        RecommendationService(generation).respond(request),
        generation.settings.request_timeout,
    )
