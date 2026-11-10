"""조문·부칙 경계와 페이지 연속성은 가상 원문으로 검증한다."""

from test_pdf_loader import make_pdf

from app.rag.cleaner import clean_document
from app.rag.documents import to_document, to_source
from app.rag.law_chunker import law_sections, split_long
from app.rag.models import Config, Line, Page, RawDocument
from app.rag.pipeline import process_document


def line(text, page=1, index=0, y=100):
    return Line(
        line_id=f"p{page}:b{index}:l0",
        page=page,
        bbox=(70, y, 500, y + 10),
        text=text,
        font_size=11,
    )


def test_article_crosses_page_but_does_not_mix_other_article():
    a, b = line("제1조(목적) 테스트"), line("② 다음 페이지 이어짐", 2)
    c = line("제2조(정의) 새 조문", 2, 1)
    pages = [
        (Page(number=1, width=595, height=842, rotation=0, status="OK"), [a]),
        (Page(number=2, width=595, height=842, rotation=0, status="OK"), [b, c]),
    ]
    sections = list(law_sections(pages))
    assert [s[0] for s in sections] == ["제1조", "제2조"]
    assert [x.page for x in sections[0][2]] == [1, 2]
    assert "새 조문" not in "".join(x.text for x in sections[0][2])


def test_body_supplement_and_references_are_distinct():
    texts = [
        "제1조(목적) 본문",
        "제2조에 따른 참조",
        "부칙 <제123호>",
        "제1조(시행일) 2026.1.1.",
        "제2조 삭제 <2025.1.1.>",
    ]
    lines = [line(t, index=i) for i, t in enumerate(texts)]
    page = Page(number=1, width=595, height=842, rotation=0, status="OK")
    sections = list(law_sections([(page, lines)]))
    assert sections[0][1][0] == "본문"
    assert len(sections[0][2]) == 2
    assert sections[2][1][0].startswith("부칙:")
    assert sections[-1][0] == "제2조"


def test_split_keeps_lines_and_numbering():
    lines = [
        line("제1조(목적)", index=0),
        line("① " + "가" * 120, index=1),
        line("② " + "나" * 120, index=2),
    ]
    parts = split_long(lines, 150)
    assert len(parts) == 2
    assert [x for part in parts for x in part] == lines


def test_repeated_body_is_not_deleted():
    pages = [
        Page(
            number=n,
            width=595,
            height=842,
            rotation=0,
            status="OK",
            lines=[line("제1조(목적) 반복 내용", n)],
        )
        for n in [1, 2]
    ]
    doc = RawDocument(
        source_file="test.pdf",
        document_version="test",
        document_title="법",
        document_type="LAW",
        pages=pages,
    )
    kept, removed = clean_document(doc)
    assert sum(len(lines) for page, lines in kept) == 2
    assert not removed


def test_source_contract_and_langchain_adapter(tmp_path):
    path = make_pdf(
        tmp_path / "소득세법.pdf",
        ["제1조(목적) 테스트", "② 계속\n제2조 삭제 <2025.1.1.>"],
    )
    raw, exclusions, chunks, report = process_document(path, Config())
    source = to_source(chunks[0])
    assert source.page_start == 1 and source.page_end == 2
    assert not source.applicability_verified and source.applicable_tax_year is None
    assert source.source_url is None
    assert to_document(chunks[0]).id == chunks[0].chunk_id
    assert report["uncoveredLineIds"] == []
    assert report["humanReviewPassed"] == report["retrievalReady"] == 0
