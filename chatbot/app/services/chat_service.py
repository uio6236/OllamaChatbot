"""상담 생성. 회원 인증·DB 조회 및 저장은 하지 않는다."""

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.calc_rules import CalcRuleCatalog, get_calc_rule_catalog
from app.services.generation import GenerationService
from app.services.question_policy import (
    CLARIFY_MESSAGE,
    OTHER_TAX_MESSAGE,
    OUT_OF_SCOPE_MESSAGE,
    SIMULATION_MESSAGE,
    classify_question,
)
from app.services.tax_result_service import TaxResultService


class ChatService:
    def __init__(
        self, generation: GenerationService, calc_rules: CalcRuleCatalog | None = None
    ):
        self.generation = generation
        self.calc_rules = calc_rules

    async def respond(self, request: ChatRequest) -> ChatResponse:
        decision = classify_question(request)
        messages = {
            "SIMULATION": SIMULATION_MESSAGE,
            "OUTSIDE": OUT_OF_SCOPE_MESSAGE,
            "OTHER_TAX": OTHER_TAX_MESSAGE,
            "CLARIFY": CLARIFY_MESSAGE,
            "SERVICE": "희망환급에서는 연말정산 예상 결과와 공제·감면 내역을 확인하고 챗봇에 질문할 수 있습니다. 어떤 기능의 사용 방법이 궁금하신가요?",
        }
        if decision.kind == "MIXED":
            rules = self.calc_rules or get_calc_rule_catalog()
            rule = rules.get(decision.topic) if decision.topic else None
            principle = (
                f"Calc 규칙상 {rule.name}의 계산 원리는 다음과 같습니다. "
                + " ".join(rule.description_steps[:2])
                if rule
                else "어떤 공제의 계산 원리인지 항목명을 알려주시면 확인된 Calc 규칙으로 설명할 수 있습니다."
            )
            return ChatResponse(
                status="ANSWERED",
                answer=f"{principle}\n\n{SIMULATION_MESSAGE}",
                model=None,
                sources=[],
            )
        if decision.kind in messages:
            return ChatResponse(
                status="INSUFFICIENT_EVIDENCE"
                if decision.kind == "CLARIFY"
                else "ANSWERED",
                answer=messages[decision.kind],
                model=None,
                sources=[],
            )
        if decision.question != request.message:
            request = request.model_copy(update={"message": decision.question})
        if request.question_type == "TAX_RESULT":
            calc_rules = self.calc_rules or get_calc_rule_catalog()
            tax_result_service = TaxResultService(self.generation, calc_rules)
            return await tax_result_service.respond(request)

        if CalcRuleCatalog.might_match_question(request.message):
            calc_rules = self.calc_rules or get_calc_rule_catalog()
            tax_result_service = TaxResultService(self.generation, calc_rules)
            rule_response = await tax_result_service.respond_rule_only(request.message)
            if rule_response is not None:
                return rule_response

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
