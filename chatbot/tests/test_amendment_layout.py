"""다단 항목과 종전·개정의 두 단계 열 구조를 구분한다."""

from app.rag.amendment_chunker import amendment_sections
from app.rag.models import Line, Page


def item(text, x, y, index):
    return Line(
        line_id=f"p1:b{index}:l0",
        page=1,
        bbox=(x, y, x + 60, y + 8),
        text=text,
        font_size=10,
    )


def test_two_regions_each_have_previous_and_revised():
    texts = [
        ("근로소득", 40, 20),
        ("1. 테스트 개정", 40, 40),
        ("[개정취지] 테스트", 40, 60),
        ("종 전", 70, 80),
        ("개 정", 250, 80),
        ("종전 값 100", 40, 100),
        ("개정 값 200", 220, 100),
        ("☞ 적용시기 및 적용례", 40, 150),
        ("2025.1.1. 이후", 40, 170),
        ("2. 다른 항목", 470, 40),
        ("종 전", 500, 80),
        ("개 정", 680, 80),
        ("종전 값 300", 470, 100),
        ("개정 값 400", 650, 100),
        ("☞ 적용시기 및 적용례", 470, 150),
        ("2027.1.1. 이후", 470, 170),
    ]
    lines = [item(t, x, y, i) for i, (t, x, y) in enumerate(texts)]
    page = Page(number=1, width=841, height=595, rotation=0, status="OK", lines=lines)
    sections = list(amendment_sections([(page, lines)]))
    assert len(sections) == 2
    first, second = sections[0][-1], sections[1][-1]
    assert first["previous_rule"] == "종전 값 100"
    assert first["revised_rule"] == "개정 값 200"
    assert "2025" in first["application_note"]
    assert "2027" in second["application_note"]
    assert second["income_type"] == ["EARNED"]
    assert "300" not in first["previous_rule"]


def test_same_title_across_income_types_is_not_deduplicated():
    pages = []
    for number, income in enumerate(["근로소득", "종교인소득"], 1):
        lines = [
            item(income, 40, 20, number * 10),
            item("1. 반복 제목", 40, 40, number * 10 + 1),
        ]
        page = Page(
            number=number, width=595, height=841, rotation=0, status="OK", lines=lines
        )
        pages.append((page, lines))
    sections = list(amendment_sections(pages))
    assert len(sections) == 2
    assert [s[-1]["income_type"] for s in sections] == [["EARNED"], ["RELIGIOUS"]]
    assert "COMPARISON_HEADERS_UNRESOLVED" in sections[0][3]


def test_multiple_comparisons_within_one_amendment_stay_with_own_notes():
    texts = [
        ("근로소득", 40, 10),
        ("1. 복수 개정", 40, 25),
        ("① 첫 세부 항목", 40, 40),
        ("[개정취지] 첫 취지", 40, 55),
        ("종 전", 70, 70),
        ("개 정", 250, 70),
        ("종전 100", 40, 90),
        ("개정 200", 220, 90),
        ("☞ 적용시기 및 적용례", 40, 110),
        ("2025.1.1.", 40, 125),
        ("② 다음 세부 항목", 40, 150),
        ("[개정취지] 다음 취지", 40, 165),
        ("종 전", 70, 180),
        ("개 정", 250, 180),
        ("종전 300", 40, 200),
        ("개정 400", 220, 200),
        ("☞ 적용시기 및 적용례", 40, 220),
        ("2027.1.1.", 40, 235),
    ]
    lines = [item(t, x, y, i) for i, (t, x, y) in enumerate(texts)]
    page = Page(number=1, width=595, height=841, rotation=0, status="OK", lines=lines)
    sections = list(amendment_sections([(page, lines)]))
    assert len(sections) == 2
    assert "2025" in sections[0][-1]["application_note"]
    assert "2027" not in sections[0][-1]["application_note"]
    assert sections[1][-1]["previous_rule"] == "종전 300"
    assert "②" in sections[1][-1]["sub_amendment_title"]
