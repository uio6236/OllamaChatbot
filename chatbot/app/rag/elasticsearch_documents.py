"""평가 전용 문서 변환. 운영 승인 문서를 만드는 어댑터가 아니다."""

from app.rag.loader import digest
from app.rag.pipeline import canonical
from app.rag.scope import validate_selection


def evaluation_documents(selection):
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
            }
        )
    if len({d["id"] for d in documents}) != len(documents):
        raise ValueError("중복 검색 문서 ID입니다.")
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
