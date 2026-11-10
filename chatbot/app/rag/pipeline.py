"""유형별 청킹·좌표 추적·재현성 검증과 덮어쓰기 없는 결과 저장."""

import json
import platform
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

from app.rag.amendment_chunker import amendment_sections
from app.rag.cleaner import clean_document
from app.rag.documents import to_source
from app.rag.guide_chunker import guide_sections
from app.rag.law_chunker import law_sections, markers, split_long
from app.rag.layout import overlapping_tables
from app.rag.loader import digest, load_pdf
from app.rag.models import Chunk, Config


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def config_identity(config: Config):
    return {
        "config": config.model_dump(by_alias=True),
        "pymupdf": pymupdf.VersionBind,
        "python": platform.python_version(),
    }


def process_document(path: Path, config: Config):
    raw = load_pdf(path, config)
    pages, excluded = clean_document(raw)
    config_hash = digest(canonical(config_identity(config)).encode())
    if raw.document_type == "AMENDMENT_SUMMARY":
        sections = list(amendment_sections(pages))
    elif raw.document_type == "GUIDE":
        sections = [
            (*section, {}) for section in guide_sections(pages, config.max_chars)
        ]
    else:
        sections = [(*section, {}) for section in law_sections(pages)]
    chunks = []
    for article, structure, lines, reasons, extra in sections:
        if not lines:
            continue
        parent = digest(
            canonical(
                [
                    raw.document_version,
                    raw.source_file,
                    config_hash,
                    structure,
                    [line.line_id for line in lines],
                ]
            ).encode()
        )
        # 개정 비교표는 한 항목을 유지하고 초과 길이를 검토 대상으로 남긴다.
        parts = (
            [lines]
            if raw.document_type in {"GUIDE", "AMENDMENT_SUMMARY"}
            else split_long(lines, config.max_chars)
        )
        for index, part in enumerate(parts):
            numbers = {line.page for line in part}
            relevant = [page for page in raw.pages if page.number in numbers]
            issues = ["HUMAN_REVIEW_PENDING", *reasons]
            for page in relevant:
                issues.extend(page.review_reasons)
            if any(page.status != "OK" for page in relevant):
                issues.append("PAGE_EXTRACTION_NOT_OK")
            tables = [
                table for page in relevant for table in overlapping_tables(page, part)
            ]
            if tables:
                issues.append("TABLE_ALIGNMENT_REVIEW")
            text = "\n".join(line.text for line in part)
            if len(text) > config.max_chars:
                issues.append("OVERSIZE_STRUCTURE_PRESERVED")
            chunk = Chunk(
                document_title=raw.document_title,
                document_version=raw.document_version,
                document_type=raw.document_type,
                source_file=raw.source_file,
                article=article,
                content=text,
                structure_path=structure,
                source_spans=part,
                page_start=min(numbers),
                page_end=max(numbers),
                parent_id=parent,
                part_index=index,
                tables=tables,
                declared_tax_year=raw.declared_tax_year,
                publication_year=raw.publication_year,
                document_label_year=raw.document_label_year,
                document_effective_date=raw.document_effective_date,
                pipeline_version=config.pipeline_version,
                config_hash=config_hash,
                structure_markers=markers(part),
                review_reasons=sorted(set(issues)),
                **extra,
            )
            chunk.content_hash = digest(text.encode())
            if chunk.amendment_title:
                chunk.amendment_group_id = digest(
                    canonical(
                        [
                            raw.document_version,
                            raw.source_file,
                            chunk.section_income_type,
                            chunk.amendment_title,
                        ]
                    ).encode()
                )
            chunk.chunk_id = digest(
                canonical([parent, index, chunk.content_hash]).encode()
            )
            to_source(chunk)
            chunk.automatic_checks_passed = bool(text.strip()) and not any(
                reason in issues
                for reason in [
                    "PAGE_EXTRACTION_NOT_OK",
                    "PAGE_EXTRACTION_GAP",
                    "REPLACEMENT_CHARACTER",
                ]
            )
            chunks.append(chunk)
    if raw.document_type == "GUIDE":
        for before, after in zip(chunks, chunks[1:]):
            if (
                before.structure_path == after.structure_path
                and after.page_start == before.page_end + 1
            ):
                before.continuation_candidates.append(after.chunk_id)
                after.continuation_candidates.append(before.chunk_id)
    source_ids = {line.line_id for page in raw.pages for line in page.lines}
    accounted = {line.line_id for chunk in chunks for line in chunk.source_spans}
    accounted.update(item.line.line_id for item in excluded)
    uncovered = sorted(source_ids - accounted)
    uses = Counter(line.line_id for chunk in chunks for line in chunk.source_spans)
    duplicates = defaultdict(list)
    for chunk in chunks:
        duplicates[chunk.content_hash].append(chunk.chunk_id)
    repeated = [ids for ids in duplicates.values() if len(ids) > 1]
    report = {
        "sourceFile": raw.source_file,
        "documentTitle": raw.document_title,
        "documentType": raw.document_type,
        "documentVersion": raw.document_version,
        "totalPages": len(raw.pages),
        "pageStatus": dict(Counter(p.status for p in raw.pages)),
        "pagesRequiringReview": [
            {"page": p.number, "status": p.status, "reasons": p.review_reasons}
            for p in raw.pages
            if p.status != "OK" or p.review_reasons or p.tables
        ],
        "chunkCount": len(chunks),
        "automaticChecksPassed": sum(c.automatic_checks_passed for c in chunks),
        "humanReviewPassed": 0,
        "reviewPending": len(chunks),
        "retrievalReady": 0,
        "crossPageArticleChunks": [
            c.chunk_id for c in chunks if c.article and c.page_end > c.page_start
        ],
        "articleUnits": len(
            {(c.structure_path[0], c.article) for c in chunks if c.article}
        ),
        "supplementChunks": sum(c.structure_path[0].startswith("부칙") for c in chunks),
        "deletedArticleChunks": sum(
            bool(c.article) and "삭제" in c.content.splitlines()[0] for c in chunks
        ),
        "tableCount": sum(len(p.tables) for p in raw.pages),
        "tablesWithMissingOrMergedCells": sum(
            any(cell is None for cell in t.cells) for p in raw.pages for t in p.tables
        ),
        "amendmentRegions": [
            {
                "page": c.page_start,
                "title": c.amendment_title,
                "incomeType": c.income_type,
                "structurePath": c.structure_path,
                "hasPrevious": c.previous_rule is not None,
                "hasRevised": c.revised_rule is not None,
                "hasPurpose": c.amendment_purpose is not None,
                "hasApplicationNote": c.application_note is not None,
                "comparisonRowCount": len(c.comparison_rows),
                "reviewReasons": c.review_reasons,
            }
            for c in chunks
            if raw.document_type == "AMENDMENT_SUMMARY"
        ],
        "uncoveredLineIds": uncovered,
        "multiplyAssignedLineIds": sorted(
            key for key, count in uses.items() if count > 1
        ),
        "duplicateContentCandidates": repeated,
        "applicabilityUnverified": len(chunks),
        "continuationCandidatePairs": [
            [c.chunk_id, following]
            for c in chunks
            for following in c.continuation_candidates
            if c.chunk_id < following
        ],
    }
    if uncovered or report["multiplyAssignedLineIds"]:
        for chunk in chunks:
            chunk.automatic_checks_passed = False
            chunk.review_reasons.append("DOCUMENT_COVERAGE_ERROR")
        report["automaticChecksPassed"] = 0
    return raw, excluded, chunks, report


