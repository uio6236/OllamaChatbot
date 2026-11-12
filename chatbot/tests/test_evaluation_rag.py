"""평가 전용 생성, 실패·보류와 실제 서버 선택 실행을 구분한다."""

import asyncio
import json
import os
from unittest.mock import Mock

import pytest
from test_evidence_bundles import fixture_bundle

from app.rag.elasticsearch_store import EvaluationSearchError
from app.rag.evaluation_rag import EvaluationRag, load_evaluation_rag
from app.services.generation import GenerationService, UnavailableRetriever


class LocalFakeStore:
    def __init__(self, document):
        self.document = document
        self.status = "RETRIEVED_UNVERIFIED"
        self.calls = 0

    def search_evaluation(self, question):
        return {
            "status": self.status,
            "intent": {"status": "IN_SCOPE", "topics": ["RENT"], "reason": "가상 평가"},
            "hits": [self.document] if self.status == "RETRIEVED_UNVERIFIED" else [],
        }

    def request(self, method, path, **kwargs):
        self.calls += 1
        return {
            "docs": [
                {"found": True, "_id": self.document["id"], "_source": self.document}
            ]
        }

    index = "hope-rag-eval-mock"


def fixture_runner(tmp_path):
    _, chunk, _, record, row = fixture_bundle(tmp_path)
    record = record.model_copy(update={"approval_target_id": "rent-2026-spouse-cap"})
    row.update(
        {
            "score": 1,
            "article": chunk.article,
            "documentTitle": chunk.document_title,
            "sourceFile": chunk.source_file,
        }
    )
    store = LocalFakeStore(row)
    model = Mock()
    model.generate_grounded.return_value = '{"status":"ANSWERED","answer":"가상 조건 확인이 필요합니다 [E1]","citations":["E1"]}'
    generation = GenerationService(UnavailableRetriever(), model)
    return EvaluationRag(
        store, [row], [record], {chunk.chunk_id: chunk}, tmp_path, generation=generation
    ), model


def test_mock_full_path_and_trace(tmp_path):
    runner, model = fixture_runner(tmp_path)
    result = asyncio.run(runner.respond("월세 공제 질문"))
    assert result["status"] == "ANSWERED"
    assert result["modelCalled"] and not result["answerUseAllowed"]
    assert result["answer"].startswith("[평가용·미검증]")
    system, data = model.generate_grounded.call_args.args
    assert "UNVERIFIED" in system
    assert len(json.loads(data)["evidence"]) == len(result["modelEvidence"])


@pytest.mark.parametrize("status", ["OUT_OF_SCOPE", "INSUFFICIENT_EVIDENCE"])
def test_no_generation_without_search_evidence(tmp_path, status):
    runner, model = fixture_runner(tmp_path)
    runner.store.status = status
    result = asyncio.run(runner.respond("질문"))
    assert result["status"] == status and not result["modelCalled"]
    assert runner.store.calls == 0
    model.generate_grounded.assert_not_called()


def test_search_failure_no_fallback(tmp_path):
    runner, model = fixture_runner(tmp_path)
    runner.store.search_evaluation = Mock(
        side_effect=EvaluationSearchError("EVAL_ELASTICSEARCH_REQUEST_FAILED")
    )
    result = asyncio.run(runner.respond("질문"))
    assert result["status"] == "INSUFFICIENT_EVIDENCE" and not result["modelCalled"]
    model.generate_grounded.assert_not_called()


def test_budget_exceeded_never_calls_model(tmp_path):
    runner, model = fixture_runner(tmp_path)
    runner.context_window = 100
    result = asyncio.run(runner.respond("월세 공제"))
    assert result["holdReason"] == "CONTEXT_BUDGET_WHOLE_BUNDLE_HELD"
    model.generate_grounded.assert_not_called()


def test_model_withheld_does_not_publish_candidate_answer(tmp_path):
    runner, model = fixture_runner(tmp_path)
    model.generate_grounded.return_value = '{"status":"INSUFFICIENT_EVIDENCE","answer":"가상 설명 [E1]","citations":["E1"]}'
    result = asyncio.run(runner.respond("월세 공제"))
    assert result["answer"] is None and result["holdReason"] == "MODEL_WITHHELD"


