"""품질 위험 탐지는 적용연도 승인과 독립적이다."""

import pytest

from app.rag.loader import digest
from app.rag.models import Chunk, Line, Page, RawDocument
from app.rag.quality_checks import compare_text, inspect_chunk


def fixture_chunk(content="제1조(테스트) 2026.1.1. 이후 100원 이하"):
    line = Line(
        line_id="p1:b0:l0", page=1, bbox=(10, 20, 300, 30), text=content, font_size=11
    )
    doc = RawDocument(
        source_file="test.pdf",
        document_version="a" * 64,
        document_title="테스트",
        document_type="LAW",
        pages=[
            Page(number=1, width=595, height=841, rotation=0, status="OK", lines=[line])
        ],
    )
    chunk = Chunk(
        chunk_id="chunk-test",
        document_title="테스트",
        document_version="a" * 64,
        document_type="LAW",
        source_file="test.pdf",
        page_start=1,
        page_end=1,
        content=content,
        content_hash=digest(content.encode()),
        structure_path=["본문", "제1조"],
        source_spans=[line],
        article="제1조",
        config_hash="b" * 64,
        pipeline_version="test",
    )
    return chunk, doc


@pytest.mark.parametrize(
    "changed,code",
    [
        ("2026.1.1. 200원 이하", "NUMBER_MISMATCH"),
        ("2027.1.1. 100원 이하", "DATE_MISMATCH"),
        ("2026.1.1. 100원 초과", "NEGATION_MISMATCH"),
        ("2026.1.1. 100원 이하 또는", "LOGIC_MISMATCH"),
    ],
)
def test_important_text_differences(changed, code):
    findings = compare_text(changed, "2026.1.1. 100원 이하", "테스트 비교문")
    assert code in {f.code for f in findings}


@pytest.mark.parametrize(
    "text,code",
    [
        ("257", "PAGE_NUMBER_ONLY"),
        ("본문 쇯 쇽 표지", "SUSPICIOUS_GLYPH"),
        ("본문 \ufffd 문자", "SUSPICIOUS_GLYPH"),
        ("제1조(테스트) 첫 조문\n제2조(다른조문) 혼합", "ARTICLE_MIX_CANDIDATE"),
    ],
)
def test_glyph_page_and_article_candidates(text, code):
    chunk, doc = fixture_chunk(text)
    findings = inspect_chunk(chunk, doc, "a" * 64)
    assert code in {f.code for f in findings}
    assert chunk.applicable_tax_year is None and not chunk.applicability_verified


def test_content_and_provenance_tampering():
    chunk, doc = fixture_chunk()
    chunk.content = "숫자 변조 999원"
    codes = {f.code for f in inspect_chunk(chunk, doc, "c" * 64)}
    assert {"CONTENT_HASH_CHANGED", "SOURCE_HASH_CHANGED", "NUMBER_MISMATCH"} <= codes


def test_independent_reference_is_comparison_only():
    chunk, doc = fixture_chunk()
    findings = inspect_chunk(chunk, doc, "a" * 64, official_reference=chunk.content)
    assert not any(f.code == "OFFICIAL_COMPARISON_NOT_PERFORMED" for f in findings)
    assert not chunk.applicability_verified


def test_invalid_calendar_date_is_reviewed():
    chunk, doc = fixture_chunk(
        "제1조(테스트) 2026.2.30. 이후 적용하는 가상 날짜입니다."
    )
    codes = {f.code for f in inspect_chunk(chunk, doc, "a" * 64)}
    assert "INVALID_DATE_CANDIDATE" in codes
