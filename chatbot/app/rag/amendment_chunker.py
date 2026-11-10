"""소득 유형과 좌우 개정 항목을 분리한다. 의미 확정은 수동 검토로 남긴다."""

import re

from app.rag.layout import (
    AMENDMENT_HEADING,
    INCOME_TYPES,
    amendment_regions,
    comparison,
)


def amendment_sections(pages):
    income_type = None
    for page, lines in pages:
        for side, region in amendment_regions(page, lines):
            for line in region:
                compact = re.sub(r"\s", "", line.text)
                if compact in INCOME_TYPES:
                    income_type = INCOME_TYPES[compact]
            headings = [
                line.text.strip()
                for line in region
                if AMENDMENT_HEADING.match(line.text.strip())
            ]
            title = headings[0] if headings else None
            # 원형번호 하위 제목 뒤에 개정취지가 따라오는 경우 별도 비교 묶음이다.
            starts = [
                i
                for i, line in enumerate(region)
                if re.match(r"^[①-⑳]\s*\S", line.text.strip())
                and i + 1 < len(region)
                and "개정취지" in region[i + 1].text
            ]
            boundaries = [0, *starts[1:], len(region)] if starts else [0, len(region)]
            inherited_articles = comparison(region)["related_articles"]
            for part_index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
                part = region[start:end]
                extra = comparison(part)
                reasons = extra.pop("review_reasons")
                if not title:
                    reasons.append("AMENDMENT_TITLE_UNRESOLVED")
                if income_type is None:
                    reasons.append("INCOME_TYPE_UNRESOLVED")
                extra.update(
                    amendment_title=title,
                    sub_amendment_title=region[starts[part_index]].text
                    if starts
                    else None,
                    related_articles=extra["related_articles"] or inherited_articles,
                    section_income_type=income_type,
                    income_type=[income_type] if income_type else [],
                )
                yield (
                    None,
                    [
                        income_type or "미확인",
                        title or "미확인",
                        f"p{page.number}:region{side}:part{part_index}",
                    ],
                    part,
                    reasons,
                    extra,
                )
