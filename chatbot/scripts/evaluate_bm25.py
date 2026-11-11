"""원문 위치 정답과 법적 적용 정답을 구분하는 평가 전용 CLI."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.elasticsearch_documents import evaluation_documents  # noqa: E402
from app.rag.elasticsearch_store import EvaluationSearchError, EvaluationStore  # noqa: E402
from app.rag.loader import digest  # noqa: E402
from app.rag.pipeline import canonical  # noqa: E402

# 원문 안에 실제 위치가 있는 경우에만 검색 위치 정답으로 연결한다.
# 적용연도에 대한 법적 정답을 제공하지 않는다.
QUESTIONS = {
    "RENT": [
        (
            "월세 세액공제 총급여와 종합소득 요건은?",
            "조세특례제한법",
            "제95조의2",
            "총급여",
        ),
        (
            "무주택 세대주와 세대원의 월세 요건은?",
            "조세특례제한법",
            "제95조의2",
            "세대주",
        ),
        (
            "주소가 다른 배우자의 월세 추가 공제 조건은?",
            "조세특례제한법",
            "제95조의2",
            "배우자",
        ),
        (
            "세대주와 배우자 월세액 합산 한도는?",
            "조세특례제한법",
            "제95조의2",
            "합계액",
        ),
        (
            "다자녀 월세 주택의 기준시가와 면적 요건은?",
            "조세특례제한법 시행령",
            "제95조",
            "기준시가",
        ),
        (
            "월세 계약 주소와 주민등록 주소 조건은?",
            "조세특례제한법 시행령",
            "제95조",
            "주소",
        ),
        (
            "월세 공제 신청 및 증빙을 정하는 조문은?",
            "조세특례제한법 시행령",
            "제95조",
            "신청",
        ),
        (
            "제21223호 월세 적용례는 어떤 지급분을 대상으로 하나?",
            "조세특례제한법",
            "제17조",
            "지급",
        ),
        (
            "2026년 1월 주말부부 월세에 2월 개정 시행령을 적용할 수 있나?",
            None,
            None,
            None,
        ),
        ("사업자의 상가 임대료 필요경비 공제는?", "OUT_OF_SCOPE", None, None),
    ],
    "CARD": [
        (
            "신용카드 등 사용금액 공제의 총급여 최저사용 기준은?",
            "조세특례제한법",
            "제126조의2",
            "총급여",
        ),
        (
            "체크카드와 현금영수증 공제 계산 규정은?",
            "조세특례제한법",
            "제126조의2",
            "현금영수증",
        ),
        (
            "전통시장과 대중교통 사용분은 어디에 규정되나?",
            "조세특례제한법",
            "제126조의2",
            "전통시장",
        ),
        ("문화체육 사용분과 총급여 요건은?", "조세특례제한법", "제126조의2", "도서"),
        (
            "자녀 수에 따른 카드 공제한도 규정은?",
            "조세특례제한법",
            "제126조의2",
            "자녀",
        ),
        (
            "카드 공제한도에 반영하는 자녀의 소득 나이 정의는?",
            "조세특례제한법 시행령",
            "제121조의2",
            "자녀",
        ),
        (
            "다른 거주자의 기본공제 자녀와 카드 공제한도 중복은?",
            "조세특례제한법 시행령",
            "제121조의2",
            "기본공제",
        ),
        (
            "교육비 세액공제와 신용카드 공제의 제외 규정은?",
            "조세특례제한법 시행령",
            "제121조의2",
            "교육비",
        ),
        ("2026년 1월부터 개정 자녀 정의가 모두 적용되나?", None, None, None),
        ("법인카드 매입세액 공제 방법은?", "OUT_OF_SCOPE", None, None),
    ],
    "HOUSING_SAVING": [
        (
            "주택청약 납입액 소득공제의 총급여 요건은?",
            "조세특례제한법",
            "제87조",
            "총급여",
        ),
        (
            "청약 소득공제의 무주택 세대주 배우자 요건은?",
            "조세특례제한법",
            "제87조",
            "배우자",
        ),
        (
            "청약 납입액 공제의 연간 한도와 공제율은?",
            "조세특례제한법",
            "제87조",
            "납입",
        ),
        (
            "주택청약 납입 소득공제와 이자 비과세를 구분하는 조문은?",
            "조세특례제한법",
            "제87조",
            "비과세",
        ),
        ("청약 중도해지 추징과 예외 규정은?", "조세특례제한법", "제87조", "해지"),
        (
            "무주택확인서 제출 조건을 정하는 시행령은?",
            "조세특례제한법 시행령",
            "제81조",
            "무주택",
        ),
        (
            "청약 저축 해지 추징의 예외 사유는?",
            "조세특례제한법 시행령",
            "제81조",
            "해지",
        ),
        (
            "주택마련저축납입증명서 제출과 대체 서류는?",
            "조세특례제한법 시행규칙",
            "제34조",
            "납입증명서",
        ),
        (
            "청약 배우자 확대가 모든 기존 가입자의 2026년 납입분에 적용되나?",
            None,
            None,
            None,
        ),
        ("주택 임대사업자 양도소득세 감면 조건은?", "OUT_OF_SCOPE", None, None),
    ],
}


def make_questions(documents):
    result = []
    for topic, entries in QUESTIONS.items():
        for i, (query, title, article, needle) in enumerate(entries, 1):
            relevant = [
                d
                for d in documents
                if d["canonicalTitle"] == title
                and d["article"] == article
                and needle
                and needle in d["content"]
            ]
            status = (
                "OUT_OF_SCOPE"
                if title == "OUT_OF_SCOPE"
                else "TEXT_LOCATOR"
                if relevant
                else "UNDETERMINED"
            )
            result.append(
                {
                    "id": f"{topic}-{i:02}",
                    "topic": topic,
                    "query": query,
                    "status": status,
                    "goldGroups": sorted({d["duplicateGroup"] for d in relevant}),
                    "goldChunkIds": sorted(d["chunkId"] for d in relevant),
                    "anchor": needle,
                    "legalApplicability": "UNVERIFIED",
                }
            )
    return result


def score_question(question, hits):
    gold = set(question["goldGroups"])
    groups = [h["duplicateGroup"] for h in hits]
    ranks = [i + 1 for i, group in enumerate(groups) if group in gold]
    return {
        **question,
        "hits": hits,
        "relevantRanks": ranks,
        "recallAt5": len(gold & set(groups[:5])) / len(gold) if gold else None,
        "reciprocalRank": 1 / min(ranks) if ranks else 0 if gold else None,
        "otherTopicResults": [
            h["chunkId"] for h in hits if question["topic"] not in h["topics"]
        ],
        "outOfScopeExposure": bool(hits)
        if question["status"] == "OUT_OF_SCOPE"
        else None,
        "mixedOrHistoricalRisk": any(
            h["textRole"] in {"PREVIOUS_AND_REVISED", "AMENDMENT_TEXT"}
            or any(
                v["documentVersion"] != h["documentVersion"]
                for v in h.get("variants", [])
            )
            for h in hits
        ),
    }


def evaluate(questions, store):
    rows = [score_question(q, store.search(q["query"], size=10)) for q in questions]
    scored = [r for r in rows if r["status"] == "TEXT_LOCATOR"]
    return {
        "status": "EXECUTED",
        "scoredQuestions": len(scored),
        "recallAt5": sum(r["recallAt5"] for r in scored) / len(scored)
        if scored
        else None,
        "mrrAt10": sum(r["reciprocalRank"] for r in scored) / len(scored)
        if scored
        else None,
        "metricUnit": "deduplicated article group; not legal correctness",
        "questions": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data/processed/bm25-evaluations",
    )
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    documents = evaluation_documents(selection)
    questions = make_questions(documents)
    store = EvaluationStore(selection["selectionHash"])
    try:
        server = store.health()
        integrity = store.verify(documents)
        result = {
            **evaluate(questions, store),
            "server": server,
            "indexIntegrity": integrity,
        }
    except EvaluationSearchError as exc:
        result = {
            "status": "NOT_EXECUTED",
            "reason": str(exc),
            "recallAt5": None,
            "mrrAt10": None,
            "questions": questions,
        }
    finally:
        store.close()
    result["selectionHash"] = selection["selectionHash"]
    result["usageScope"] = "EVALUATION_ONLY"
    result["questionsHash"] = digest(canonical(questions).encode())
    root = args.output_root.resolve()
    if not root.is_relative_to(
        (Path(__file__).resolve().parents[1] / "data/processed").resolve()
    ):
        parser.error("결과는 chatbot/data/processed 하위에 저장합니다.")
    path = root / digest(canonical(result).encode())
    path.mkdir(parents=True, exist_ok=True)
    file = path / "evaluation.json"
    if file.exists() and json.loads(file.read_text(encoding="utf-8")) != result:
        parser.error("기존 결과를 덮어쓸 수 없습니다.")
    if not file.exists():
        file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(file)
    return 0 if result["status"] == "EXECUTED" else 2


if __name__ == "__main__":
    sys.exit(main())