def test_independent_fixture_frozen_and_not_old_benchmark():
    from pathlib import Path

    from app.rag.loader import digest
    from scripts.evaluate_bm25 import QUESTIONS

    file = Path(__file__).parent / "fixtures/independent_rag_questions.json"
    assert (
        digest(file.read_bytes())
        == "2446fa0161a6ba5dc4b4d1945b4cccd6faa4da19437adf70ac5e4ec258baa71e"
    )
    dataset = json.loads(file.read_text(encoding="utf-8"))
    assert dataset["frozenBeforeRetrieval"]
    assert len(dataset["questions"]) == 24
    assert not {q["query"] for q in dataset["questions"]} & {
        q[0] for rows in QUESTIONS.values() for q in rows
    }


def test_grouped_citation_regression_is_real_and_not_answer_approval(tmp_path):

    from app.rag.evaluation_rag import check_model_answer, diagnose_model_answer

    # 실모델 관찰과 같은 표기. 법적 내용은 가상이며 기존 source 승인 상태를 바꾸지 않는다.
    bundle, *_ = fixture_bundle(tmp_path)
    raw = '{"status":"INSUFFICIENT_EVIDENCE","answer":"추가 확인이 필요합니다 [E1, E2, E3].","citations":["E1","E2","E3"]}'
    assert check_model_answer(raw, bundle)[1] is None
    assert diagnose_model_answer(raw, bundle)["numericMatches"] == []
    assert diagnose_model_answer(raw, bundle)["normalizationsApplied"] == [
        "groupedCitationIds"
    ]
    runner, model = fixture_runner(tmp_path)
    model.generate_grounded.return_value = raw
    result = asyncio.run(runner.respond("월세 공제"))
    assert result["answer"] is None and result["holdReason"] == "MODEL_WITHHELD"


@pytest.mark.parametrize("notation", ["[E1, E99]", "[E1-E3]", "[E1, URL]", "[E1]"])
def test_grouped_citation_does_not_fix_unknown_range_or_missing_ids(tmp_path, notation):
    from app.rag.evaluation_rag import check_model_answer

    bundle, *_ = fixture_bundle(tmp_path)
    raw = json.dumps(
        {
            "status": "ANSWERED",
            "answer": "가상 설명 " + notation,
            "citations": ["E1", "E2", "E3"],
        }
    )
    assert check_model_answer(raw, bundle)[1] == "UNTRACEABLE_CITATION"


def test_prompt_focus_preserves_entire_bundle_not_an_answer_template(tmp_path):
    from app.rag.evaluation_rag import pack_prompt, question_focus

    bundle, *_ = fixture_bundle(tmp_path)
    focus = question_focus("월세 소득공제 요건", bundle)
    assert "primaryEvidenceIds" in focus
    assert "answer" not in focus
    prompt, _ = pack_prompt("월세 소득공제 요건", bundle)
    packed = json.loads(prompt)
    assert len(packed["evidence"]) == len(bundle.parts)
    assert [e["content"] for e in packed["evidence"]] == [
        p.content for p in bundle.parts
    ]


@pytest.mark.skipif(
    os.environ.get("RUN_RAG_GENERATION_INTEGRATION") != "1",
    reason="실제 ES/Ollama 평가 명시 실행 전용",
)
def test_live_search_context_and_actual_model():
    from scripts.run_rag_evaluation import DEFAULT_EVIDENCE, DEFAULT_SELECTION

    runner = load_evaluation_rag(DEFAULT_SELECTION, DEFAULT_EVIDENCE)
    try:
        prepared = asyncio.run(runner.respond("월세 공제 조건", generate=False))
        assert prepared["status"] == "PREPARED_NOT_GENERATED"
        result = asyncio.run(
            runner.respond("월세 공제에서 무주택 여부를 확인하는 이유는?")
        )
        assert result["modelCalled"]
        assert result["status"] in {"ANSWERED", "INSUFFICIENT_EVIDENCE"}
        # 모델 접속 오류를 생성 성공으로 간주하지 않는다. 응답 자체를 받아야 한다.
        assert result.get("rawModelOutput")
        assert not result["answerUseAllowed"]
    finally:
        runner.store.close()
