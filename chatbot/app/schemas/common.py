"""엄격한 camelCase JSON 계약. 계산 금액의 부호를 임의로 바꾸지 않는다."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic.alias_generators import to_camel

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Money = Annotated[int, Field(ge=-999_999_999_999, le=999_999_999_999)]
TaxYear = Annotated[int, Field(ge=2000, le=2100)]


class ContractModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid", strict=True)


class DeductionDetail(ContractModel):
    type_code: Annotated[Text, Field(max_length=30)]
    type_name: Annotated[Text, Field(max_length=50)]
    kind: Literal[
        "INCOME_DEDUCTION", "TAX_CREDIT", "TAX_REDUCTION", "CARD", "CARD_RULE"
    ]
    base_amount: Money
    deduction_amount: Money
    source_note: Annotated[str, Field(max_length=200)] | None = None


class TaxResult(ContractModel):
    prediction_id: Annotated[int, Field(gt=0)]
    withheld_tax: Annotated[Money, Field(ge=0)]
    decided_tax: Annotated[Money, Field(ge=0)]
    expected_refund: Money
    details: Annotated[list[DeductionDetail], Field(max_length=100)]


class HistoryMessage(ContractModel):
    role: Literal["user", "assistant"]
    content: Annotated[Text, Field(max_length=4000)]


class Source(ContractModel):
    chunk_id: Annotated[Text, Field(max_length=200)]
    document_version: Annotated[Text, Field(max_length=200)]
    document_title: Annotated[Text, Field(max_length=300)]
    article: Annotated[Text, Field(max_length=300)] | None
    source_file: Annotated[Text, Field(max_length=255)]
    source_url: Annotated[str, Field(pattern=r"^https?://", max_length=2000)] | None
    page_start: Annotated[int, Field(ge=1)]
    page_end: Annotated[int, Field(ge=1)]
    effective_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None
    applicable_tax_year: TaxYear | None
    applicability_verified: bool

    @model_validator(mode="after")
    def validate_metadata(self):
        if self.effective_date is not None:
            date.fromisoformat(self.effective_date)
        if self.page_end < self.page_start:
            raise ValueError("출처 페이지 범위가 올바르지 않습니다.")
        if self.applicability_verified and self.applicable_tax_year is None:
            raise ValueError("검증된 출처에는 적용 귀속연도가 필요합니다.")
        if "/" in self.source_file or "\\" in self.source_file:
            raise ValueError("출처에는 파일명만 사용합니다.")
        return self


class InternalErrorResponse(ContractModel):
    code: str
    message: str
