"""평가 전용 문서 변환. 운영 승인 문서를 만드는 어댑터가 아니다."""

import re

from app.rag.loader import digest
from app.rag.pipeline import canonical
from app.rag.scope import validate_selection


def source_metadata(row):
    if row["documentType"] == "AMENDMENT_SUMMARY":
        kind = "AMENDMENT_SUMMARY"
    elif row["textRole"] == "AMENDMENT_TEXT":
        kind = "AMENDMENT_TEXT"
    elif any(r["role"] == "APPLICATION" for r in row["contextRegions"]):
        kind = "SUPPLEMENT"
    else:
        kind = {"LAW": "LAW_BODY", "DECREE": "DECREE_BODY", "RULE": "RULE_BODY"}.get(
            row["documentType"], "UNKNOWN"
        )
    match = re.match(r"\s*제\d+조(?:의\d+)?\s*\(([^)]+)\)", row["content"])
    title = match.group(1) if match else ""
    labels = {
        "RENT": "월세 세액공제 임차료 집세",
        "CARD": "신용카드 체크카드 현금영수증 소득공제",
        "HOUSING_SAVING": "주택청약종합저축 주택마련저축 납입액 소득공제",
    }
    return {
        "sourceKind": kind,
        "articleTitle": title,
        "featureNames": " ".join(labels[t] for t in row["topics"] if t in labels),
        "legalVersions": sorted(
            {e["lawVersion"] for e in row.get("officialEvidenceLinks", [])}
        ),
        "comparisonOnly": kind == "AMENDMENT_SUMMARY",
        "legalApplicability": "UNVERIFIED",
    }


def evaluation_documents(selection, *, profile="baseline"):
    if profile not in {"baseline", "quality-v2"}:
        raise ValueError("평가 문서 프로필이 다릅니다.")
    validate_selection(selection)
    if selection["mode"] != "initial":
        raise ValueError("이번 색인은 initial 범위만 허용합니다.")
    documents = []
    for row in selection["candidates"]:
        if (
            row.get("usageScope"),
            row.get("verificationStatus"),
            row.get("approvalStatus"),
        ) != ("EVALUATION_ONLY", "UNVERIFIED", "HOLD"):
            raise ValueError("평가 문서의 신뢰 경계가 다릅니다.")
        documents.append(
            {
                "id": digest(
                    canonical(
                        ["eval-document-v1", selection["selectionHash"], row["chunkId"]]
                    ).encode()
                ),
                **row,
                "selectionHash": selection["selectionHash"],
                **(source_metadata(row) if profile == "quality-v2" else {}),
            }
        )
    if len({d["id"] for d in documents}) != len(documents):
        raise ValueError("중복 검색 문서 ID입니다.")
    if profile == "quality-v2":
        titles = {
            d["duplicateGroup"]: d["articleTitle"]
            for d in documents
            if d["articleTitle"]
        }
        for document in documents:
            document["articleTitle"] = document["articleTitle"] or titles.get(
                document["duplicateGroup"], ""
            )
    return documents


def reject_operational_input(documents):
    """원본/평가 문서의 운영 전용 입력 혼입을 차단한다. 운영 적재는 미구현."""
    for document in documents:
        if (
            document.get("usageScope") != "CURRENT_2026"
            or document.get("schemaVersion") != "approved-context-v3"
        ):
            raise ValueError("운영에는 v3 승인 내보내기와 최신 원장 검사가 필요합니다.")
    raise ValueError("이번 단계에서 운영 색인은 지원하지 않습니다.")
