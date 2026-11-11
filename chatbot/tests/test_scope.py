"""범위 선정의 명시성·재현성과 미승인 상태 보존."""

import copy

import pytest
from test_quality_checks import fixture_chunk

from app.rag.elasticsearch_documents import (
    evaluation_documents,
    reject_operational_input,
)
from app.rag.loader import digest
from app.rag.pipeline import canonical
from app.rag.scope import select_candidates, validate_selection


def selection_fixture():
    chunk, _ = fixture_chunk("제95조의2(월세) 총급여 조건은 가상 사례입니다.")
    chunk.document_title = "조세특례제한법"
    chunk.article = "제95조의2"
    result = select_candidates([chunk], [])
    result["selectionHash"] = digest(canonical(result).encode())
    return result


def test_explicit_document_article_not_keyword():
    chunk, _ = fixture_chunk("월세 신용카드 주택청약")
    assert select_candidates([chunk], [])["selectedCount"] == 0
    chunk.document_title = "조세특례제한법"
    chunk.article = "제95조의2"
    result = select_candidates([chunk], [])
    assert result["selectedCount"] == 1
    assert result["candidates"][0]["applicableTaxYear"] is None
    assert result["candidates"][0]["approvalStatus"] == "HOLD"


def test_wrong_law_supplement_not_selected_by_article_number():
    chunk, _ = fixture_chunk()
    chunk.document_title = "소득세법"
    chunk.article = "제95조의2"
    assert select_candidates([chunk], [])["selectedCount"] == 0
    chunk.document_title = "조세특례제한법"
    chunk.structure_path = ["부칙 제1호"]
    assert select_candidates([chunk], [])["selectedCount"] == 0


def test_summary_income_and_title_both_required():
    chunk, _ = fixture_chunk()
    chunk.document_type = "AMENDMENT_SUMMARY"
    chunk.amendment_title = "12. 자녀 수에 따라 신용카드 등 소득공제 한도 확대"
    chunk.income_type = ["BUSINESS"]
    assert select_candidates([chunk], [])["selectedCount"] == 0
    chunk.income_type = ["EARNED"]
    assert select_candidates([chunk], [])["selectedCount"] == 1


def test_order_and_document_ids_reproducible():
    result = selection_fixture()
    a = evaluation_documents(result)
    assert a == evaluation_documents(copy.deepcopy(result))
    c, _ = fixture_chunk()
    d = c.model_copy(update={"chunk_id": "another"})
    assert select_candidates([c, d], []) == select_candidates([d, c], [])


@pytest.mark.parametrize(
    "field,value",
    [("content", "변조"), ("usageScope", "CURRENT_2026"), ("mode", "expanded")],
)
def test_tampering_and_expanded_index_block(field, value):
    result = selection_fixture()
    if field == "mode":
        result[field] = value
    else:
        result["candidates"][0][field] = value
    result["selectionHash"] = digest(
        canonical({k: v for k, v in result.items() if k != "selectionHash"}).encode()
    )
    with pytest.raises(ValueError):
        evaluation_documents(result)


def test_original_chunk_and_evaluation_cannot_be_operational_input():
    with pytest.raises(ValueError):
        reject_operational_input(evaluation_documents(selection_fixture()))
    with pytest.raises(ValueError):
        reject_operational_input([{"content": "원본", "applicabilityVerified": False}])


def test_content_hash_even_when_outer_hash_recomputed():
    result = selection_fixture()
    result["candidates"][0]["content"] = "변조"
    result["selectionHash"] = digest(
        canonical({k: v for k, v in result.items() if k != "selectionHash"}).encode()
    )
    with pytest.raises(ValueError, match="원문"):
        validate_selection(result)


def test_draft_region_tamper_and_missing_reference_blocked():
    from app.rag.review_models import ReviewRecordV3

    chunk, _ = fixture_chunk("가상 검수 대상 원문")
    base = dict(
        chunk_id=chunk.chunk_id,
        document_version=chunk.document_version,
        content_hash=chunk.content_hash,
        config_hash=chunk.config_hash,
    )
    region = dict(
        **base,
        region_id="r1",
        line_ids=[chunk.source_spans[0].line_id],
        text_hash=chunk.content_hash,
        locator="가상 영역",
        official_law_id="test",
        official_law_version="test",
        role="RULE",
    )
    record = ReviewRecordV3(
        **base,
        review_id="draft",
        approval_target_id="rent-2026-spouse-cap",
        regions=[region],
        required_region_ids=["r1"],
    )
    assert select_candidates([chunk], [record])["selectedCount"] == 1
    record.regions[0].text_hash = "0" * 64
    with pytest.raises(ValueError, match="해시"):
        select_candidates([chunk], [record])
    record.required_region_ids = []
    with pytest.raises(ValueError, match="필수"):
        select_candidates([chunk], [record])


def test_fastapi_graph_does_not_import_evaluation_store():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app"
    files = [
        root / "main.py",
        *list((root / "api").glob("*.py")),
        *list((root / "services").glob("*.py")),
    ]
    for file in files:
        tree = ast.parse(file.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in {
                    "app.rag.scope",
                    "app.rag.elasticsearch_store",
                    "app.rag.elasticsearch_documents",
                }
