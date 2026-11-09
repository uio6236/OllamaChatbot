"""상담 생성. 회원 인증·DB 조회 및 저장은 하지 않는다."""

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.generation import GenerationService


class ChatService:
    def __init__(self, generation: GenerationService):
        self.generation = generation

    async def respond(self, request: ChatRequest) -> ChatResponse:
        evidence = await self.generation.retrieve(request.message, request.tax_year)
        if not evidence:
            return ChatResponse(
                status="INSUFFICIENT_EVIDENCE",
                answer="해당 귀속연도에 적용할 수 있는 근거를 충분히 확인하지 못했습니다.",
                model=None,
                sources=[],
            )
        answer = await self.generation.generate(
            request.model_dump(by_alias=True), evidence
        )
        return ChatResponse(
            status="ANSWERED",
            answer=answer,
            model=self.generation.model_name,
            sources=[item.source for item in evidence],
        )
