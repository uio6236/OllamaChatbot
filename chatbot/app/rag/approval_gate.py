"""폐쇄형 검색 사용 승인 게이트. 외부 서비스 호출·색인은 하지 않는다."""

import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from app.rag.loader import digest
from app.rag.pipeline import canonical, write_json, write_jsonl
from app.rag.quality_checks import inspect_chunk, load_corpus, safe_child
from app.rag.review_models import POLICY_VERSION, ReviewRecord, ReviewRecordV3
from app.rag.review_regions import resolve_regions


def read_ledger(path: Path):
    latest = {}
    review_ids = set()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            raw = json.loads(line)
            policy = raw.get(
                "policyVersion", raw.get("policy_version", "review-policy-v2")
            )
            if policy not in {"review-policy-v2", POLICY_VERSION}:
                raise ValueError("알 수 없는 검수 정책입니다.")
            model = ReviewRecordV3 if policy == POLICY_VERSION else ReviewRecord
            record = model.model_validate_json(line)
            key = (
                (record.chunk_id, record.approval_target_id)
                if isinstance(record, ReviewRecordV3)
                else record.chunk_id
            )
            previous = latest.get(key)
            if record.review_id in review_ids:
                raise ValueError("검수 ID가 중복되어 원장을 신뢰할 수 없습니다.")
            if record.sequence != (previous.sequence + 1 if previous else 0):
                raise ValueError("검수 원장의 순서가 연속적이지 않습니다.")
            if record.previous_review_id != (previous.review_id if previous else None):
                raise ValueError("검수 원장의 이전 기록 연결이 다릅니다.")
            latest[key] = record
            review_ids.add(record.review_id)
    return latest


def official_evidence_valid(evidence, evidence_root: Path) -> bool:
    parsed = urlparse(evidence.url)
    host = (parsed.hostname or "").lower()
    allowed = any(
        host == domain or host.endswith("." + domain)
        for domain in ("law.go.kr", "nts.go.kr")
    )
    if (
        not evidence.reviewed
        or parsed.scheme != "https"
        or not allowed
        or parsed.username
        or parsed.password
    ):
        return False
    try:
        path = safe_child(evidence_root, evidence.snapshot_file)
        if digest(path.read_bytes()) != evidence.snapshot_hash:
            return False
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        return False

    def normalize(value):
        return re.sub(r"\s", "", value)

    return normalize(evidence.excerpt) in normalize(text)


def selected_text(chunk, usage):
    if chunk.document_type != "AMENDMENT_SUMMARY":
        if usage.text_role != "FULL" or usage.selected_line_ids:
            return None, "UNSUPPORTED_PARTIAL_SELECTION"
        if chunk.previous_rule or chunk.revised_rule:
            return None, "MIXED_RULE_ROLES"
        return chunk.content, None
    if usage.text_role != "REVISED_WITH_APPLICATION" or not usage.selected_line_ids:
        return None, "MIXED_PREVIOUS_REVISED"
    ids = usage.selected_line_ids
    if len(set(ids)) != len(ids):
        return None, "DUPLICATE_SELECTED_LINES"
    spans = chunk.source_spans
    chosen = [s for s in spans if s.line_id in ids]
    if [s.line_id for s in chosen] != ids:
        return None, "SELECTION_NOT_IN_SOURCE_ORDER"
    headers = {}
    for span in spans:
        compact = re.sub(r"\s", "", span.text)
        if compact in {"종전", "개정"}:
            if compact in headers:
                return None, "AMBIGUOUS_COMPARISON_HEADERS"
            headers[compact] = span
    notes = [s for s in spans if "적용시기" in s.text or "적용례" in s.text]
    if len(headers) != 2 or not notes or not chunk.application_note:
        return None, "APPLICATION_CONTEXT_UNRESOLVED"
    start = max(s.bbox[3] for s in headers.values())
    note_start = min(s.bbox[1] for s in notes)
    split = sum((s.bbox[0] + s.bbox[2]) / 2 for s in headers.values()) / 2
    revised = {
        s.line_id
        for s in spans
        if start <= s.bbox[1] < note_start and s.bbox[0] >= split
    }
    application = {s.line_id for s in spans if s.bbox[1] >= note_start}
    # 경과 표·예외 각주를 일부만 선택하여 의미가 바뀌는 것을 막는다.
    if (
        not revised
        or not revised <= set(ids)
        or not application <= set(ids)
        or set(usage.required_application_line_ids) != application
    ):
        return None, "REQUIRED_CONTEXT_OMITTED"
    if not set(ids) <= revised | application:
        return None, "PREVIOUS_OR_UNRELATED_TEXT_SELECTED"
    revised_text = "".join(s.text for s in spans if s.line_id in revised)
    if "좌동" in re.sub(r"\s", "", revised_text):
        return None, "SAME_AS_PREVIOUS_CONTEXT_UNRESOLVED"
    return "\n".join(s.text for s in chosen), None


