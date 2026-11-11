"""결정적 위험도 대기열·표본·개정 항목 검수 묶음. 자동 승인은 하지 않는다."""

from collections import Counter, defaultdict
from pathlib import Path

from app.rag.loader import digest
from app.rag.pipeline import canonical, write_json, write_jsonl
from app.rag.quality_checks import inspect_chunk, load_corpus
from app.rag.review_models import POLICY_VERSION, ReviewRecordV3

POLICY = POLICY_VERSION
CORE_TOPICS = {
    "RENT": ("월세",),
    "CARD": ("신용카드", "카드등", "카드 등"),
    "HOUSING_SAVING": ("주택청약", "주택마련저축"),
    "CHILD_EDUCATION": ("자녀세액공제", "자녀 세액공제", "교육비"),
    "YOUTH_SME": ("중소기업 취업자", "중소기업에 취업", "청년 중소기업"),
}


def topics(chunk):
    haystack = chunk.content + "\n" + "\n".join(chunk.structure_path)
    return sorted(
        name for name, terms in CORE_TOPICS.items() if any(t in haystack for t in terms)
    )


def classify(chunk, findings, is_core):
    if chunk.document_type == "AMENDMENT_SUMMARY":
        return "P0"
    if is_core and chunk.document_type in {"LAW", "DECREE", "RULE"}:
        return "P0"
    serious = {
        "NUMBER_MISMATCH",
        "DATE_MISMATCH",
        "NEGATION_MISMATCH",
        "ARTICLE_MIX_CANDIDATE",
        "SUSPICIOUS_GLYPH",
        "INVALID_DATE_CANDIDATE",
        "SOURCE_SPAN_MISMATCH",
        "SOURCE_HASH_CHANGED",
        "CONTENT_HASH_CHANGED",
    }
    if any(f.severity == "BLOCK" or f.code in serious for f in findings):
        return "P1"
    if is_core and (chunk.tables or chunk.page_end > chunk.page_start):
        return "P1"
    if is_core and chunk.document_type == "GUIDE":
        return "P2"
    return "P3"


def make_queue(
    chunks, documents, source_integrity, seed="hope-refund-v1", sample_size=30
):
    if sample_size < 0:
        raise ValueError("표본 크기는 0 이상이어야 합니다.")
    core_ids = {c.chunk_id for c in chunks if topics(c)}
    # 같은 조문 부모와 직접 연결된 부칙은 검토 후보를 확대한다. 적용 승인은 아니다.
    parents = {c.parent_id for c in chunks if c.chunk_id in core_ids and c.parent_id}
    core_articles = defaultdict(set)
    for c in chunks:
        if c.chunk_id in core_ids and c.article:
            core_articles[c.source_file].add(c.article)
    rows = []
    raw_by_doc = {
        name: {line.line_id: line for page in doc.pages for line in page.lines}
        for name, doc in documents.items()
    }
    for chunk in chunks:
        direct_topics = topics(chunk)
        connected = chunk.parent_id in parents or (
            chunk.structure_path[0].startswith("부칙")
            and any(
                article in chunk.content for article in core_articles[chunk.source_file]
            )
        )
        findings = inspect_chunk(
            chunk,
            documents[chunk.source_file],
            source_integrity.get(chunk.source_file),
            original_lines=raw_by_doc[chunk.source_file],
        )
        rows.append(
            {
                "chunkId": chunk.chunk_id,
                "sourceFile": chunk.source_file,
                "documentVersion": chunk.document_version,
                "contentHash": chunk.content_hash,
                "configHash": chunk.config_hash,
                "pageStart": chunk.page_start,
                "pageEnd": chunk.page_end,
                "article": chunk.article,
                "priority": classify(chunk, findings, bool(direct_topics) or connected),
                "topics": direct_topics,
                "coreContextCandidate": connected,
                "findings": [f.model_dump(by_alias=True) for f in findings],
                "officialComparison": "NOT_PERFORMED",
                "sampleSelected": False,
                "structureStatus": "PENDING",
                "applicabilityStatus": "PENDING",
                "usageStatus": "HOLD",
                "applicableTaxYear": None,
                "applicabilityVerified": False,
            }
        )
    # 저위험 법령만 표본 후보다. 문서·페이지 연결·분할 유형별로 순환 선택한다.
    by_id = {c.chunk_id: c for c in chunks}
    strata = defaultdict(lambda: defaultdict(list))
    for row in rows:
        c = by_id[row["chunkId"]]
        codes = {f["code"] for f in row["findings"] if f["severity"] != "INFO"}
        if c.document_type not in {"LAW", "DECREE", "RULE"} or row["priority"] != "P3":
            continue
        if codes - {"CROSS_PAGE", "PARENT_CONTEXT_REQUIRED"}:
            continue
        key = (c.page_end > c.page_start, c.part_index > 0)
        strata[c.source_file][key].append(row)
    for groups in strata.values():
        for group in groups.values():
            group.sort(key=lambda row: digest((seed + row["chunkId"]).encode()))
        selected = 0
        while selected < sample_size and any(groups.values()):
            for key in sorted(groups):
                if groups[key] and selected < sample_size:
                    groups[key].pop(0)["sampleSelected"] = True
                    selected += 1
    return sorted(
        rows,
        key=lambda row: (
            row["priority"],
            row["sourceFile"],
            row["pageStart"],
            row["chunkId"],
        ),
    )


