"""대기열·표본 재현성과 원본 불변성/기본 제외를 확인한다."""

import json

import pytest
from test_pdf_loader import make_pdf
from test_quality_checks import fixture_chunk

from app.rag.approval_gate import export_approved
from app.rag.loader import digest
from app.rag.models import Config
from app.rag.pipeline import run_pipeline
from app.rag.review_queue import build_review_bundle, make_queue


def test_priority_and_sample_are_reproducible():
    base, doc = fixture_chunk(
        "제1조(일반) 충분히 긴 비핵심 설명 자료를 사용하는 가상 사례입니다."
    )
    chunks = []
    for i in range(40):
        clone = base.model_copy(deep=True)
        clone.chunk_id = f"test-{i}"
        clone.parent_id = f"parent-{i}"
        chunks.append(clone)
    first = make_queue(
        chunks, {doc.source_file: doc}, {doc.source_file: "a" * 64}, sample_size=10
    )
    second = make_queue(
        list(reversed(chunks)),
        {doc.source_file: doc},
        {doc.source_file: "a" * 64},
        sample_size=10,
    )
    assert first == second
    assert sum(r["sampleSelected"] for r in first) == 10
    assert all(
        r["usageStatus"] == "HOLD" and r["applicableTaxYear"] is None for r in first
    )


@pytest.mark.parametrize(
    "kind,text,priority",
    [
        ("AMENDMENT_SUMMARY", "개정자료 테스트", "P0"),
        (
            "LAW",
            "제1조(월세) 월세 세액공제의 관련 법령을 설명하는 가상 테스트입니다.",
            "P0",
        ),
        (
            "GUIDE",
            "월세 세액공제에 관한 2025년 설명을 충분한 길이로 보존하는 테스트입니다.",
            "P2",
        ),
        (
            "LAW",
            "제1조(기타) 숫자가 깨진 쇯 의심 글리프를 포함하는 테스트입니다.",
            "P1",
        ),
    ],
)
def test_priority_rules(kind, text, priority):
    chunk, doc = fixture_chunk(text)
    chunk.document_type = kind
    rows = make_queue([chunk], {doc.source_file: doc}, {doc.source_file: "a" * 64})
    assert rows[0]["priority"] == priority


def test_bundle_export_zero_and_old_artifacts_unchanged(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    make_pdf(raw / "소득세법.pdf", ["제1조(월세) 가상 테스트 규정"])
    processed = run_pipeline(raw, tmp_path / "processed", Config(), 1)
    before = {p.name: digest(p.read_bytes()) for p in processed.iterdir()}
    bundle = build_review_bundle(processed, raw, tmp_path / "reviews")
    with pytest.raises(FileExistsError):
        build_review_bundle(processed, raw, tmp_path / "reviews")
    output = export_approved(
        processed,
        raw,
        bundle / "review-ledger.jsonl",
        tmp_path / "evidence",
        tmp_path / "exports",
    )
    report = json.loads((output / "export-report.json").read_text(encoding="utf-8"))
    assert report["approvedCount"] == 0
    assert (output / "approved-chunks.jsonl").read_bytes() == b""
    assert {p.name: digest(p.read_bytes()) for p in processed.iterdir()} == before


def test_tampered_artifact_fails_closed(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    make_pdf(raw / "소득세법.pdf", ["제1조(기타) 가상 테스트 규정"])
    processed = run_pipeline(raw, tmp_path / "processed", Config(), 1)
    (processed / "document-01.chunks.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="해시"):
        build_review_bundle(processed, raw, tmp_path / "reviews")
    assert not (tmp_path / "reviews").exists()
