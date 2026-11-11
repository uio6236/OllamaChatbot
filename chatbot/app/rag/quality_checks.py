"""기존 생성물·원본의 읽기 전용 무결성 및 구조 위험 신호 검사."""

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from app.rag.loader import digest
from app.rag.models import Chunk, RawDocument
from app.rag.review_models import Finding

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?(?:\s*(?:%|원|만원|억원|세|년|월|일))?")
DATE = re.compile(r"(?:19|20)\d{2}[.년/-]\s*\d{1,2}(?:[.월/-]\s*\d{1,2})?")
NEGATION = re.compile(r"미만|이하|이상|초과|제외|포함|아니|않|없|삭제")
LOGIC = re.compile(r"또는|모두|다만|한정|각각")
SUSPICIOUS_GLYPH = re.compile(r"[\ufffd\ue000-\uf8ff]|[쇬-쇿]")
FULL_DATE = re.compile(r"((?:19|20)\d{2})[./년-]\s*(\d{1,2})[./월-]\s*(\d{1,2})(?!\d)")


def safe_child(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("기준 경로 밖의 파일 참조를 거부합니다.")
    return path


def load_corpus(processed: Path, raw_dir: Path):
    manifest = json.loads((processed / "manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("complete"):
        raise ValueError("미완료 전처리 결과는 검수/내보내기에 사용하지 않습니다.")
    for name, checksum in manifest["artifacts"].items():
        if digest(safe_child(processed, name).read_bytes()) != checksum:
            raise ValueError(f"생성물 해시 불일치: {name}")
    source_integrity = {}
    for source in manifest["identity"]["inputs"]:
        path = safe_child(raw_dir, source["sourceFile"])
        source_integrity[source["sourceFile"]] = (
            source["sha256"]
            if path.is_file() and digest(path.read_bytes()) == source["sha256"]
            else None
        )
    report = json.loads((processed / "report.json").read_text(encoding="utf-8"))
    chunks = []
    documents = {}
    for item in report["documents"]:
        prefix = item["artifactPrefix"]
        page_file = prefix + ".pages.json"
        chunk_file = prefix + ".chunks.jsonl"
        review_file = prefix + ".review.jsonl"
        if not {page_file, chunk_file, review_file} <= manifest["artifacts"].keys():
            raise ValueError("필수 생성물의 manifest 등록이 누락되었습니다.")
        doc = RawDocument.model_validate_json(
            safe_child(processed, page_file).read_text(encoding="utf-8")
        )
        if doc.document_version != source_integrity.get(doc.source_file):
            source_integrity[doc.source_file] = None
        documents[doc.source_file] = doc
        with safe_child(processed, chunk_file).open(encoding="utf-8") as stream:
            chunks.extend(
                Chunk.model_validate_json(line) for line in stream if line.strip()
            )
    if len({c.chunk_id for c in chunks}) != len(chunks):
        raise ValueError("중복 청크 ID가 있습니다.")
    return manifest, chunks, documents, source_integrity


def compare_text(candidate: str, reference: str, origin: str) -> list[Finding]:
    """비교 결과는 구조 신호이며 공식 법령의 적용 판단을 하지 않는다."""
    findings = []
    for code, pattern in [
        ("NUMBER", NUMBER),
        ("DATE", DATE),
        ("NEGATION", NEGATION),
        ("LOGIC", LOGIC),
    ]:

        def normalize(value):
            return re.sub(r"\s", "", value)

        left = Counter(normalize(x) for x in pattern.findall(candidate))
        right = Counter(normalize(x) for x in pattern.findall(reference))
        if left != right:
            findings.append(
                Finding(
                    code=code + "_MISMATCH",
                    severity="BLOCK",
                    detail=f"{origin}의 {code} 표지가 다릅니다. 자동 보정하지 않습니다.",
                )
            )
    if re.sub(r"\s", "", candidate) != re.sub(r"\s", "", reference):
        findings.append(
            Finding(
                code="TEXT_MISMATCH",
                severity="REVIEW",
                detail=f"{origin} 텍스트가 다릅니다. 원문 대조가 필요합니다.",
            )
        )
    return findings


def inspect_chunk(
    chunk: Chunk,
    doc: RawDocument,
    actual_source_hash: str | None,
    official_reference: str | None = None,
    original_lines=None,
) -> list[Finding]:
    result = []

    def add(code, severity, detail):
        result.append(Finding(code=code, severity=severity, detail=detail))

    if (
        actual_source_hash != chunk.document_version
        or doc.document_version != chunk.document_version
    ):
        add("SOURCE_HASH_CHANGED", "BLOCK", "현재 원본과 승인 대상 버전이 다릅니다.")
    if digest(chunk.content.encode()) != chunk.content_hash:
        add("CONTENT_HASH_CHANGED", "BLOCK", "청크 본문 해시가 다릅니다.")
    originals = (
        original_lines
        if original_lines is not None
        else {line.line_id: line for page in doc.pages for line in page.lines}
    )
    for span in chunk.source_spans:
        if span.line_id not in originals or span != originals[span.line_id]:
            add("SOURCE_SPAN_MISMATCH", "BLOCK", "원본 줄/좌표/페이지 연결이 다릅니다.")
            break
    span_text = "\n".join(s.text for s in chunk.source_spans)
    result.extend(compare_text(chunk.content, span_text, "추출 줄"))
    if (
        not chunk.source_spans
        or chunk.page_start != min((s.page for s in chunk.source_spans), default=0)
        or chunk.page_end != max((s.page for s in chunk.source_spans), default=0)
    ):
        add("PAGE_RANGE_MISMATCH", "BLOCK", "출처 페이지 범위가 일치하지 않습니다.")
    if re.fullmatch(r"\s*\d+\s*", chunk.content):
        add("PAGE_NUMBER_ONLY", "BLOCK", "쪽수만 있는 청크는 답변 근거에서 제외합니다.")
    elif len(chunk.content.strip()) < 30:
        add(
            "SHORT_FRAGMENT",
            "REVIEW",
            "짧은 삭제 조문/제목/본문 조각을 구분해야 합니다.",
        )
    if SUSPICIOUS_GLYPH.search(chunk.content):
        add(
            "SUSPICIOUS_GLYPH",
            "REVIEW",
            "깨진 문자 또는 특수 표지 글리프 후보가 있습니다.",
        )
    for match in FULL_DATE.finditer(chunk.content):
        try:
            date(*(int(part) for part in match.groups()))
        except ValueError:
            add(
                "INVALID_DATE_CANDIDATE",
                "REVIEW",
                "유효하지 않은 날짜 후보입니다. 원문을 확인하고 자동 보정하지 않습니다.",
            )
            break
    if len(chunk.content) > 2500:
        add("LONG_STRUCTURE", "REVIEW", "장문 조문의 단서·상위 문맥을 확인해야 합니다.")
    if chunk.page_end > chunk.page_start:
        add("CROSS_PAGE", "REVIEW", "페이지 사이의 항·호·단서 연결을 확인해야 합니다.")
    headers = re.findall(r"(?m)^\s*(제\d+조(?:의\d+)?)(?=\s*\(|\s+삭제)", chunk.content)
    if chunk.article and any(header != chunk.article for header in headers):
        add("ARTICLE_MIX_CANDIDATE", "BLOCK", "다른 조문 제목이 섞였을 수 있습니다.")
    if chunk.article and not headers:
        add(
            "PARENT_CONTEXT_REQUIRED",
            "REVIEW",
            "하위 청크의 조문 제목은 부모와 함께 확인합니다.",
        )
    if any(any(cell is None for cell in table.cells) for table in chunk.tables):
        add("MERGED_TABLE", "REVIEW", "병합/누락 셀의 의미를 검토해야 합니다.")
    if chunk.tables:
        add("TABLE_ALIGNMENT", "REVIEW", "행·열·각주의 대응 검토가 필요합니다.")
    if "IMAGE_REGIONS_NOT_OCR" in chunk.review_reasons:
        add(
            "IMAGE_LOCATION_UNKNOWN",
            "INFO",
            "이미지 위치가 없어 본문 겹침 여부를 판단하지 않습니다.",
        )
    if chunk.document_type == "AMENDMENT_SUMMARY":
        add(
            "MIXED_PREVIOUS_REVISED",
            "REVIEW",
            "전체 본문을 현행 근거로 승인할 수 없습니다.",
        )
        if not chunk.application_note:
            add(
                "APPLICATION_NOTE_UNRESOLVED",
                "REVIEW",
                "별도 적용례 근거가 필요합니다.",
            )
    if chunk.document_type == "GUIDE" and chunk.declared_tax_year == 2025:
        add("HISTORICAL_2025", "REVIEW", "2026년 현행 근거로 자동 승격하지 않습니다.")
    if "<개정안" in chunk.content:
        add("DRAFT_TEXT", "REVIEW", "확정되지 않은 개정안/서식 후보입니다.")
    if official_reference is None:
        add(
            "OFFICIAL_COMPARISON_NOT_PERFORMED",
            "INFO",
            "검증된 공식 본문 스냅샷이 제공되지 않았습니다.",
        )
    else:
        result.extend(
            compare_text(chunk.content, official_reference, "제공된 공식 비교문")
        )
    return result
