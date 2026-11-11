"""가상 규칙만으로 v3 승인 경계를 검증한다. 실제 법령 승인이 아니다."""

import json

import pytest
from test_quality_checks import fixture_chunk

from app.rag.approval_gate import approve_chunk, export_approved, read_ledger
from app.rag.loader import digest
from app.rag.models import Line
from app.rag.review_models import (
    ApplicabilityDecision,
    EvidenceV3,
    LegalCondition,
    OfficialEvidence,
    Region,
    ReviewRecord,
    ReviewRecordV3,
    StructureDecision,
    UsageDecision,
)


def v3_fixture(tmp_path, target="a"):
    chunk, doc = fixture_chunk()
    texts = [
        "제1조(가상) ① 총급여 100원 이하인 사람에게 적용한다.",
        "② 무주택인 사람에게 적용한다. 임의의 실제 세법이 아니다.",
        "다만, 다른 공제를 받은 사람은 제외한다.",
        "부칙: 2026.1.1. 이후 지출하는 분부터 적용한다.",
    ]
    lines = [
        Line(
            line_id=f"p1:b{i}:l0",
            page=1,
            bbox=(10, i * 20, 400, i * 20 + 10),
            text=t,
            font_size=11,
        )
        for i, t in enumerate(texts)
    ]
    chunk.source_spans = lines
    chunk.content = "\n".join(texts)
    chunk.content_hash = digest(chunk.content.encode())
    doc.pages[0].lines = lines
    index = 0 if target == "a" else 1
    regions = [
        Region(
            region_id=rid,
            chunk_id=chunk.chunk_id,
            document_version=chunk.document_version,
            content_hash=chunk.content_hash,
            config_hash=chunk.config_hash,
            line_ids=[lines[i].line_id],
            text_hash=digest(texts[i].encode()),
            locator=f"가상 제1조 영역 {i}",
            role=role,
            official_law_id="mock-law",
            official_law_version="mock-v1",
        )
        for rid, i, role in [
            ("main", index, "RULE"),
            ("exception", 2, "EXCEPTION"),
            ("application", 3, "APPLICATION"),
        ]
    ]
    evidence = []
    for r in regions:
        text = next(s.text for s in lines if s.line_id == r.line_ids[0])
        name = f"{target}-{r.region_id}.txt"
        (tmp_path / name).write_text(text, encoding="utf-8")
        evidence.append(
            EvidenceV3(
                evidence_id=r.region_id,
                url="https://www.law.go.kr/mock-only",
                snapshot_file=name,
                snapshot_hash=digest(text.encode()),
                excerpt=text,
                locator=r.locator,
                role="APPLICATION" if r.role == "APPLICATION" else "RULE",
                reviewed=True,
                law_id="mock-law",
                law_version="mock-v1",
                promulgation_date="2025-12-01",
                effective_date="2026-01-01",
                accessed_at="2026-11-11T10:00:00+09:00",
                excerpt_hash=digest(text.encode()),
                region_ids=[r.region_id],
            )
        )
    record = ReviewRecordV3(
        review_id=f"review-{target}",
        approval_target_id=target,
        chunk_id=chunk.chunk_id,
        document_version=chunk.document_version,
        content_hash=chunk.content_hash,
        config_hash=chunk.config_hash,
        reviewer="mock-reviewer",
        reviewed_at="2026-11-11T10:00:00+09:00",
        structure=StructureDecision(
            status="PASS_MANUAL", method="가상 대조", evidence_note="가상 검수"
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
        regions=regions,
        required_region_ids=[r.region_id for r in regions],
        legal_conditions=[
            LegalCondition(
                kind="대상", text=texts[index], region_id="main", reviewed=True
            )
        ],
        context_reviewed=True,
        context_review_note="가상 상위 문장·예외·적용례를 수동 검토함",
        official_evidence=evidence,
    )
    return chunk, doc, record


def run(tmp_path, mutation=None):
    chunk, doc, record = v3_fixture(tmp_path)
    if mutation:
        mutation(chunk, doc, record)
    return approve_chunk(chunk, doc, "a" * 64, record, tmp_path)


def test_legal_conditions_and_separate_context_are_preserved(tmp_path):
    view, reason = run(tmp_path)
    assert reason is None
    assert len(view["regions"]) == 3 and "content" not in view
    assert view["legalConditions"][0]["text"] == view["regions"][0]["content"]
    assert all(r["pageStart"] == 1 and r["sourceSpans"] for r in view["regions"])


@pytest.mark.parametrize(
    "issue", ["부칙 미확인", "버전 불일치", "시가/기준시가 불일치"]
)
def test_unresolved_issues_block(tmp_path, issue):
    assert (
        run(tmp_path, lambda c, d, r: r.unresolved_issues.append(issue))[1]
        == "UNRESOLVED_VERIFICATION"
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda c, d, r: setattr(r.applicability, "conditions", "기존 자유문자열"),
        lambda c, d, r: setattr(r, "context_reviewed", False),
        lambda c, d, r: r.regions.pop(),
        lambda c, d, r: r.required_region_ids.append("missing"),
        lambda c, d, r: setattr(r.regions[0], "line_ids", ["missing"]),
        lambda c, d, r: setattr(r.regions[0], "text_hash", "c" * 64),
        lambda c, d, r: setattr(r.regions[0], "start_offset", 999),
        lambda c, d, r: setattr(r.regions[0], "document_version", "c" * 64),
        lambda c, d, r: setattr(r.legal_conditions[0], "text", "요건이 변경됨"),
        lambda c, d, r: setattr(r.legal_conditions[0], "reviewed", False),
        lambda c, d, r: setattr(r.official_evidence[0], "law_version", "wrong"),
        lambda c, d, r: setattr(r.official_evidence[0], "reviewed", False),
        lambda c, d, r: setattr(r.official_evidence[0], "excerpt_hash", "c" * 64),
        lambda c, d, r: setattr(r.official_evidence[0], "accessed_at", "2026-11-11"),
        lambda c, d, r: setattr(r, "reviewer", None),
        lambda c, d, r: setattr(r.applicability, "status", "PENDING"),
    ],
)
def test_invalid_or_incomplete_review_blocks(tmp_path, change):
    assert run(tmp_path, change)[0] is None


