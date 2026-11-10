"""안내서는 조문으로 분류하지 않는다. 표는 자동 의미 병합하지 않는다."""

import re

HEADING = re.compile(
    r"^(?:제\s*\d+\s*[장절]|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[.． ]|\d+[.． ]|[가-하][.)])"
)


def guide_sections(pages, max_chars):
    path = ["안내서"]
    for page, lines in pages:
        collected = []
        for line in lines:
            heading = HEADING.match(line.text.strip()) and line.font_size >= 11
            # 표에 속한 줄은 중간 제목으로 오인하지 않는다.
            in_table = any(
                t.bbox[0] <= line.bbox[0] <= t.bbox[2]
                and t.bbox[1] <= line.bbox[1] <= t.bbox[3]
                for t in page.tables
            )
            if heading and not in_table:
                if collected:
                    yield None, path, collected, ["GUIDE_HEADING_REVIEW"]
                collected = []
                path = ["안내서", line.text.strip()]
            collected.append(line)
        if collected:
            # 경계가 불명확한 계속 표는 원문 보존 후 검토 대상으로 남긴다.
            reasons = ["GUIDE_HEADING_REVIEW", "PAGE_CONTINUATION_REVIEW"]
            if sum(len(line.text) for line in collected) > max_chars:
                reasons.append("LONG_GUIDE_SECTION")
            yield None, path, collected, reasons