def validate_legacy_chunk(chunk, doc, source_hash, record, evidence_root: Path):
    """v2 회귀 검증 전용. 운영 내보내기에서 호출하지 않는다."""
    if record is None:
        return None, "NO_APPROVAL_RECORD"
    if record.usage.status != "APPROVED":
        return None, "USAGE_" + record.usage.status
    if record.policy_version != "review-policy-v2":
        return None, "POLICY_VERSION_MISMATCH"
    if (
        record.chunk_id != chunk.chunk_id
        or record.document_version != chunk.document_version
        or record.content_hash != chunk.content_hash
        or record.config_hash != chunk.config_hash
    ):
        return None, "APPROVAL_HASH_MISMATCH"
    findings = inspect_chunk(chunk, doc, source_hash)
    if any(f.severity == "BLOCK" for f in findings):
        return None, "STRUCTURE_BLOCKING_FINDING"
    if record.structure.status not in {"PASS_MANUAL", "PASS_SAMPLED"}:
        return None, "STRUCTURE_NOT_REVIEWED"
    if not record.structure.evidence_note or not record.structure.method:
        return None, "STRUCTURE_EVIDENCE_MISSING"
    if record.usage.scope != "CURRENT_2026":
        return None, "NOT_PRODUCTION_SCOPE"
    application = record.applicability
    if (
        application.status != "VERIFIED"
        or not application.applicability_verified
        or application.applicable_tax_year != 2026
        or application.conditions
    ):
        return None, "APPLICABILITY_NOT_VERIFIED_FOR_SCOPE"
    if not application.income_types or set(record.usage.income_types) != set(
        application.income_types
    ):
        return None, "INCOME_SCOPE_UNRESOLVED"
    if (
        chunk.section_income_type
        and chunk.section_income_type not in application.income_types
    ):
        return None, "INCOME_SCOPE_MISMATCH"
    if chunk.document_type == "GUIDE" and chunk.declared_tax_year == 2025:
        return None, "HISTORICAL_2025_NOT_CURRENT_2026"
    if {e.role for e in record.official_evidence} != {"RULE", "APPLICATION"}:
        return None, "OFFICIAL_RULE_OR_APPLICATION_MISSING"
    if not all(
        official_evidence_valid(e, evidence_root) for e in record.official_evidence
    ):
        return None, "OFFICIAL_EVIDENCE_INVALID"
    text, reason = selected_text(chunk, record.usage)
    if reason:
        return None, reason
    # 미해결된 고위험 사유를 표본 승인만으로 넘기지 않는다.
    if record.structure.status == "PASS_SAMPLED":
        if any(
            f.severity == "REVIEW"
            and f.code not in {"CROSS_PAGE", "PARENT_CONTEXT_REQUIRED"}
            for f in findings
        ):
            return None, "HIGH_RISK_REQUIRES_MANUAL_REVIEW"
    view_id = digest(
        canonical(
            [
                chunk.chunk_id,
                digest(text.encode()),
                record.review_id,
                record.usage.model_dump(by_alias=True),
            ]
        ).encode()
    )
    return {
        "chunkId": view_id,
        "parentChunkId": chunk.chunk_id,
        "content": text,
        "contentHash": digest(text.encode()),
        "sourceContentHash": chunk.content_hash,
        "documentVersion": chunk.document_version,
        "documentTitle": chunk.document_title,
        "sourceFile": chunk.source_file,
        "pageStart": chunk.page_start,
        "pageEnd": chunk.page_end,
        "article": chunk.article,
        "sourceUrl": next(e.url for e in record.official_evidence if e.role == "RULE"),
        "effectiveDate": chunk.effective_date,
        "applicableTaxYear": 2026,
        "applicabilityVerified": True,
        "usageScope": "CURRENT_2026",
        "incomeTypes": record.usage.income_types,
        "reviewId": record.review_id,
        "selectedLineIds": record.usage.selected_line_ids,
    }, None


