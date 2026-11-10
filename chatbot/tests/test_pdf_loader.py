"""안전한 생성 PDF로 원문 보존·빈 페이지·추출 실패를 검증한다."""

from unittest.mock import Mock

import pymupdf
import pytest

from app.rag.loader import digest, extract_page, load_pdf
from app.rag.models import Config


def make_pdf(path, pages):
    with pymupdf.open() as pdf:
        for text in pages:
            page = pdf.new_page()
            if text:
                page.insert_text((70, 90), text, fontname="korea", fontsize=11)
        pdf.save(path)
    return path


def test_loader_preserves_source_and_reports_empty(tmp_path):
    path = make_pdf(
        tmp_path / "소득세법.pdf", ["제1조(목적)\n① 테스트 2026.1.1. 100원", ""]
    )
    before = path.read_bytes()
    result = load_pdf(path, Config())
    assert path.read_bytes() == before
    assert result.document_version == digest(before)
    assert [p.number for p in result.pages] == [1, 2]
    assert result.pages[1].status == "EMPTY"
    assert result.pages[1].review_reasons == ["NO_EXTRACTED_TEXT"]
    assert "2026.1.1." in "".join(line.text for line in result.pages[0].lines)


def test_page_failure_is_not_silently_skipped():
    page = Mock()
    page.rect.width, page.rect.height, page.rotation = 100, 200, 0
    page.get_text.side_effect = RuntimeError("테스트 오류")
    result = extract_page(page, 3, Config())
    assert result.number == 3
    assert result.status == "FAILED"
    assert result.review_reasons == ["PAGE_EXTRACTION_FAILED:RuntimeError"]


def test_broken_pdf_is_rejected(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(Exception):
        load_pdf(path, Config())


def test_encrypted_pdf_is_not_processed(tmp_path):
    path = tmp_path / "encrypted.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(
            path,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="test-owner",
            user_pw="test-user",
        )
    with pytest.raises(ValueError, match="암호화"):
        load_pdf(path, Config())


def test_table_cells_are_preserved(tmp_path):
    path = tmp_path / "테스트 신고안내.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for x in [70, 170, 270]:
            page.draw_line((x, 100), (x, 180))
        for y in [100, 140, 180]:
            page.draw_line((70, y), (270, y))
        for x, y, text in [
            (80, 120, "Previous"),
            (180, 120, "Revised"),
            (80, 160, "100"),
            (180, 160, "200"),
        ]:
            page.insert_text((x, y), text)
        pdf.save(path)
    result = load_pdf(path, Config())
    assert result.pages[0].tables[0].rows == [["Previous", "Revised"], ["100", "200"]]
    assert "TABLE_ALIGNMENT_REVIEW" in result.pages[0].tables[0].review_reasons


def test_merged_table_is_reviewed_without_filling_missing_cell(tmp_path):
    path = tmp_path / "병합 신고안내.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for x in [70, 270]:
            page.draw_line((x, 100), (x, 180))
        page.draw_line((170, 140), (170, 180))
        for y in [100, 140, 180]:
            page.draw_line((70, y), (270, y))
        page.insert_text((80, 120), "Merged heading")
        page.insert_text((80, 160), "Left")
        page.insert_text((180, 160), "Right")
        pdf.save(path)
    result = load_pdf(path, Config())
    table = result.pages[0].tables[0]
    assert any(cell is None for cell in table.cells)
    assert "MERGED_OR_MISSING_CELLS" in table.review_reasons
    assert table.rows[0][1] is None
