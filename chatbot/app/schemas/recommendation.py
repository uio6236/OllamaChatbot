"""추천 생성 계약. 절세액과 DB 외래키는 모델 출력에서 받지 않는다."""

from typing import Annotated, Literal

from pydantic import Field

from app.schemas.common import ContractModel, Source, TaxResult, TaxYear, Text


class RecommendationRequest(ContractModel):
    tax_year: TaxYear
    tax_result: TaxResult


class Recommendation(ContractModel):
    type_code: Annotated[Text, Field(max_length=30)] | None
    content: Annotated[Text, Field(max_length=12000)]
    model: Annotated[Text, Field(max_length=50)]
    sources: Annotated[list[Source], Field(max_length=10)]


class RecommendationResponse(ContractModel):
    status: Literal["ANSWERED", "INSUFFICIENT_EVIDENCE"]
    recommendations: Annotated[list[Recommendation], Field(max_length=10)]
