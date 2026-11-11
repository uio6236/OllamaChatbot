"""가상 검수 자료만 사용해 승인·회수·부분 선택의 폐쇄형 동작을 검증한다."""

import pytest
from pydantic import ValidationError
from test_quality_checks import fixture_chunk

from app.rag.approval_gate import read_ledger
from app.rag.approval_gate import validate_legacy_chunk as approve_chunk
from app.rag.loader import digest
from app.rag.models import Line, Page
from app.rag.review_models import (
    ApplicabilityDecision,
    OfficialEvidence,
    ReviewRecord,
    StructureDecision,
    UsageDecision,
)


def approved_record(chunk, evidence_root):
    # 네트워크 호출 없음. 실제 법령의 내용/적용 검증이 아닌 가상 테스트다.
    text = "가상 테스트 규칙과 적용례 원문"
    (evidence_root / "test-rule.txt").write_text(text, encoding="utf-8")
    evidence = [
        OfficialEvidence(
            url="https://www.law.go.kr/test-only",
            snapshot_file="test-rule.txt",
            snapshot_hash=digest(text.encode()),
            excerpt=text,
            locator="가상 조문",
            role=role,
            reviewed=True,
        )
        for role in ["RULE", "APPLICATION"]
    ]
    return ReviewRecord(
        review_id="test-approved",
        chunk_id=chunk.chunk_id,
        document_version=chunk.document_version,
        content_hash=chunk.content_hash,
        config_hash=chunk.config_hash,
        reviewer="test-reviewer",
        reviewed_at="2026-11-11T10:00:00+09:00",
        structure=StructureDecision(
            status="PASS_MANUAL",
            method="테스트 원문 대조",
            evidence_note="가상 구조 검증",
        ),
        applicability=ApplicabilityDecision(
            status="VERIFIED",
            applicable_tax_year=2026,
            applicability_verified=True,
            income_types=["EARNED"],
        ),
        usage=UsageDecision(
            status="APPROVED", scope="CURRENT_2026", income_types=["EARNED"]
        ),
        official_evidence=evidence,
    )


def test_absent_record_is_excluded(tmp_path):
    chunk, doc = fixture_chunk()
    assert approve_chunk(chunk, doc, "a" * 64, None, tmp_path) == (
        None,
        "NO_APPROVAL_RECORD",
    )


def test_explicit_approval_is_required_and_export_does_not_mutate(tmp_path):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    view, reason = approve_chunk(chunk, doc, "a" * 64, record, tmp_path)
    assert reason is None and view["applicableTaxYear"] == 2026
    assert view["parentChunkId"] == chunk.chunk_id
    assert chunk.applicable_tax_year is None and not chunk.applicability_verified


@pytest.mark.parametrize("mutation", ["source", "content", "config"])
def test_changed_hash_invalidates_approval(tmp_path, mutation):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    actual_hash = "a" * 64
    if mutation == "source":
        actual_hash = "c" * 64
    if mutation == "content":
        chunk.content = "테스트 변경 300원"
    if mutation == "config":
        chunk.config_hash = "d" * 64
    view, reason = approve_chunk(chunk, doc, actual_hash, record, tmp_path)
    assert view is None


def test_2025_guide_cannot_be_labeled_current_2026(tmp_path):
    chunk, doc = fixture_chunk()
    chunk.document_type = "GUIDE"
    chunk.declared_tax_year = 2025
    record = approved_record(chunk, tmp_path)
    assert (
        approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[1]
        == "HISTORICAL_2025_NOT_CURRENT_2026"
    )


@pytest.mark.parametrize("status", ["HOLD", "REJECTED", "REVOKED"])
def test_hold_reject_and_revocation_exclude(tmp_path, status):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    record.usage.status = status
    assert approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[1] == "USAGE_" + status


def amendment_fixture():
    chunk, doc = fixture_chunk()
    lines = []
    data = [
        ("1. 테스트 개정", 10, 10),
        ("종 전", 40, 40),
        ("개 정", 240, 40),
        ("종전 100원", 10, 60),
        ("개정 200원", 210, 60),
        ("☞ 적용시기 및 적용례", 10, 90),
        ("2026.1.1. 이후", 10, 110),
        ("예외 각주", 10, 130),
    ]
    for i, (text, x, y) in enumerate(data):
        lines.append(
            Line(
                line_id=f"p1:b{i}:l0",
                page=1,
                bbox=(x, y, x + 80, y + 8),
                text=text,
                font_size=11,
            )
        )
    chunk.source_spans = lines
    chunk.content = "\n".join(line.text for line in lines)
    chunk.content_hash = digest(chunk.content.encode())
    chunk.document_type = "AMENDMENT_SUMMARY"
    chunk.article = None
    chunk.previous_rule = "종전 100원"
    chunk.revised_rule = "개정 200원"
    chunk.application_note = "☞ 적용시기 및 적용례\n2026.1.1. 이후\n예외 각주"
    chunk.section_income_type = "EARNED"
    doc.pages = [
        Page(number=1, width=595, height=841, rotation=0, status="OK", lines=lines)
    ]
    return chunk, doc


