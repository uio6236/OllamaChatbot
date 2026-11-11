"""명시적 조문·기존 검수 영역에 따른 평가 후보 선정. 승인 상태는 변경하지 않는다."""

import json
from collections import Counter
from pathlib import Path

from app.rag.loader import digest
from app.rag.pipeline import canonical
from app.rag.quality_checks import load_corpus
from app.rag.review_models import ReviewRecordV3

POLICY = "service-scope-v1"
CORE = {
    "조세특례제한법": {
        "제95조의2": "RENT",
        "제126조의2": "CARD",
        "제87조": "HOUSING_SAVING",
    },
    "조세특례제한법 시행령": {
        "제95조": "RENT",
        "제121조의2": "CARD",
        "제81조": "HOUSING_SAVING",
    },
    "조세특례제한법 시행규칙": {"제34조": "HOUSING_SAVING", "제52조의3": "CARD"},
}
SUMMARY = {
    "11. 월세 세액공제 적용 대상자 및 대상주택 확대": "RENT",
    "12. 자녀 수에 따라 신용카드 등 소득공제 한도 확대": "CARD",
    "13. 신용카드 소득공제 대상에서 교육비 세액공제 대상을 제외": "CARD",
    "16. 주택청약종합저축 세제지원 적용기한 연장": "HOUSING_SAVING",
}
EXPANDED = {
    "소득세법": {
        "제20조",
        "제47조",
        "제50조",
        "제51조",
        "제51조의3",
        "제52조",
        "제53조",
        "제54조",
        "제55조",
        "제59조",
        "제59조의2",
        "제59조의3",
        "제59조의4",
        "제60조",
        "제61조",
        "제137조",
    },
    "소득세법 시행령": {
        "제106조",
        "제107조",
        "제108조",
        "제112조",
        "제113조",
        "제114조",
        "제118조의2",
        "제119조의3",
    },
    "조세특례제한법": {"제30조"},
    "조세특례제한법 시행령": {"제27조"},
}
TARGETS = {
    "rent-2026-spouse-cap": "RENT",
    "card-2026-child-limit": "CARD",
    "housing-2026-payment": "HOUSING_SAVING",
}


