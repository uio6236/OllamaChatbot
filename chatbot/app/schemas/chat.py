"""상담 생성 요청과 응답."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.common import (
    ContractModel,
    HistoryMessage,
    Source,
    TaxResult,
    TaxYear,
    Text,
)


class ChatRequest(ContractModel):
    question_type: Literal["GENERAL", "TAX_RESULT"]
    message: Annotated[Text, Field(max_length=1000)]
    tax_year: TaxYear
    tax_result: TaxResult | None
    history: Annotated[list[HistoryMessage], Field(max_length=10)]

    @model_validator(mode="after")
    def validate_context(self):
        if (self.question_type == "TAX_RESULT") != (self.tax_result is not None):
            raise ValueError("질문 종류와 계산 결과가 일치하지 않습니다.")
        if sum(len(item.content) for item in self.history) > 12000:
            raise ValueError("대화 문맥이 너무 깁니다.")
        return self


class ChatResponse(ContractModel):
    status: Literal["ANSWERED", "INSUFFICIENT_EVIDENCE"]
    answer: Annotated[Text, Field(max_length=12000)]
    model: Annotated[Text, Field(max_length=50)] | None
    sources: Annotated[list[Source], Field(max_length=10)]