def test_mixed_amendment_full_text_is_not_approved(tmp_path):
    chunk, doc = amendment_fixture()
    record = approved_record(chunk, tmp_path)
    assert (
        approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[1]
        == "MIXED_PREVIOUS_REVISED"
    )


def partial_record(chunk, tmp_path):
    record = approved_record(chunk, tmp_path)
    record.usage.text_role = "REVISED_WITH_APPLICATION"
    record.usage.selected_line_ids = [f"p1:b{i}:l0" for i in [4, 5, 6, 7]]
    record.usage.required_application_line_ids = [f"p1:b{i}:l0" for i in [5, 6, 7]]
    return record


def test_only_revised_text_and_entire_application_context_export(tmp_path):
    chunk, doc = amendment_fixture()
    record = partial_record(chunk, tmp_path)
    view, reason = approve_chunk(chunk, doc, "a" * 64, record, tmp_path)
    assert reason is None
    assert "100원" not in view["content"]
    assert "200원" in view["content"] and "예외 각주" in view["content"]


@pytest.mark.parametrize("bad_selection", [[4, 5, 6], [3, 4, 5, 6, 7], [7, 6, 5, 4]])
def test_partial_selection_cannot_drop_exception_or_add_previous(
    tmp_path, bad_selection
):
    chunk, doc = amendment_fixture()
    record = partial_record(chunk, tmp_path)
    record.usage.selected_line_ids = [f"p1:b{i}:l0" for i in bad_selection]
    assert approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[0] is None


def test_unverified_or_tampered_official_snapshot_is_excluded(tmp_path):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    (tmp_path / "test-rule.txt").write_text("변경됨", encoding="utf-8")
    assert (
        approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[1]
        == "OFFICIAL_EVIDENCE_INVALID"
    )


def test_evidence_path_cannot_escape(tmp_path):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    record.official_evidence[0].snapshot_file = "../test-rule.txt"
    assert approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[0] is None


def test_latest_revocation_wins_and_chain_is_validated(tmp_path):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    revoked = record.model_copy(deep=True)
    revoked.review_id = "test-revoked"
    revoked.sequence = 1
    revoked.previous_review_id = record.review_id
    revoked.usage.status = "REVOKED"
    path = tmp_path / "ledger.jsonl"
    path.write_text(
        record.model_dump_json(by_alias=True)
        + "\n"
        + revoked.model_dump_json(by_alias=True)
        + "\n",
        encoding="utf-8",
    )
    latest = read_ledger(path)
    assert latest[chunk.chunk_id].usage.status == "REVOKED"
    revoked.sequence = 3
    path.write_text(
        record.model_dump_json() + "\n" + revoked.model_dump_json() + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        read_ledger(path)


def test_verification_cannot_be_inferred_from_status_only():
    with pytest.raises(ValidationError):
        ApplicabilityDecision(status="VERIFIED")
    with pytest.raises(ValidationError):
        UsageDecision(income_types=["UNKNOWN"])


@pytest.mark.parametrize("status", ["PENDING", "PASS_AUTO", "HOLD", "REJECT"])
def test_structure_status_alone_cannot_approve(tmp_path, status):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    record.structure.status = status
    assert approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[0] is None


def test_missing_official_application_evidence_blocks_export(tmp_path):
    chunk, doc = fixture_chunk()
    record = approved_record(chunk, tmp_path)
    record.official_evidence = record.official_evidence[:1]
    assert (
        approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[1]
        == "OFFICIAL_RULE_OR_APPLICATION_MISSING"
    )


def test_same_as_previous_is_not_exported_without_its_context(tmp_path):
    chunk, doc = amendment_fixture()
    chunk.source_spans[4].text = "○ (좌 동)"
    chunk.content = "\n".join(s.text for s in chunk.source_spans)
    chunk.content_hash = digest(chunk.content.encode())
    record = partial_record(chunk, tmp_path)
    assert (
        approve_chunk(chunk, doc, "a" * 64, record, tmp_path)[1]
        == "SAME_AS_PREVIOUS_CONTEXT_UNRESOLVED"
    )