def approve_chunk(
    chunk,
    doc,
    source_hash,
    record,
    evidence_root: Path,
    *,
    chunks=None,
    documents=None,
    integrity=None,
):
    """검토자가 승인한 v3 문맥 묶음만 출력한다. v2는 자동 승격하지 않는다."""
    if record is None:
        return None, "NO_APPROVAL_RECORD"
    if (
        not isinstance(record, ReviewRecordV3)
        or record.policy_version != POLICY_VERSION
    ):
        return None, "POLICY_VERSION_MISMATCH"
    if record.usage.status != "APPROVED":
        return None, "USAGE_" + record.usage.status
    # model_copy 또는 메모리 변경도 내보내기 시 다시 엄격하게 검증한다.
    try:
        record = ReviewRecordV3.model_validate_json(record.model_dump_json())
    except ValueError:
        return None, "INVALID_REVIEW_RECORD"
    if (
        record.chunk_id,
        record.document_version,
        record.content_hash,
        record.config_hash,
    ) != (
        chunk.chunk_id,
        chunk.document_version,
        chunk.content_hash,
        chunk.config_hash,
    ):
        return None, "APPROVAL_HASH_MISMATCH"
    app = record.applicability
    if record.unresolved_issues or app.conditions:
        return None, "UNRESOLVED_VERIFICATION"
    if (
        app.status != "VERIFIED"
        or not app.applicability_verified
        or app.applicable_tax_year != 2026
        or record.usage.scope != "CURRENT_2026"
    ):
        return None, "APPLICABILITY_NOT_VERIFIED_FOR_SCOPE"
    if not app.income_types or set(app.income_types) != set(record.usage.income_types):
        return None, "INCOME_SCOPE_UNRESOLVED"
    if (
        record.structure.status != "PASS_MANUAL"
        or not record.structure.evidence_note
        or not record.structure.method
    ):
        return None, "STRUCTURE_NOT_REVIEWED"
    if (
        record.usage.selected_line_ids
        or record.usage.required_application_line_ids
        or record.usage.text_role != "FULL"
    ):
        return None, "LEGACY_SELECTION_NOT_SUPPORTED"
    chunks = chunks if chunks is not None else {chunk.chunk_id: chunk}
    documents = documents if documents is not None else {chunk.source_file: doc}
    integrity = integrity if integrity is not None else {chunk.source_file: source_hash}
    try:
        regions = resolve_regions(record, chunks, documents, integrity)
    except ValueError as exc:
        return None, str(exc)
    if not any(r["chunkId"] == chunk.chunk_id and r["role"] == "RULE" for r in regions):
        return None, "PRIMARY_RULE_MISSING"
    if any(
        chunks[r["chunkId"]].section_income_type
        and chunks[r["chunkId"]].section_income_type not in app.income_types
        for r in regions
    ):
        return None, "INCOME_SCOPE_MISMATCH"
    evidence = record.official_evidence
    if {e.role for e in evidence} != {"RULE", "APPLICATION"}:
        return None, "OFFICIAL_RULE_OR_APPLICATION_MISSING"
    by_id = {r["regionId"]: r for r in regions}
    covered = set()
    if len({e.evidence_id for e in evidence}) != len(evidence):
        return None, "DUPLICATE_EVIDENCE"
    for e in evidence:
        try:
            stamp = datetime.fromisoformat(e.accessed_at)
            date.fromisoformat(e.promulgation_date)
            date.fromisoformat(e.effective_date)
            snapshot = safe_child(evidence_root, e.snapshot_file).read_text(
                encoding="utf-8"
            )
            valid = (
                stamp.tzinfo is not None
                and official_evidence_valid(e, evidence_root)
                and e.excerpt in snapshot
                and digest(e.excerpt.encode()) == e.excerpt_hash
                and e.region_ids
                and len(set(e.region_ids)) == len(e.region_ids)
            )
        except (ValueError, OSError, UnicodeError):
            valid = False
        if not valid:
            return None, "OFFICIAL_EVIDENCE_INVALID"
        for rid in e.region_ids:
            if rid not in by_id or by_id[rid]["content"] != e.excerpt:
                return None, "OFFICIAL_REGION_MISMATCH"
            if (by_id[rid]["officialLawId"], by_id[rid]["officialLawVersion"]) != (
                e.law_id,
                e.law_version,
            ):
                return None, "OFFICIAL_VERSION_MISMATCH"
            if (by_id[rid]["role"] == "APPLICATION") != (e.role == "APPLICATION"):
                return None, "OFFICIAL_ROLE_MISMATCH"
            covered.add(rid)
    if covered != set(by_id):
        return None, "OFFICIAL_REGION_EVIDENCE_MISSING"
    payload = {
        "exportSchemaVersion": "approved-context-v3",
        "parentChunkId": chunk.chunk_id,
        "approvalTargetId": record.approval_target_id,
        "documentVersion": chunk.document_version,
        "sourceContentHash": chunk.content_hash,
        "regions": regions,
        "legalConditions": [
            c.model_dump(by_alias=True) for c in record.legal_conditions
        ],
        "requiredRegionIds": record.required_region_ids,
        "officialEvidence": [e.model_dump(by_alias=True) for e in evidence],
        "contextReviewNote": record.context_review_note,
        "applicableTaxYear": 2026,
        "applicabilityVerified": True,
        "incomeTypes": app.income_types,
        "usageScope": "CURRENT_2026",
        "reviewId": record.review_id,
        "policyVersion": POLICY_VERSION,
    }
    payload["contentHash"] = digest(canonical(regions).encode())
    payload["chunkId"] = digest(canonical(payload).encode())
    return payload, None


