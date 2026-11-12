"""REST 계약 Mock 통합 검사. 실제 BM25 품질 측정과 구분한다."""

import copy
import json
import os

import httpx
import pytest
from test_scope import selection_fixture

from app.rag.elasticsearch_documents import evaluation_documents
from app.rag.elasticsearch_store import (
    EvaluationSearchError,
    EvaluationStore,
    index_name,
)
from scripts.evaluate_bm25 import make_questions, score_question


class MockElastic:
    def __init__(self, version="7.10.1"):
        self.version = version
        self.mapping = None
        self.documents = {}
        self.paths = []
        self.bulk_error = False

    def __call__(self, request):
        path = request.url.path
        self.paths.append(path)
        header = {"X-Elastic-Product": "Elasticsearch"}

        def response(data, status=200):
            return httpx.Response(status, json=data, headers=header)

        if path == "/":
            return response(
                {"version": {"number": self.version}, "tagline": "You Know, for Search"}
            )
        name = path.split("/")[1]
        if request.method == "GET" and path.count("/") == 1:
            if self.mapping and self.version.startswith("7."):
                self.mapping["dynamic"] = "false"
            return (
                response({name: {"mappings": self.mapping}})
                if self.mapping
                else response({}, 404)
            )
        if request.method == "PUT":
            self.mapping = json.loads(request.content)["mappings"]
            return response({"acknowledged": True})
        if path.endswith("/_bulk"):
            rows = [json.loads(s) for s in request.content.decode().splitlines()]
            for action, document in zip(rows[::2], rows[1::2], strict=True):
                assert "_index" not in action["create"]
                self.documents[action["create"]["_id"]] = document
            return response(
                {
                    "errors": self.bulk_error,
                    "items": [{"create": {"status": 201}}] * len(self.documents),
                }
            )
        if path.endswith("/_count"):
            return response({"count": len(self.documents)})
        if path.endswith("/_search"):
            return response(
                {
                    "hits": {
                        "hits": [
                            {"_id": k, "_score": 2.0, "_source": v}
                            for k, v in self.documents.items()
                        ]
                    }
                }
            )
        raise AssertionError(path)


def setup_store(version="7.10.1", profile="baseline"):
    data = selection_fixture()
    server = MockElastic(version)
    store = EvaluationStore(
        data["selectionHash"], transport=httpx.MockTransport(server), profile=profile
    )
    return store, server, evaluation_documents(data, profile=profile)


@pytest.mark.parametrize("version", ["7.10.1", "8.19.0", "9.0.0"])
def test_rest_index_search_integrity_and_readonly_reuse(version):
    store, server, docs = setup_store(version)
    try:
        assert store.index_documents(docs)["count"] == 1
        assert store.search("월세")[0]["chunkId"] == docs[0]["chunkId"]
        assert store.index_documents(docs, reuse=True)["integrity"] == "PASS"
        assert all(p == "/" or p.startswith("/hope-rag-eval-") for p in server.paths)
        with pytest.raises(EvaluationSearchError, match="INDEX_EXISTS"):
            store.index_documents(docs)
        server.documents[docs[0]["id"]]["content"] = "변조"
        with pytest.raises(EvaluationSearchError, match="CONTENT_MISMATCH"):
            store.verify(docs)
    finally:
        store.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://external.test:9200",
        "http://user:secret@localhost:9200",
        "http://localhost:9200/hope-rag-prod-x",
        "http://localhost:9200?index=prod",
    ],
)
def test_no_external_server_or_production_url(url):
    with pytest.raises(ValueError):
        EvaluationStore("a" * 64, url=url)


def test_no_arbitrary_index_or_wildcard():
    store, _, _ = setup_store()
    try:
        with pytest.raises(ValueError):
            store.request("POST", "/hope-rag-prod-x/_search")
        with pytest.raises(ValueError):
            index_name("*")
    finally:
        store.close()


def test_partial_bulk_is_failure_and_unselected_integrity_fails():
    store, server, docs = setup_store()
    try:
        server.bulk_error = True
        with pytest.raises(EvaluationSearchError, match="BULK_PARTIAL"):
            store.index_documents(docs)
        server.documents["unselected"] = copy.deepcopy(docs[0])
        with pytest.raises(EvaluationSearchError, match="CONTENT_MISMATCH"):
            store.verify(docs)
    finally:
        store.close()


