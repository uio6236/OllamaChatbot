"""PyMuPDF 페이지 추출. 빈 페이지·부분 실패도 반드시 결과에 남긴다."""

import hashlib
import re
from pathlib import Path

import pymupdf

from app.rag.models import Config, Line, Page, RawDocument, Table


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def document_kind(name: str) -> str:
    if "개정세법" in name:
        return "AMENDMENT_SUMMARY"
    if "신고안내" in name:
        return "GUIDE"
    if "시행규칙" in name:
        return "RULE"
    if "시행령" in name:
        return "DECREE"
    return "LAW"


def extract_page(page, number: int, config: Config) -> Page:
    result = Page(
        number=number,
        width=page.rect.width,
        height=page.rect.height,
        rotation=page.rotation,
        status="OK",
    )
    try:
        # 이미지 바이트를 중간 JSON에 복사하지 않는다. 텍스트와 좌표는 보존한다.
        data = page.get_text(
            "dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
        )
        for bi, block in enumerate(data["blocks"]):
            for li, line in enumerate(block.get("lines", [])):
                spans = line["spans"]
                result.lines.append(
                    Line(
                        line_id=f"p{number}:b{bi}:l{li}",
                        page=number,
                        bbox=line["bbox"],
                        text="".join(s["text"] for s in spans),
                        font_size=max((s["size"] for s in spans), default=0),
                    )
                )
        result.image_count = len(page.get_images())
        if result.image_count:
            result.review_reasons.append("IMAGE_REGIONS_NOT_OCR")
        if not any(line.text.strip() for line in result.lines):
            result.status = "EMPTY"
            result.review_reasons.append("NO_EXTRACTED_TEXT")
        if any("\ufffd" in line.text for line in result.lines):
            result.review_reasons.append("REPLACEMENT_CHARACTER")
        if config.detect_tables:
            try:
                for table in page.find_tables().tables:
                    rows = table.extract()
                    # table.cells는 실제 사각형만 반환한다. 행별 cells에는 병합 자리의 None도 있다.
                    cells = [cell for row in table.rows for cell in row.cells]
                    reasons = ["TABLE_ALIGNMENT_REVIEW"]
                    if any(cell is None for cell in cells):
                        reasons.append("MERGED_OR_MISSING_CELLS")
                    result.tables.append(
                        Table(
                            bbox=table.bbox,
                            rows=rows,
                            cells=cells,
                            review_reasons=reasons,
                        )
                    )
            except Exception as exc:
                result.status = "PARTIAL" if result.lines else "FAILED"
                result.review_reasons.append(
                    f"TABLE_EXTRACTION_FAILED:{type(exc).__name__}"
                )
    except Exception as exc:
        result.status = "FAILED"
        result.review_reasons.append(f"PAGE_EXTRACTION_FAILED:{type(exc).__name__}")
    return result


def load_pdf(path: Path, config: Config) -> RawDocument:
    version = digest(path.read_bytes())
    with pymupdf.open(path) as pdf:
        if pdf.needs_pass:
            raise ValueError("암호화 PDF는 자동 처리하지 않습니다.")
        pages = [extract_page(page, i + 1, config) for i, page in enumerate(pdf)]
    kind = document_kind(path.name)
    title = (
        re.split(r"\(", path.stem)[0]
        if kind in {"LAW", "DECREE", "RULE"}
        else path.stem
    )
    header = "\n".join(line.text for line in pages[0].lines) if pages else ""
    tail = "\n".join(line.text for page in pages[-2:] for line in page.lines)
    publication = re.search(r"발행일자\s*(\d{4})\s*년", tail)
    label = re.search(r"(20\d{2})년", header)
    match = re.search(r"\[시행\s+(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.", header)
    effective = (
        "-".join([match[1], match[2].zfill(2), match[3].zfill(2)]) if match else None
    )
    return RawDocument(
        source_file=path.name,
        document_version=version,
        document_title=title,
        document_type=kind,
        pages=pages,
        document_effective_date=effective,
        declared_tax_year=2025 if kind == "GUIDE" and "2025" in path.name else None,
        publication_year=int(publication[1]) if publication else None,
        document_label_year=int(label[1]) if label else None,
    )