def export_approved(
    processed: Path,
    raw_dir: Path,
    ledger_path: Path,
    evidence_root: Path,
    output_root: Path,
):
    manifest, chunks, documents, integrity = load_corpus(processed, raw_dir)
    records = read_ledger(ledger_path)
    unknown = {r.chunk_id for r in records.values()} - {c.chunk_id for c in chunks}
    if unknown:
        raise ValueError("원장에 현재 실행에 없는 청크가 있습니다.")
    approved = []
    excluded = []
    by_chunk = {c.chunk_id: c for c in chunks}
    targets = [(by_chunk[r.chunk_id], r) for r in records.values()]
    represented = {r.chunk_id for r in records.values()}
    targets.extend((c, None) for c in chunks if c.chunk_id not in represented)
    for chunk, record in sorted(
        targets,
        key=lambda pair: (pair[0].chunk_id, getattr(pair[1], "approval_target_id", "")),
    ):
        view, reason = approve_chunk(
            chunk,
            documents[chunk.source_file],
            integrity.get(chunk.source_file),
            record,
            evidence_root,
            chunks=by_chunk,
            documents=documents,
            integrity=integrity,
        )
        if view:
            approved.append(view)
        else:
            excluded.append(
                {
                    "chunkId": chunk.chunk_id,
                    "approvalTargetId": getattr(record, "approval_target_id", None),
                    "reason": reason,
                }
            )
    identity = {
        "runId": manifest["runId"],
        "manifestHash": digest((processed / "manifest.json").read_bytes()),
        "ledgerHash": digest(ledger_path.read_bytes()),
        "resultHash": digest(canonical([approved, excluded]).encode()),
        "policyVersion": POLICY_VERSION,
    }
    output = output_root / digest(canonical(identity).encode())
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output / "approved-chunks.jsonl", approved)
    write_jsonl(output / "excluded.jsonl", excluded)
    write_json(
        output / "export-report.json",
        {
            **identity,
            "inputCount": len(chunks),
            "targetCount": len(targets),
            "approvedCount": len(approved),
            "excludedCount": len(excluded),
            "exclusionReasons": dict(Counter(x["reason"] for x in excluded)),
        },
    )
    write_json(
        output / "export-manifest.json",
        {
            "identity": identity,
            "artifacts": {
                p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
            },
        },
    )
    return output
