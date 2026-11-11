"""원본 범위 검증. 문맥 목록의 법적 완전성은 검토자가 판단한다."""

from app.rag.loader import digest
from app.rag.quality_checks import inspect_chunk


def resolve_regions(record, chunks, documents, integrity):
    if not record.context_reviewed or not record.context_review_note:
        raise ValueError("CONTEXT_NOT_REVIEWED")
    regions = record.regions
    ids = [r.region_id for r in regions]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("INVALID_REGION_IDS")
    if set(record.required_region_ids) != set(ids):
        raise ValueError("REQUIRED_CONTEXT_MISSING")
    if len(record.required_region_ids) != len(ids):
        raise ValueError("DUPLICATE_REQUIRED_REGION")
    result = []
    for region in regions:
        chunk = chunks.get(region.chunk_id)
        if chunk is None:
            raise ValueError("UNKNOWN_REGION_CHUNK")
        if (region.document_version, region.content_hash, region.config_hash) != (
            chunk.document_version,
            chunk.content_hash,
            chunk.config_hash,
        ):
            raise ValueError("REGION_SOURCE_CHANGED")
        if chunk.document_type == "GUIDE" and chunk.declared_tax_year == 2025:
            raise ValueError("HISTORICAL_2025_NOT_CURRENT_2026")
        # 비교표의 좌동/종전 관계는 자동 해소하지 않고 보류한다.
        if (
            chunk.document_type == "AMENDMENT_SUMMARY"
            or chunk.previous_rule
            or chunk.revised_rule
        ):
            raise ValueError("MIXED_PREVIOUS_REVISED")
        findings = inspect_chunk(
            chunk, documents[chunk.source_file], integrity.get(chunk.source_file)
        )
        if any(f.severity == "BLOCK" for f in findings):
            raise ValueError("STRUCTURE_BLOCKING_FINDING")
        selected = [s for s in chunk.source_spans if s.line_id in region.line_ids]
        if not selected or [s.line_id for s in selected] != region.line_ids:
            raise ValueError("INVALID_REGION_LINES")
        positions = [chunk.source_spans.index(s) for s in selected]
        if positions != list(range(positions[0], positions[-1] + 1)):
            raise ValueError("NONCONTIGUOUS_REGION")
        source = "\n".join(s.text for s in selected)
        end = region.end_offset if region.end_offset is not None else len(source)
        if not 0 <= region.start_offset < end <= len(source):
            raise ValueError("INVALID_REGION_OFFSETS")
        text = source[region.start_offset : end]
        if digest(text.encode()) != region.text_hash:
            raise ValueError("REGION_HASH_CHANGED")
        if "좌동" in "".join(text.split()):
            raise ValueError("SAME_AS_PREVIOUS_CONTEXT_UNRESOLVED")
        result.append(
            {
                **region.model_dump(by_alias=True),
                "content": text,
                "sourceFile": chunk.source_file,
                "documentTitle": chunk.document_title,
                "pageStart": min(s.page for s in selected),
                "pageEnd": max(s.page for s in selected),
                "sourceSpans": [s.model_dump(by_alias=True) for s in selected],
            }
        )
    by_id = {r["regionId"]: r for r in result}
    for condition in record.legal_conditions:
        if (
            not condition.reviewed
            or condition.region_id not in by_id
            or condition.text not in by_id[condition.region_id]["content"]
        ):
            raise ValueError("LEGAL_CONDITION_NOT_PRESERVED")
    return result
