"""미리 고정한 독립 질문의 검색/범위/생성 검사를 분리해 기록한다."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.elasticsearch_documents import evaluation_documents  # noqa: E402
from app.rag.evaluation_rag import load_evaluation_rag  # noqa: E402
from app.rag.loader import digest  # noqa: E402
from scripts.evaluate_bm25 import score_question, summarize_rows  # noqa: E402
from scripts.run_rag_evaluation import (  # noqa: E402
    DEFAULT_EVIDENCE,
    DEFAULT_SELECTION,
    ROOT,
    save_report,
)


def questions_from_fixture(fixture, documents):
    questions = []
    for item in fixture["questions"]:
        relevant = [
            d
            for d in documents
            if not item.get("unresolved")
            and d["canonicalTitle"] == item.get("title")
            and d["article"] == item.get("article")
            and item.get("anchor") in d["content"]
        ]
        questions.append(
            {
                **item,
                "status": "OUT_OF_SCOPE"
                if item.get("outside")
                else "TEXT_LOCATOR"
                if relevant
                else "UNDETERMINED",
                "goldGroups": sorted({d["duplicateGroup"] for d in relevant}),
                "goldChunkIds": sorted(d["chunkId"] for d in relevant),
                "legalApplicability": "UNVERIFIED",
            }
        )
    return questions


async def evaluate_independent(runner, questions, generate_ids):
    rows = []
    generated = []
    for question in questions:
        search = runner.store.search_evaluation(question["query"])
        row = score_question(question, search["hits"])
        row["retrievalStatus"] = search["status"]
        row["intent"] = search["intent"]
        row["intentCorrect"] = search["intent"]["status"] == question["expectedIntent"]
        rows.append(row)
        generated.append(
            {
                "questionId": question["id"],
                **await runner.respond(
                    question["query"], generate=question["id"] in generate_ids
                ),
            }
        )
    return {
        "status": "EXECUTED",
        "usageScope": "EVALUATION_ONLY",
        "retrieval": summarize_rows(rows),
        "scopeAccuracy": sum(r["intentCorrect"] for r in rows) / len(rows),
        "scopeMismatches": [r["id"] for r in rows if not r["intentCorrect"]],
        "generation": generated,
        "modelCalls": sum(r["modelCalled"] for r in generated),
        "answeredSamples": sum(r["status"] == "ANSWERED" for r in generated),
        "groundedness": "REFERENCE_AND_NUMERIC_GUARDS_ONLY; semantic/legal review required",
        "datasetRole": "DEVELOPMENT_REGRESSION",
        "comparisonWarning": "현재 수정에 사용한 개발 회귀 세트. 새 독립/홀드아웃 성능으로 주장하지 않음.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument(
        "--questions",
        type=Path,
        default=ROOT / "tests/fixtures/independent_rag_questions.json",
    )
    parser.add_argument("--generate-ids", nargs="*", default=[])
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data/processed/independent-rag-evaluations",
    )
    args = parser.parse_args()
    fixture = json.loads(args.questions.read_text(encoding="utf-8"))
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    documents = evaluation_documents(selection, profile="quality-v2")
    questions = questions_from_fixture(fixture, documents)
    if not fixture.get("frozenBeforeRetrieval") or not set(args.generate_ids) <= {
        q["id"] for q in questions
    }:
        parser.error("고정된 질문 목록과 생성 대상 ID를 확인해주세요.")
    runner = load_evaluation_rag(args.selection, args.evidence_root)
    try:
        result = asyncio.run(
            evaluate_independent(runner, questions, set(args.generate_ids))
        )
    finally:
        runner.store.close()
    result["questionsFileHash"] = digest(args.questions.read_bytes())
    result["selectionHash"] = selection["selectionHash"]
    print(save_report(result, args.output_root))


if __name__ == "__main__":
    main()
