"""추출물과 분리한 검수 원장. 자동 검사가 법령 적용을 승인하지 않는다."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic.alias_generators import to_camel

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
POLICY_VERSION = "review-policy-v3"
IncomeType = Literal["EARNED", "BUSINESS", "RELIGIOUS", "PENSION"]


class ReviewModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", strict=True
    )


class Finding(ReviewModel):
    code: str
    severity: Literal["BLOCK", "REVIEW", "INFO"]
    detail: str


class StructureDecision(ReviewModel):
    status: Literal[
        "PENDING", "PASS_AUTO", "PASS_MANUAL", "PASS_SAMPLED", "HOLD", "REJECT"
    ] = "PENDING"
    method: str | None = None
    evidence_note: str | None = None


class ApplicabilityDecision(ReviewModel):
    status: Literal["PENDING", "VERIFIED", "CONDITIONAL", "NOT_APPLICABLE"] = "PENDING"
    applicable_tax_year: int | None = None
    applicability_verified: bool = False
    income_types: list[IncomeType] = Field(default_factory=list)
    conditions: str | None = None

    @model_validator(mode="after")
    def consistent_verification(self):
        if self.status == "VERIFIED":
            if not self.applicability_verified or self.applicable_tax_year is None:
                raise ValueError("검증 완료에는 귀속연도와 검증 표시가 필요합니다.")
        elif self.applicability_verified or self.applicable_tax_year is not None:
            raise ValueError("미검증/조건부 자료의 귀속연도는 null/false로 유지합니다.")
        return self


class OfficialEvidence(ReviewModel):
    url: Text
    snapshot_file: Text
    snapshot_hash: Hash
    excerpt: Text
    locator: Text
    role: Literal["RULE", "APPLICATION"]
    reviewed: bool = False


class UsageDecision(ReviewModel):
    status: Literal["HOLD", "APPROVED", "REJECTED", "REVOKED"] = "HOLD"
    scope: Literal["CURRENT_2026", "EVALUATION_ONLY"] | None = None
    # 본문 전체 또는 원본 줄 ID만 선택한다. 자유 작성한 대체 문장은 받지 않는다.
    selected_line_ids: list[str] = Field(default_factory=list)
    text_role: Literal["FULL", "REVISED_WITH_APPLICATION"] = "FULL"
    required_application_line_ids: list[str] = Field(default_factory=list)
    income_types: list[IncomeType] = Field(default_factory=list)


class ReviewRecord(ReviewModel):
    review_id: Text
    chunk_id: Text
    document_version: Hash
    content_hash: Hash
    config_hash: Hash
    sequence: Annotated[int, Field(ge=0)] = 0
    previous_review_id: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    policy_version: str = "review-policy-v2"
    structure: StructureDecision = Field(default_factory=StructureDecision)
    applicability: ApplicabilityDecision = Field(default_factory=ApplicabilityDecision)
    usage: UsageDecision = Field(default_factory=UsageDecision)
    official_evidence: list[OfficialEvidence] = Field(default_factory=list)
    reason: str = "검토 전: 승인되지 않았습니다."

    @model_validator(mode="after")
    def audit_fields(self):
        if (
            self.usage.status in {"APPROVED", "REVOKED", "REJECTED"}
            or self.sequence > 0
        ):
            if not self.reviewer or not self.reviewer.strip() or not self.reviewed_at:
                raise ValueError("승인에는 검토자와 검토일이 필요합니다.")
            stamp = datetime.fromisoformat(self.reviewed_at)
            if stamp.tzinfo is None:
                raise ValueError("검토일에는 시간대가 필요합니다.")
        return self


class Region(ReviewModel):
    region_id: Text
    chunk_id: Text
    document_version: Hash
    content_hash: Hash
    config_hash: Hash
    line_ids: list[Text]
    start_offset: Annotated[int, Field(ge=0)] = 0
    end_offset: Annotated[int, Field(gt=0)] | None = None
    text_hash: Hash
    locator: Text
    official_law_id: Text
    official_law_version: Text
    role: Literal["RULE", "PARENT", "EXCEPTION", "DEFINITION", "APPLICATION"]


class LegalCondition(ReviewModel):
    kind: Text
    text: Text
    region_id: Text
    reviewed: bool = False


class EvidenceV3(OfficialEvidence):
    evidence_id: Text
    law_id: Text
    law_version: Text
    promulgation_date: Text
    effective_date: Text
    accessed_at: Text
    excerpt_hash: Hash
    region_ids: list[Text]


class ReviewRecordV3(ReviewRecord):
    policy_version: Literal["review-policy-v3"] = "review-policy-v3"
    approval_target_id: Text
    regions: list[Region] = Field(default_factory=list)
    required_region_ids: list[Text] = Field(default_factory=list)
    legal_conditions: list[LegalCondition] = Field(default_factory=list)
    unresolved_issues: list[Text] = Field(default_factory=list)
    context_reviewed: bool = False
    context_review_note: str | None = None
    official_evidence: list[EvidenceV3] = Field(default_factory=list)