def select_candidates(chunks, drafts, *, mode="initial"):
    if mode not in {"initial", "expanded"}:
        raise ValueError("알 수 없는 범위입니다.")
    by_id = {c.chunk_id: c for c in chunks}
    if len(by_id) != len(chunks):
        raise ValueError("중복 청크 ID입니다.")
    links = {}
    issues = {}
    canonical_titles = {}
    evidence_links = {}
    for record in drafts:
        if record.approval_target_id not in TARGETS:
            continue
        topic = TARGETS[record.approval_target_id]
        issues[topic] = record.unresolved_issues
        if set(record.required_region_ids) != {r.region_id for r in record.regions}:
            raise ValueError("검수 초안의 필수 영역 연결이 누락되었습니다.")
        for region in record.regions:
            c = by_id.get(region.chunk_id)
            if c is None or (c.document_version, c.content_hash, c.config_hash) != (
                region.document_version,
                region.content_hash,
                region.config_hash,
            ):
                raise ValueError("검수 초안의 원본 연결이 변경되었습니다.")
            spans = [s for s in c.source_spans if s.line_id in region.line_ids]
            if [s.line_id for s in spans] != region.line_ids:
                raise ValueError("검수 초안의 원문 영역이 없습니다.")
            text = "\n".join(s.text for s in spans)[
                region.start_offset : region.end_offset
            ]
            if digest(text.encode()) != region.text_hash:
                raise ValueError("검수 초안 영역 해시가 다릅니다.")
            links.setdefault(c.chunk_id, []).append(
                {
                    "topic": topic,
                    "approvalTargetId": record.approval_target_id,
                    **region.model_dump(by_alias=True),
                }
            )
            canonical_titles[c.chunk_id] = "조세특례제한법" + (
                " 시행규칙"
                if "시행규칙" in c.source_file
                else " 시행령"
                if "시행령" in c.source_file
                else ""
            )
            for evidence in record.official_evidence:
                if region.region_id in evidence.region_ids:
                    evidence_links.setdefault(c.chunk_id, {})[evidence.evidence_id] = {
                        "evidenceId": evidence.evidence_id,
                        "url": evidence.url,
                        "lawId": evidence.law_id,
                        "lawVersion": evidence.law_version,
                        "accessedAt": evidence.accessed_at,
                        "snapshotFile": evidence.snapshot_file,
                        "snapshotHash": evidence.snapshot_hash,
                        "reviewed": evidence.reviewed,
                    }
    selected = []
    for c in sorted(chunks, key=lambda x: x.chunk_id):
        topic = CORE.get(c.document_title, {}).get(c.article)
        reason = "명시적 문서·본문 조문 일치"
        if not c.structure_path or c.structure_path[0] != "본문":
            topic = None
        if c.document_type == "AMENDMENT_SUMMARY" and c.income_type == ["EARNED"]:
            topic = SUMMARY.get(c.amendment_title)
            reason = "명시적 근로소득 개정 항목 일치"
            if mode == "expanded" and c.amendment_title in {
                "6. 자녀세액공제 나이 요건 변경",
                "7. 근로소득 원천징수 시 자녀세액공제분 합리화",
            }:
                topic = "FAMILY"
        if (
            mode == "expanded"
            and c.structure_path
            and c.structure_path[0] == "본문"
            and c.article in EXPANDED.get(c.document_title, set())
        ):
            topic = (
                "YOUTH_SME"
                if c.document_title.startswith("조세특례")
                else "RESULT_CONTEXT"
            )
        references = links.get(c.chunk_id, [])
        topics = sorted(
            {r["topic"] for r in references} | ({topic} if topic else set())
        )
        if not topics:
            continue
        if references:
            reason = "기존 v3 초안의 필수 영역이 참조하는 원본 청크"
        title = canonical_titles.get(c.chunk_id, c.document_title)
        group = digest(
            canonical(
                [
                    title,
                    c.article or c.amendment_title or c.chunk_id,
                    "SUMMARY" if c.document_type == "AMENDMENT_SUMMARY" else "LAW",
                ]
            ).encode()
        )
        selected.append(
            {
                "chunkId": c.chunk_id,
                "documentId": digest(
                    canonical([c.source_file, c.document_version]).encode()
                ),
                "documentVersion": c.document_version,
                "contentHash": c.content_hash,
                "configHash": c.config_hash,
                "documentTitle": c.document_title,
                "canonicalTitle": title,
                "documentType": c.document_type,
                "article": c.article,
                "topics": topics,
                "selectionReason": reason,
                "sourceFile": c.source_file,
                "sourceUrl": c.source_url,
                "pageStart": c.page_start,
                "pageEnd": c.page_end,
                "content": c.content,
                "duplicateGroup": group,
                "contextRegions": references,
                "officialEvidenceLinks": sorted(
                    evidence_links.get(c.chunk_id, {}).values(),
                    key=lambda e: e["evidenceId"],
                ),
                "contextIssues": sorted({i for t in topics for i in issues.get(t, [])}),
                "usageScope": "EVALUATION_ONLY",
                "verificationStatus": "UNVERIFIED",
                "approvalStatus": "HOLD",
                "applicableTaxYear": None,
                "applicabilityVerified": False,
                "textRole": "PREVIOUS_AND_REVISED"
                if c.document_type == "AMENDMENT_SUMMARY"
                else "AMENDMENT_TEXT"
                if "관련개정문과부칙" in c.source_file and c.article is None
                else "UNVERIFIED_SOURCE",
                "effectiveDate": c.effective_date,
                "documentEffectiveDate": c.document_effective_date,
            }
        )
    counts = Counter(t for row in selected for t in row["topics"])
    groups = Counter(r["duplicateGroup"] for r in selected)
    return {
        "policyVersion": POLICY,
        "mode": mode,
        "inputCount": len(chunks),
        "selectedCount": len(selected),
        "excludedCount": len(chunks) - len(selected),
        "topicMembershipCounts": dict(sorted(counts.items())),
        "duplicateGroups": sum(n > 1 for n in groups.values()),
        "missingDraftTargets": sorted(
            set(TARGETS) - {r.approval_target_id for r in drafts}
        ),
        "contextCompleteness": "NOT_LEGALLY_VERIFIED",
        "candidates": selected,
    }


def build_scope(corpora, ledger, *, mode="initial"):
    chunks = []
    inputs = []
    for processed, raw in corpora:
        manifest, rows, _, integrity = load_corpus(Path(processed), Path(raw))
        if any(v is None for v in integrity.values()):
            raise ValueError("원본 해시가 다릅니다.")
        chunks.extend(rows)
        inputs.append(
            {
                "manifestHash": digest(
                    (Path(processed) / "manifest.json").read_bytes()
                ),
                "runId": manifest.get("runId"),
            }
        )
    with Path(ledger).open(encoding="utf-8") as stream:
        drafts = [
            ReviewRecordV3.model_validate_json(line) for line in stream if line.strip()
        ]
    result = select_candidates(chunks, drafts, mode=mode)
    result["inputs"] = inputs
    result["draftLedgerHash"] = digest(Path(ledger).read_bytes())
    result["selectionHash"] = digest(canonical(result).encode())
    return result


def validate_selection(selection):
    payload = {k: v for k, v in selection.items() if k != "selectionHash"}
    if selection.get("selectionHash") != digest(canonical(payload).encode()):
        raise ValueError("선정 결과 해시가 다릅니다.")
    if (
        selection.get("policyVersion") != POLICY
        or len(selection["candidates"]) != selection["selectedCount"]
    ):
        raise ValueError("선정 결과 형식이 다릅니다.")
    for row in selection["candidates"]:
        if digest(row["content"].encode()) != row["contentHash"]:
            raise ValueError("선정 원문 해시가 다릅니다.")
    return selection


def save_selection(result, output_root):
    root = Path(output_root).resolve()
    allowed = Path(__file__).resolve().parents[2] / "data/processed"
    if not root.is_relative_to(allowed.resolve()):
        raise ValueError("결과는 chatbot/data/processed 하위에 저장합니다.")
    target = root / result["selectionHash"] / "scope.json"
    if target.exists():
        if json.loads(target.read_text(encoding="utf-8")) != result:
            raise ValueError("기존 결과 불일치입니다.")
        return target
    target.parent.mkdir(parents=True, exist_ok=False)
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target
