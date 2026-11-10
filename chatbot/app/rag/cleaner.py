"""원문을 바꾸지 않고 확실한 반복 가장자리 문구만 청킹 대상에서 제외한다."""

import re
from collections import Counter

from app.rag.models import Exclusion, RawDocument


def clean_document(doc: RawDocument):
    repeated = Counter()
    for page in doc.pages:
        repeated.update(
            set(
                line.text.strip()
                for line in page.lines
                if line.bbox[3] < 65 or line.bbox[1] > page.height - 45
            )
        )
    kept = []
    excluded = []
    for page in doc.pages:
        lines = []
        for line in sorted(page.lines, key=lambda x: (x.bbox[1], x.bbox[0], x.line_id)):
            text = line.text.strip()
            edge = line.bbox[3] < 65 or line.bbox[1] > page.height - 45
            reason = None
            if not text:
                reason = "WHITESPACE"
            elif edge and doc.document_type in {"LAW", "DECREE", "RULE"}:
                if text in {"법제처", "국가법령정보센터"} or re.fullmatch(
                    r"법제처\s+\d+\s+국가법령정보센터", text
                ):
                    reason = "LAW_RUNNING_HEADER"
                elif text == doc.document_title and repeated[text] >= 2:
                    reason = "REPEATED_DOCUMENT_TITLE"
                elif text.isdecimal() and line.bbox[3] < 35:
                    reason = "LAW_HEADER_PAGE_NUMBER"
            if reason:
                excluded.append(Exclusion(line=line, reason=reason))
            else:
                lines.append(line)
        kept.append((page, lines))
    return kept, excluded