def write_json(path: Path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, values):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for value in values:
            stream.write(canonical(value) + "\n")


def run_pipeline(
    input_dir: Path,
    output_root: Path,
    config: Config,
    expected_count: int = 8,
    verify_reproducibility: bool = False,
    reuse: bool = False,
):
    files = sorted(input_dir.glob("*.pdf"), key=lambda path: path.name)
    if len(files) != expected_count:
        raise ValueError(f"PDF 개수 불일치: 기대 {expected_count}, 실제 {len(files)}")
    inventory = [
        {"sourceFile": p.name, "sha256": digest(p.read_bytes())} for p in files
    ]
    identity = {"inputs": inventory, **config_identity(config)}
    run_id = digest(canonical(identity).encode())
    output = output_root / run_id
    if output.exists():
        manifest_path = output / "manifest.json"
        if not reuse or not manifest_path.is_file():
            raise FileExistsError(
                "기존 결과를 덮어쓰지 않습니다. 검증된 결과는 --reuse로 재사용하세요."
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["identity"] != identity or not manifest.get("complete"):
            raise ValueError("기존 결과가 완전하지 않거나 설정이 다릅니다.")
        for name, checksum in manifest["artifacts"].items():
            if digest((output / name).read_bytes()) != checksum:
                raise ValueError("기존 생성물 해시 검증에 실패했습니다.")
        if verify_reproducibility and not manifest["reproducibilityVerified"]:
            raise ValueError("기존 실행에 재현성 검증 기록이 없습니다.")
        return output
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    failures = []
    for position, path in enumerate(files):
        print(f"[{position + 1}/{len(files)}] {path.name}", flush=True)
        try:
            raw, excluded, chunks, report = process_document(path, config)
            if verify_reproducibility:
                _, _, second, second_report = process_document(path, config)
                if [c.model_dump(by_alias=True) for c in chunks] != [
                    c.model_dump(by_alias=True) for c in second
                ] or report != second_report:
                    raise ValueError("두 번 처리한 결과의 청크/보고서가 다릅니다.")
            if digest(path.read_bytes()) != raw.document_version:
                raise ValueError("처리 도중 원본 파일이 변경되었습니다.")
            prefix = f"document-{position + 1:02d}"
            write_json(output / f"{prefix}.pages.json", raw.model_dump(by_alias=True))
            write_jsonl(
                output / f"{prefix}.excluded.jsonl",
                (x.model_dump(by_alias=True) for x in excluded),
            )
            write_jsonl(
                output / f"{prefix}.chunks.jsonl",
                (x.model_dump(by_alias=True) for x in chunks),
            )
            write_jsonl(
                output / f"{prefix}.review.jsonl",
                (
                    {
                        "chunkId": c.chunk_id,
                        "reasons": c.review_reasons,
                        "reviewStatus": c.review_status,
                    }
                    for c in chunks
                ),
            )
            report["artifactPrefix"] = prefix
            reports.append(report)
        except Exception as exc:
            failures.append({"sourceFile": path.name, "errorType": type(exc).__name__})
    write_json(
        output / "report.json", {"documents": reports, "failedDocuments": failures}
    )
    artifacts = {
        p.name: digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()
    }
    write_json(
        output / "manifest.json",
        {
            "runId": run_id,
            "identity": identity,
            "complete": not failures,
            "reproducibilityVerified": verify_reproducibility and not failures,
            "artifacts": artifacts,
        },
    )
    if failures:
        raise RuntimeError(
            f"{len(failures)}개 문서 처리 실패. report.json을 확인하세요: {output}"
        )
    return output
