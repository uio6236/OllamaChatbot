"""결과 버전·재현성·재사용 무결성과 원본 보호 검증."""

import json

import pytest
from test_pdf_loader import make_pdf

from app.rag.models import Config
from app.rag.pipeline import run_pipeline


def test_reproducibility_no_overwrite_and_integrity(tmp_path):
    inputs = tmp_path / "raw"
    inputs.mkdir()
    make_pdf(inputs / "소득세법.pdf", ["제1조(목적) 테스트"])
    output = run_pipeline(inputs, tmp_path / "processed", Config(), 1, True)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["complete"] and manifest["reproducibilityVerified"]
    with pytest.raises(FileExistsError):
        run_pipeline(inputs, tmp_path / "processed", Config(), 1)
    assert (
        run_pipeline(inputs, tmp_path / "processed", Config(), 1, reuse=True) == output
    )
    (output / "document-01.chunks.jsonl").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="해시"):
        run_pipeline(inputs, tmp_path / "processed", Config(), 1, reuse=True)


def test_count_mismatch_produces_no_output(tmp_path):
    with pytest.raises(ValueError, match="개수"):
        run_pipeline(tmp_path, tmp_path / "out", Config())
    assert not (tmp_path / "out").exists()


def test_failed_document_is_reported(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "소득세법.pdf").write_bytes(b"broken")
    with pytest.raises(RuntimeError):
        run_pipeline(raw, tmp_path / "out", Config(), 1)
    report = json.loads(
        next((tmp_path / "out").glob("*/report.json")).read_text(encoding="utf-8")
    )
    assert len(report["failedDocuments"]) == 1


def test_configuration_changes_result_version(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    make_pdf(raw / "소득세법.pdf", ["제1조(목적) 테스트"])
    a = run_pipeline(raw, tmp_path / "out", Config(max_chars=2000), 1)
    b = run_pipeline(raw, tmp_path / "out", Config(max_chars=3000), 1)
    assert a != b