@pytest.mark.parametrize(
    "old,new", [("이하", "초과"), ("2026.1.1.", "2027.1.1."), ("제외", "포함")]
)
def test_official_date_negation_mismatch_even_with_updated_hash(tmp_path, old, new):
    c, d, r = v3_fixture(tmp_path)
    e = next(e for e in r.official_evidence if old in e.excerpt)
    e.excerpt = e.excerpt.replace(old, new)
    e.excerpt_hash = digest(e.excerpt.encode())
    (tmp_path / e.snapshot_file).write_text(e.excerpt, encoding="utf-8")
    e.snapshot_hash = e.excerpt_hash
    assert approve_chunk(c, d, "a" * 64, r, tmp_path)[1] == "OFFICIAL_REGION_MISMATCH"


@pytest.mark.parametrize("kind", ["GUIDE", "AMENDMENT_SUMMARY"])
def test_historical_or_mixed_material_blocks(tmp_path, kind):
    def change(c, d, r):
        c.document_type = kind
        c.declared_tax_year = 2025

    assert run(tmp_path, change)[0] is None


def test_independent_targets_and_revocation_chain(tmp_path):
    c, d, a = v3_fixture(tmp_path, "a")
    _, _, b = v3_fixture(tmp_path, "b")
    revoked = a.model_copy(deep=True)
    revoked.review_id = "revoked-a"
    revoked.sequence = 1
    revoked.previous_review_id = a.review_id
    revoked.usage.status = "REVOKED"
    p = tmp_path / "ledger.jsonl"
    p.write_text(
        "\n".join(x.model_dump_json(by_alias=True) for x in [a, b, revoked]) + "\n",
        encoding="utf-8",
    )
    records = read_ledger(p)
    assert (
        approve_chunk(c, d, "a" * 64, records[(c.chunk_id, "a")], tmp_path)[1]
        == "USAGE_REVOKED"
    )
    assert approve_chunk(c, d, "a" * 64, records[(c.chunk_id, "b")], tmp_path)[0]
    revoked.previous_review_id = b.review_id
    p.write_text(
        "\n".join(x.model_dump_json() for x in [a, b, revoked]), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        read_ledger(p)


def test_v2_is_readable_but_never_promoted(tmp_path):
    c, d, r = v3_fixture(tmp_path)
    legacy = ReviewRecord(
        chunk_id=c.chunk_id,
        document_version=c.document_version,
        content_hash=c.content_hash,
        config_hash=c.config_hash,
        review_id="legacy",
    )
    p = tmp_path / "old.jsonl"
    p.write_text(legacy.model_dump_json(by_alias=True) + "\n", encoding="utf-8")
    before = p.read_bytes()
    record = read_ledger(p)[c.chunk_id]
    assert (
        approve_chunk(c, d, "a" * 64, record, tmp_path)[1] == "POLICY_VERSION_MISMATCH"
    )
    assert p.read_bytes() == before
    assert json.loads(before)["policyVersion"] == "review-policy-v2"


def test_deterministic_bundle_id_and_missing_approval(tmp_path):
    c, d, r = v3_fixture(tmp_path)
    assert approve_chunk(c, d, "a" * 64, r, tmp_path) == approve_chunk(
        c, d, "a" * 64, r, tmp_path
    )
    assert approve_chunk(c, d, "a" * 64, None, tmp_path)[0] is None


def test_cross_chunk_context_keeps_separate_provenance(tmp_path):
    c, d, r = v3_fixture(tmp_path)
    other = c.model_copy(deep=True)
    other.chunk_id = "context-chunk"
    r.regions[-1].chunk_id = other.chunk_id
    view, reason = approve_chunk(
        c,
        d,
        "a" * 64,
        r,
        tmp_path,
        chunks={c.chunk_id: c, other.chunk_id: other},
        documents={c.source_file: d},
        integrity={c.source_file: "a" * 64},
    )
    assert reason is None
    assert view["regions"][-1]["chunkId"] == "context-chunk"
    assert approve_chunk(c, d, "a" * 64, r, tmp_path)[1] == "UNKNOWN_REGION_CHUNK"


@pytest.mark.parametrize("mutation", ["source", "content", "span"])
def test_v3_source_and_content_tampering(tmp_path, mutation):
    c, d, r = v3_fixture(tmp_path)
    source = "a" * 64
    if mutation == "source":
        source = "f" * 64
    elif mutation == "content":
        c.content += "변조"
    else:
        c.source_spans = [s.model_copy(deep=True) for s in c.source_spans]
        c.source_spans[0].text += "변조"
    assert approve_chunk(c, d, source, r, tmp_path)[0] is None


def test_subline_offsets_preserve_exact_selected_text(tmp_path):
    c, d, r = v3_fixture(tmp_path)
    region = r.regions[0]
    region.start_offset = len("제1조(가상) ")
    text = c.source_spans[0].text[region.start_offset :]
    region.text_hash = digest(text.encode())
    r.legal_conditions[0].text = text
    e = r.official_evidence[0]
    e.excerpt = text
    e.excerpt_hash = region.text_hash
    view, reason = approve_chunk(c, d, "a" * 64, r, tmp_path)
    assert reason is None
    assert view["regions"][0]["content"] == text


def test_unrelated_v2_approval_cannot_enter_v3_export(tmp_path):
    c, d, r = v3_fixture(tmp_path)
    data = r.model_dump()
    fields = set(ReviewRecord.model_fields)
    data = {k: v for k, v in data.items() if k in fields}
    data["policy_version"] = "review-policy-v2"
    data["official_evidence"] = [
        {k: v for k, v in evidence.items() if k in OfficialEvidence.model_fields}
        for evidence in data["official_evidence"]
    ]
    legacy = ReviewRecord.model_validate_json(json.dumps(data))
    assert legacy.usage.status == "APPROVED"
    assert (
        approve_chunk(c, d, "a" * 64, legacy, tmp_path)[1] == "POLICY_VERSION_MISMATCH"
    )


def test_export_multiple_targets_then_independent_revocation(tmp_path, monkeypatch):
    c, d, a = v3_fixture(tmp_path, "a")
    _, _, b = v3_fixture(tmp_path, "b")
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "manifest.json").write_text("가상 manifest", encoding="utf-8")
    monkeypatch.setattr(
        "app.rag.approval_gate.load_corpus",
        lambda *args: (
            {"runId": "mock"},
            [c],
            {c.source_file: d},
            {c.source_file: "a" * 64},
        ),
    )
    ledger = tmp_path / "ledger.jsonl"

    def write(records):
        ledger.write_text(
            "\n".join(r.model_dump_json(by_alias=True) for r in records) + "\n",
            encoding="utf-8",
        )

    write([a, b])
    before = ledger.read_bytes()
    output = export_approved(
        processed, tmp_path, ledger, tmp_path, tmp_path / "exports"
    )
    assert json.loads((output / "export-report.json").read_text())["approvedCount"] == 2
    assert ledger.read_bytes() == before
    revoked = a.model_copy(deep=True)
    revoked.review_id = "revoke-a"
    revoked.sequence = 1
    revoked.previous_review_id = a.review_id
    revoked.usage.status = "REVOKED"
    write([a, b, revoked])
    output = export_approved(
        processed, tmp_path, ledger, tmp_path, tmp_path / "exports"
    )
    views = [
        json.loads(line)
        for line in (output / "approved-chunks.jsonl").open(encoding="utf-8")
    ]
    assert len(views) == 1 and views[0]["approvalTargetId"] == "b"