def test_failure_does_not_fallback_or_expose_details():
    calls = []

    def fail(request):
        calls.append(str(request.url))
        raise httpx.ConnectError("sensitive internal error")

    store = EvaluationStore("a" * 64, transport=httpx.MockTransport(fail))
    try:
        with pytest.raises(EvaluationSearchError, match="REQUEST_FAILED") as exc:
            store.search("월세")
        assert "sensitive" not in str(exc.value)
        assert calls == ["http://127.0.0.1:9200/"]
    finally:
        store.close()


@pytest.mark.parametrize("version", ["6.8.0", "7.9.3", "10.0.0"])
def test_unsupported_server_version(version):
    store, _, _ = setup_store(version)
    try:
        with pytest.raises(EvaluationSearchError, match="UNSUPPORTED"):
            store.health()
    finally:
        store.close()


@pytest.mark.parametrize("failure", ["timeout", "http500", "badjson"])
def test_safe_protocol_errors(failure):
    def handle(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("internal detail")
        if failure == "http500":
            return httpx.Response(500, text="internal detail")
        return httpx.Response(200, text="internal detail")

    store = EvaluationStore("a" * 64, transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(EvaluationSearchError) as exc:
            store.health()
        assert "internal detail" not in str(exc.value)
    finally:
        store.close()


def test_foreign_or_tampered_document_is_not_exposed():
    store, server, docs = setup_store()
    try:
        store.index_documents(docs)
        server.documents[docs[0]["id"]]["usageScope"] = "CURRENT_2026"
        with pytest.raises(EvaluationSearchError, match="BOUNDARY"):
            store.search("월세")
        server.documents[docs[0]["id"]]["usageScope"] = "EVALUATION_ONLY"
        server.documents[docs[0]["id"]]["content"] = "변조"
        with pytest.raises(EvaluationSearchError, match="CONTENT_CHANGED"):
            store.search("월세")
    finally:
        store.close()


def test_duplicate_versions_are_kept_as_variants():
    store, server, docs = setup_store()
    try:
        store.index_documents(docs)
        other = {**copy.deepcopy(docs[0]), "id": "variant", "documentVersion": "b" * 64}
        server.documents["variant"] = other
        hits = store.search("월세")
        assert len(hits) == 1
        assert len(hits[0]["variants"]) == 1
        assert {
            hits[0]["documentVersion"],
            hits[0]["variants"][0]["documentVersion"],
        } == {"a" * 64, "b" * 64}
    finally:
        store.close()


def test_gold_requires_real_text_anchor_and_metrics_exclude_unknown():
    docs = evaluation_documents(selection_fixture())
    qs = make_questions(docs)
    assert len(qs) == 30
    assert sum(q["status"] == "OUT_OF_SCOPE" for q in qs) == 3
    assert all(not q["goldChunkIds"] for q in qs if q["status"] == "UNDETERMINED")
    q = next(q for q in qs if q["goldGroups"])
    hit = {**docs[0], "score": 1, "variants": []}
    assert score_question(q, [hit])["recallAt5"] == 1
    assert score_question(q, [hit])["reciprocalRank"] == 1
    unknown = next(q for q in qs if q["status"] == "UNDETERMINED")
    assert score_question(unknown, [hit])["recallAt5"] is None


def test_quality_profile_preserves_original_and_versions():
    from app.rag.elasticsearch_documents import source_metadata

    data = selection_fixture()
    old = copy.deepcopy(data)
    baseline = evaluation_documents(data)
    documents = evaluation_documents(data, profile="quality-v2")
    assert data == old
    assert documents[0]["id"] == baseline[0]["id"]
    assert documents[0]["contentHash"] == baseline[0]["contentHash"]
    assert documents[0]["sourceKind"] == "LAW_BODY"
    assert documents[0]["applicableTaxYear"] is None
    row = copy.deepcopy(data["candidates"][0])
    row["documentType"] = "AMENDMENT_SUMMARY"
    assert source_metadata(row)["comparisonOnly"]
    row["documentType"] = "LAW"
    row["contextRegions"] = [{"role": "APPLICATION"}]
    assert source_metadata(row)["sourceKind"] == "SUPPLEMENT"


def test_outside_and_ambiguous_queries_do_not_call_es():
    store, server, _ = setup_store(profile="quality-v2")
    try:
        assert (
            store.search_evaluation("법인카드 매입세액 공제는?")["status"]
            == "OUT_OF_SCOPE"
        )
        assert store.search_evaluation("카드")["status"] == "INSUFFICIENT_EVIDENCE"
        assert server.paths == []
    finally:
        store.close()


def test_quality_body_context_and_query_have_no_answer_ids():
    store, server, docs = setup_store(profile="quality-v2")
    try:
        store.index_documents(docs)
        assert (
            store.search_evaluation("월세 세액공제 요건")["status"]
            == "RETRIEVED_UNVERIFIED"
        )
        assert not store.search_evaluation("월세 소득공제 한도")["answerUseAllowed"]
        with pytest.raises(EvaluationSearchError, match="SOURCE_VIEW"):
            store.search_evaluation("월세 공제 요건", view="comparison")
        server.documents.clear()
        assert (
            store.search_evaluation("월세 공제 요건")["status"]
            == "INSUFFICIENT_EVIDENCE"
        )
    finally:
        store.close()


def test_quality_query_is_generic_and_supplement_penalty_is_conditional():
    store, server, docs = setup_store(profile="quality-v2")
    payloads = []

    def capture(request):
        if request.url.path.endswith("/_search"):
            payloads.append(json.loads(request.content))
        return server(request)

    store.close()
    store = EvaluationStore(
        docs[0]["selectionHash"],
        profile="quality-v2",
        transport=httpx.MockTransport(capture),
    )
    try:
        store.index_documents(docs)
        store.search_evaluation("월세 공제한도 규정은?")
        payload = payloads[-1]
        assert "function_score" in payload["query"]
        text = json.dumps(payload, ensure_ascii=False)
        assert "CARD-05" not in text and "제126조의2" not in text
        assert "chunkId" not in text
        store.search_evaluation("월세 부칙 적용시기는?")
        assert "function_score" not in payloads[-1]["query"]
    finally:
        store.close()


def test_quality_comparison_refuses_changed_gold():
    from scripts.evaluate_bm25 import compare_quality

    questions = make_questions(evaluation_documents(selection_fixture()))
    with pytest.raises(ValueError, match="정답"):
        compare_quality(questions, None, {"questionsHash": "0" * 64})


def test_quality_different_versions_stay_unverified_and_separate():
    store, server, docs = setup_store(profile="quality-v2")
    try:
        store.index_documents(docs)
        server.documents[docs[0]["id"]]["legalVersions"] = ["가상 법률 버전 1"]
        server.documents["other"] = {
            **copy.deepcopy(server.documents[docs[0]["id"]]),
            "id": "other",
            "legalVersions": ["가상 법률 버전 2"],
        }
        result = store.search_evaluation("월세 세액공제 요건")
        assert not result["answerUseAllowed"]
        assert result["hits"][0]["versionResolution"] == "NOT_VERIFIED"
        assert len(result["hits"][0]["variants"]) == 1
        assert result["hits"][0]["applicableTaxYear"] is None
    finally:
        store.close()


@pytest.mark.skipif(
    os.environ.get("RUN_RAG_EVAL_INTEGRATION") != "1",
    reason="로컬 ES 명시적 통합 실행 전용",
)
@pytest.mark.parametrize("profile", ["baseline", "quality-v2"])
def test_live_evaluation_index_readonly(profile):
    from pathlib import Path

    path = os.environ.get("RAG_EVAL_SELECTION")
    if not path:
        pytest.fail("RAG_EVAL_SELECTION이 필요합니다.")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    docs = evaluation_documents(data, profile=profile)
    store = EvaluationStore(data["selectionHash"], profile=profile)
    try:
        assert store.verify(docs)["count"] == len(docs)
        assert store.search("월세 세액공제")
        if profile == "quality-v2":
            assert (
                store.search_evaluation("법인카드 매입세액 공제")["status"]
                == "OUT_OF_SCOPE"
            )
            assert store.search_evaluation("월세 세액공제")["hits"]
    finally:
        store.close()
