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


class CalcInputs(ContractModel):
    """추천에 필요한 Calc 입력 일부. 누락·null은 미확인이고 0/N과 다르다."""

    total_salary: Annotated[Money, Field(ge=0)] | None = None
    national_pension: Annotated[Money, Field(ge=0)] | None = None
    health_insurance: Annotated[Money, Field(ge=0)] | None = None
    monthly_rent: Annotated[Money, Field(ge=0)] | None = None
    housing_saving: Annotated[Money, Field(ge=0)] | None = None
    pension_saving: Annotated[Money, Field(ge=0)] | None = None
    irp_saving: Annotated[Money, Field(ge=0)] | None = None
    sme_reduction_yn: Literal["Y", "N"] | None = None
    homeless_head_yn: Literal["Y", "N"] | None = None


class TaxResult(ContractModel):
    prediction_id: Annotated[int, Field(gt=0)]
    withheld_tax: Annotated[Money, Field(ge=0)]
    decided_tax: Annotated[Money, Field(ge=0)]
    expected_refund: Money
    details: Annotated[list[DeductionDetail], Field(max_length=100)]
    inputs: CalcInputs | None = None

    @model_validator(mode="after")
    def validate_input_snapshot(self):
        """세액 재계산 없이 원본 입력과 Calc 상세의 동일 기준값만 비교한다."""
        if self.inputs is None:
            return self
        values = self.inputs
        expected = {
            "EARNED_DEDUCTION": values.total_salary,
            "NATIONAL_PENSION": values.national_pension,
            "HEALTH_INSURANCE": values.health_insurance,
            "HOUSING_SAVING": values.housing_saving,
            "RENT": values.monthly_rent * 12
            if values.monthly_rent is not None
            else None,
            "PENSION": (
                values.pension_saving + values.irp_saving
                if values.pension_saving is not None and values.irp_saving is not None
                else None
            ),
        }
        for item in self.details:
            value = expected.get(item.type_code)
            if value is not None and value != item.base_amount:
                raise ValueError("원본 입력과 계산 상세의 기준액이 일치하지 않습니다.")
        return self


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
