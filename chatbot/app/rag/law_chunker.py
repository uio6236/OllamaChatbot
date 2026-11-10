"""본문·부칙 범위를 유지하며 조문을 페이지 경계와 무관하게 연결한다."""

import re

ARTICLE = re.compile(r"^(제\s*\d+\s*조(?:의\s*\d+)?)(?=\s*\(|\s+삭제)")
SUPPLEMENT = re.compile(r"^부\s*칙(?:\s|<|$)")
CHAPTER = re.compile(r"^제\s*\d+\s*[장절관]\s")
MARKER = re.compile(r"^(?:[①-⑳㉑-㉟]|\d+\.|[가-하]\. |\d+\)|[가-하]\))")


def law_sections(pages):
    scope = "본문"
    scope_number = 0
    chapters = []
    article = None
    collected = []
    reasons = []
    path = [scope, "서문"]
    for page, lines in pages:
        if page.status in {"EMPTY", "FAILED", "PARTIAL"}:
            reasons.append("PAGE_EXTRACTION_GAP")
        for line in lines:
            text = line.text.strip()
            match = ARTICLE.match(text)
            supplement = SUPPLEMENT.match(text)
            chapter = CHAPTER.match(text)
            if match or supplement or chapter:
                if collected:
                    yield article, path, collected, sorted(set(reasons))
                collected = []
                reasons = []
                if supplement:
                    scope_number += 1
                    scope = f"부칙:{scope_number}:{text}"
                    chapters = []
                    article = None
                elif chapter:
                    chapters = [text]
                    article = None
                else:
                    article = re.sub(r"\s", "", match[1])
                path = [
                    scope,
                    *chapters,
                    article or (text if not supplement else "서문"),
                ]
            collected.append(line)
    if collected:
        yield article, path, collected, sorted(set(reasons))


def split_long(lines, max_chars):
    """항·호 경계를 우선한다. 한 원문 줄은 강제로 절단하지 않는다."""
    parts = []
    current = []
    length = 0
    for line in lines:
        if (
            current
            and length + len(line.text) > max_chars
            and MARKER.match(line.text.strip())
        ):
            parts.append(current)
            current = []
            length = 0
        current.append(line)
        length += len(line.text) + 1
    if current:
        parts.append(current)
    return parts


def markers(lines):
    return [
        {
            "lineId": line.line_id,
            "text": line.text,
            "marker": MARKER.match(line.text.strip())[0],
        }
        for line in lines
        if MARKER.match(line.text.strip())
    ]
