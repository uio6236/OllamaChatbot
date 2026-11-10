"""영역·비교표 분석. 좌동과 병합 셀의 의미를 임의로 채우지 않는다."""

import re

from app.rag.models import Line, Page

INCOME_TYPES = {
    "근로소득": "EARNED",
    "사업소득": "BUSINESS",
    "종교인소득": "RELIGIOUS",
    "연금소득": "PENSION",
}
AMENDMENT_HEADING = re.compile(r"^\d{1,2}\.\s*\S")


def amendment_regions(page: Page, lines: list[Line]):
    """가로 페이지는 개정 제목의 실제 좌우 위치를 확인해 영역을 나눈다."""
    headings = [line for line in lines if AMENDMENT_HEADING.match(line.text.strip())]
    two_columns = (
        page.width > page.height
        and any(line.bbox[0] < page.width / 2 for line in headings)
        and any(line.bbox[0] > page.width / 2 for line in headings)
    )
    groups = [[], []] if two_columns else [[]]
    for line in lines:
        side = int(line.bbox[0] >= page.width / 2) if two_columns else 0
        groups[side].append(line)
    result = []
    for side, group in enumerate(groups):
        current = []
        for line in sorted(group, key=lambda x: (x.bbox[1], x.bbox[0], x.line_id)):
            if AMENDMENT_HEADING.match(line.text.strip()) and any(
                AMENDMENT_HEADING.match(old.text.strip()) for old in current
            ):
                result.append((side, current))
                current = []
            current.append(line)
        if current:
            result.append((side, current))
    return result


def comparison(lines: list[Line]) -> dict:
    headers = {}
    header_count = 0
    for line in lines:
        compact = re.sub(r"\s", "", line.text)
        if compact in {"종전", "개정"}:
            header_count += 1
            headers[compact] = line
    notes = [line for line in lines if "적용시기" in line.text or "적용례" in line.text]
    reasons = ["COMPARISON_ALIGNMENT_REQUIRES_REVIEW"]
    if header_count > 2:
        reasons.append("MULTIPLE_COMPARISONS_UNRESOLVED")
    previous = []
    revised = []
    rows = []
    if len(headers) == 2:
        left, right = headers["종전"], headers["개정"]
        split = (
            (left.bbox[0] + left.bbox[2]) / 2 + (right.bbox[0] + right.bbox[2]) / 2
        ) / 2
        start = max(left.bbox[3], right.bbox[3])
        end = min((line.bbox[1] for line in notes), default=float("inf"))
        body = [line for line in lines if line.bbox[1] >= start and line.bbox[1] < end]
        for line in body:
            (previous if line.bbox[0] < split else revised).append(line)
            if line.bbox[0] < split < line.bbox[2]:
                reasons.append("CROSSES_COMPARISON_COLUMN")
            row = next((r for r in rows if abs(r["y"] - line.bbox[1]) < 3), None)
            if row is None:
                row = {
                    "y": line.bbox[1],
                    "previous": [],
                    "revised": [],
                    "sourceLineIds": [],
                }
                rows.append(row)
            key = "previous" if line.bbox[0] < split else "revised"
            row[key].append(line.text)
            row["sourceLineIds"].append(line.line_id)
    else:
        reasons.append("COMPARISON_HEADERS_UNRESOLVED")
    if not notes:
        reasons.append("APPLICATION_NOTE_NOT_EXPLICIT")
    note_start = min((line.bbox[1] for line in notes), default=float("inf"))
    purpose = [line.text for line in lines if "개정취지" in line.text]
    return {
        "previous_rule": "\n".join(line.text for line in previous) or None,
        "revised_rule": "\n".join(line.text for line in revised) or None,
        "application_note": "\n".join(
            line.text for line in lines if line.bbox[1] >= note_start
        )
        or None,
        "amendment_purpose": "\n".join(purpose) or None,
        "related_articles": [
            line.text
            for line in lines
            if "법" in line.text
            and ("조" in line.text or "별표" in line.text)
            and line.bbox[1]
            < min((h.bbox[1] for h in headers.values()), default=float("inf"))
        ],
        "comparison_rows": rows,
        "review_reasons": sorted(set(reasons)),
    }


def overlapping_tables(page: Page, lines: list[Line]):
    if not lines:
        return []
    return [
        table
        for table in page.tables
        if any(
            line.bbox[0] < table.bbox[2]
            and line.bbox[2] > table.bbox[0]
            and line.bbox[1] < table.bbox[3]
            and line.bbox[3] > table.bbox[1]
            for line in lines
        )
    ]
