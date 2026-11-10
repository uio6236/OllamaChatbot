"""좌표와 원문을 보존하는 전처리 중간 모델."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )


class Config(Model):
    pipeline_version: str = "pdf-structure-v3"
    max_chars: int = Field(default=2500, ge=200)
    overlap_chars: Literal[0] = 0
    detect_tables: bool = True


class Line(Model):
    line_id: str
    page: int
    bbox: tuple[float, float, float, float]
    text: str
    font_size: float


class Table(Model):
    bbox: tuple[float, float, float, float]
    rows: list[list[str | None]]
    cells: list[tuple[float, float, float, float] | None]
    review_reasons: list[str] = Field(default_factory=list)


class Page(Model):
    number: int
    width: float
    height: float
    rotation: int
    status: Literal["OK", "PARTIAL", "EMPTY", "FAILED"]
    lines: list[Line] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    image_count: int = 0
    review_reasons: list[str] = Field(default_factory=list)


class RawDocument(Model):
    source_file: str
    document_version: str
    document_title: str
    document_type: Literal["LAW", "DECREE", "RULE", "GUIDE", "AMENDMENT_SUMMARY"]
    declared_tax_year: int | None = None
    publication_year: int | None = None
    document_label_year: int | None = None
    document_effective_date: str | None = None
    pages: list[Page]


class Chunk(Model):
    chunk_id: str = ""
    document_title: str
    document_version: str
    document_type: str
    article: str | None = None
    source_file: str
    source_url: str | None = None
    page_start: int
    page_end: int
    effective_date: str | None = None
    applicable_tax_year: int | None = None
    applicability_verified: bool = False
    content: str
    structure_path: list[str]
    source_spans: list[Line]
    parent_id: str = ""
    continuation_candidates: list[str] = Field(default_factory=list)
    part_index: int = 0
    declared_tax_year: int | None = None
    publication_year: int | None = None
    document_label_year: int | None = None
    document_effective_date: str | None = None
    section_income_type: str | None = None
    income_type: list[str] = Field(default_factory=list)
    amendment_title: str | None = None
    amendment_group_id: str | None = None
    sub_amendment_title: str | None = None
    amendment_purpose: str | None = None
    previous_rule: str | None = None
    revised_rule: str | None = None
    application_note: str | None = None
    related_articles: list[str] = Field(default_factory=list)
    comparison_rows: list[dict] = Field(default_factory=list)
    structure_markers: list[dict] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    pipeline_version: str
    config_hash: str
    content_hash: str = ""
    automatic_checks_passed: bool = False
    review_required: bool = True
    review_status: Literal["PENDING"] = "PENDING"
    review_reasons: list[str] = Field(default_factory=lambda: ["HUMAN_REVIEW_PENDING"])


class Exclusion(Model):
    line: Line
    reason: str