def amendment_packet(chunk, findings):
    return {
        "chunkId": chunk.chunk_id,
        "documentVersion": chunk.document_version,
        "sourceFile": chunk.source_file,
        "pageStart": chunk.page_start,
        "pageEnd": chunk.page_end,
        "sourceSpans": [s.model_dump(by_alias=True) for s in chunk.source_spans],
        "amendmentTitle": chunk.amendment_title,
        "subAmendmentTitle": chunk.sub_amendment_title,
        "amendmentGroupId": chunk.amendment_group_id,
        "incomeType": chunk.income_type,
        "previousRule": chunk.previous_rule,
        "revisedRule": chunk.revised_rule,
        "amendmentPurpose": chunk.amendment_purpose,
        "applicationNote": chunk.application_note,
        "relatedArticles": chunk.related_articles,
        "comparisonRows": chunk.comparison_rows,
        "tables": [t.model_dump(by_alias=True) for t in chunk.tables],
        "content": chunk.content,
        "findings": findings,
        "officialComparison": "NOT_PERFORMED",
        "officialEvidence": [],
        "structureStatus": "PENDING",
        "applicabilityStatus": "PENDING",
        "usageStatus": "HOLD",
    }


def build_review_bundle(
    processed: Path,
    raw_dir: Path,
    output_root: Path,
    seed="hope-refund-v1",
    sample_size=30,
):
    manifest, chunks, documents, integrity = load_corpus(processed, raw_dir)
    rows = make_queue(chunks, documents, integrity, seed, sample_size)
    identity = {
        "runId": manifest["runId"],
        "manifestHash": digest((processed / "manifest.json").read_bytes()),
        "policyVersion": POLICY,
        "seed": seed,
        "sampleSizePerLaw": sample_size,
        "sourceIntegrity": integrity,
    }
    bundle_id = digest(canonical(identity).encode())
    output = output_root / bundle_id
    output.mkdir(parents=True, exist_ok=False)
    row_map = {r["chunkId"]: r for r in rows}
    packets = [
        amendment_packet(c, row_map[c.chunk_id]["findings"])
        for c in chunks
        if c.document_type == "AMENDMENT_SUMMARY"
    ]
    records = [
        ReviewRecordV3(
            approval_target_id="initial-hold",
            review_id=digest(canonical([bundle_id, c.chunk_id, "initial"]).encode()),
            chunk_id=c.chunk_id,
            document_version=c.document_version,
            content_hash=c.content_hash,
            config_hash=c.config_hash,
        ).model_dump(by_alias=True)
        for c in chunks
    ]
    write_jsonl(output / "queue.jsonl", rows)
    write_jsonl(output / "review-ledger.jsonl", records)
    write_jsonl(output / "amendment-packets.jsonl", packets)
    table_reviews = []
    for doc in documents.values():
        document_chunks = [c for c in chunks if c.source_file == doc.source_file]
        for page in doc.pages:
            for index, table in enumerate(page.tables):
                linked = [
                    c
                    for c in document_chunks
                    if any(
                        s.page == page.number
                        and s.bbox[0] < table.bbox[2]
                        and s.bbox[2] > table.bbox[0]
                        and s.bbox[1] < table.bbox[3]
                        and s.bbox[3] > table.bbox[1]
                        for s in c.source_spans
                    )
                ]
                table_reviews.append(
                    {
                        "tableId": digest(
                            canonical(
                                [doc.document_version, page.number, index, table.bbox]
                            ).encode()
                        ),
                        "sourceFile": doc.source_file,
                        "page": page.number,
                        "table": table.model_dump(by_alias=True),
                        "mergedOrMissingCells": any(
                            cell is None for cell in table.cells
                        ),
                        "chunkIds": [c.chunk_id for c in linked],
                        "coreTopicCandidate": any(topics(c) for c in linked),
                        "reviewStatus": "PENDING",
                    }
                )
    write_jsonl(output / "table-review.jsonl", table_reviews)
    write_jsonl(
        output / "evaluation-candidates.jsonl",
        (
            {
                "chunkId": c.chunk_id,
                "content": c.content,
                "usageScope": "EVALUATION_ONLY",
                "userAnswerAllowed": False,
                "documentVersion": c.document_version,
                "sourceFile": c.source_file,
                "pageStart": c.page_start,
                "pageEnd": c.page_end,
                "applicableTaxYear": None,
                "applicabilityVerified": False,
            }
            for c in chunks
        ),
    )
    summary = {
        **identity,
        "chunkCount": len(chunks),
        "priorities": dict(Counter(r["priority"] for r in rows)),
        "findings": dict(Counter(f["code"] for r in rows for f in r["findings"])),
        "chunksWithBlockingFindings": sum(
            any(f["severity"] == "BLOCK" for f in r["findings"]) for r in rows
        ),
        "sampleCount": sum(r["sampleSelected"] for r in rows),
        "sampleCountsBySource": dict(
            Counter(r["sourceFile"] for r in rows if r["sampleSelected"])
        ),
        "amendmentPacketCount": len(packets),
        "tableCount": len(table_reviews),
        "mergedTableCandidateCount": sum(
            t["mergedOrMissingCells"] for t in table_reviews
        ),
        "structureReviewPassed": 0,
        "applicabilityVerified": 0,
        "usageApproved": 0,
        "held": len(chunks),
        "rejected": 0,
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "bundle-manifest.json",
        {
            "bundleId": bundle_id,
            "identity": identity,
            "artifacts": {
                p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
            },
        },
    )
    return output
