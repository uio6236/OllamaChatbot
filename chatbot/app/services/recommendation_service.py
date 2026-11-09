"""최초 안내 생성. 금액·저장 상태는 Backend에서 관리한다."""

from app.schemas.recommendation import (
    Recommendation,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.generation import GenerationService


class RecommendationService:
    def __init__(self, generation: GenerationService):
        self.generation = generation

    async def respond(self, request: RecommendationRequest) -> RecommendationResponse:
        evidence = await self.generation.retrieve(
            "계산 결과의 공제 항목 설명", request.tax_year
        )
        if not evidence:
            return RecommendationResponse(
                status="INSUFFICIENT_EVIDENCE", recommendations=[]
            )
        content = await self.generation.generate(
            request.model_dump(by_alias=True), evidence
        )
        return RecommendationResponse(
            status="ANSWERED",
            recommendations=[
                Recommendation(
                    typeCode=None,
                    content=content,
                    model=self.generation.model_name,
                    sources=[item.source for item in evidence],
                )
            ],
        )
