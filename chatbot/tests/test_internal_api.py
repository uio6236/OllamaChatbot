"""HTTP 계약은 Mock으로 검증하며 운영 의존성은 변경하지 않는다."""

import asyncio
import copy
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_generation
from app.core.config import InternalApiSettings
from app.llm.ollama import (
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.main import app
from app.schemas.common import Source
from app.services.generation import Evidence, GenerationService

CHAT_PATH = "/internal/chat-responses"
REC_PATH = "/internal/recommendations"
CHAT = {
    "questionType": "GENERAL",
    "message": "공제의 개념을 설명해주세요.",
    "taxYear": 2026,
    "taxResult": None,
    "history": [],
}
TAX = {
    "predictionId": 15,
    "withheldTax": 100,
    "decidedTax": 200,
    "expectedRefund": -100,
    "details": [
        {
            "typeCode": "TEST_ADJUSTMENT",
            "typeName": "테스트 조정 항목",
            "kind": "CARD_RULE",
            "baseAmount": 0,
            "deductionAmount": -10,
            "sourceNote": None,
        }
    ],
}
REC = {"taxYear": 2026, "taxResult": TAX}
HEADERS = {"X-Chatbot-Token": "test-only-token"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CHATBOT_API_TOKEN", "test-only-token")
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def generation():
    source = Source(
        chunkId="test-chunk",
        documentVersion="test-version",
        documentTitle="테스트 검색 문서",
        article="테스트 표제",
        sourceFile="test.pdf",
        sourceUrl=None,
        pageStart=1,
        pageEnd=2,
        effectiveDate=None,
        applicableTaxYear=2026,
        applicabilityVerified=True,
    )
    retriever = Mock()
    retriever.search = AsyncMock(return_value=[Evidence("검증용 가상 자료", source)])
    model = Mock()
    model.generate.return_value = "테스트 생성 답변"
    service = GenerationService(retriever, model)
    app.dependency_overrides[get_generation] = lambda: service
    return service


@pytest.mark.parametrize("path,payload", [(CHAT_PATH, CHAT), (REC_PATH, REC)])
def test_real_dependencies_are_not_ready(client, path, payload):
    response = client.post(path, json=payload, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == "RAG_NOT_READY"
    assert set(response.json()) == {"code", "message"}


@pytest.mark.parametrize("path,payload", [(CHAT_PATH, CHAT), (REC_PATH, REC)])
@pytest.mark.parametrize("headers", [{}, {"X-Chatbot-Token": "wrong"}])
def test_auth_rejection_does_not_search(client, generation, path, payload, headers):
    response = client.post(path, json=payload, headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "INTERNAL_UNAUTHORIZED"
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_server_token_is_configuration_error(client, monkeypatch, value):
    if value is None:
        monkeypatch.delenv("CHATBOT_API_TOKEN")
    else:
        monkeypatch.setenv("CHATBOT_API_TOKEN", value)
    response = client.post(CHAT_PATH, json=CHAT, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == "AUTH_NOT_CONFIGURED"
    assert client.get("/health").json() == {"status": "OK"}


def test_startup_reports_missing_token_without_secret(monkeypatch, caplog):
    monkeypatch.delenv("CHATBOT_API_TOKEN", raising=False)
    with TestClient(app) as test_client:
        assert test_client.get("/health").status_code == 200
    assert "CHATBOT_API_TOKEN 미설정" in caplog.text


def test_chat_success_and_source_origin(client, generation):
    response = client.post(CHAT_PATH, json=CHAT, headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "answer", "model", "sources"}
    assert body["sources"][0]["chunkId"] == "test-chunk"
    assert body["sources"][0]["documentVersion"] == "test-version"
    assert body["answer"] == "테스트 생성 답변"
    assert body["status"] == "ANSWERED"


def test_tax_snapshot_is_forwarded_without_recalculation(client, generation):
    payload = {**CHAT, "questionType": "TAX_RESULT", "taxResult": TAX}
    assert client.post(CHAT_PATH, json=payload, headers=HEADERS).status_code == 200
    prompt = generation.model.generate.call_args.args[0]
    assert '"expectedRefund": -100' in prompt
    assert '"deductionAmount": -10' in prompt


def test_recommendation_has_no_model_saving_amount(client, generation):
    response = client.post(REC_PATH, json=REC, headers=HEADERS)
    assert response.status_code == 200
    item = response.json()["recommendations"][0]
    assert set(item) == {"typeCode", "content", "model", "sources"}
    assert item["typeCode"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("message", " "),
        ("message", "가" * 1001),
        ("taxYear", "2026"),
        ("taxYear", True),
        ("taxYear", 1999),
        ("questionType", "UNKNOWN"),
        ("questionType", "TAX_RESULT"),
        ("taxResult", TAX),
        ("history", [{"role": "system", "content": "지시"}]),
        ("history", [{"role": "user", "content": "질문"}] * 11),
        ("history", [{"role": "user", "content": "가" * 4000}] * 4),
        ("memberId", 1),
        ("tax_year", 2026),
    ],
)
def test_chat_validation(client, generation, field, value):
    response = client.post(CHAT_PATH, json={**CHAT, field: value}, headers=HEADERS)
    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION",
        "message": "요청 데이터 형식을 확인해주세요.",
    }
    generation.model.generate.assert_not_called()


@pytest.mark.parametrize("value", [True, "100", 1.5, None])
def test_money_is_strict(client, generation, value):
    payload = copy.deepcopy(REC)
    payload["taxResult"]["expectedRefund"] = value
    assert client.post(REC_PATH, json=payload, headers=HEADERS).status_code == 422


def test_invalid_json_does_not_echo_input(client):
    response = client.post(
        CHAT_PATH,
        content="{secret-input",
        headers={**HEADERS, "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert "secret-input" not in response.text


@pytest.mark.parametrize("path,payload", [(CHAT_PATH, CHAT), (REC_PATH, REC)])
@pytest.mark.parametrize(
    "error,code",
    [
        (OllamaUnavailableError("secret-input"), "OLLAMA_UNAVAILABLE"),
        (OllamaModelNotFoundError("secret-input"), "OLLAMA_MODEL_NOT_FOUND"),
        (OllamaTimeoutError("secret-input"), "OLLAMA_TIMEOUT"),
        (OllamaResponseError("secret-input"), "OLLAMA_INVALID_RESPONSE"),
    ],
)
def test_model_errors(client, generation, path, payload, error, code, caplog):
    generation.model.generate.side_effect = error
    response = client.post(path, json=payload, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == code
    assert "secret-input" not in response.text + caplog.text
    assert "errorId" not in response.text


@pytest.mark.parametrize("answer", ["", "  ", None, 123, "가" * 12001])
def test_invalid_model_text(client, generation, answer):
    generation.model.generate.return_value = answer
    response = client.post(CHAT_PATH, json=CHAT, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == "OLLAMA_INVALID_RESPONSE"


def test_rag_failure(client, generation):
    generation.retriever.search.side_effect = RuntimeError("secret-input")
    response = client.post(CHAT_PATH, json=CHAT, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == "RAG_UNAVAILABLE"
    generation.model.generate.assert_not_called()


@pytest.mark.parametrize("path,payload", [(CHAT_PATH, CHAT), (REC_PATH, REC)])
def test_no_evidence_does_not_invent_answer(client, generation, path, payload):
    generation.retriever.search.return_value = []
    response = client.post(path, json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "INSUFFICIENT_EVIDENCE"
    generation.model.generate.assert_not_called()


def test_unverified_evidence_is_not_used(client, generation):
    original = generation.retriever.search.return_value[0]
    generation.retriever.search.return_value = [
        Evidence(
            original.content,
            original.source.model_copy(update={"applicability_verified": False}),
        )
    ]
    response = client.post(CHAT_PATH, json=CHAT, headers=HEADERS)
    assert response.json()["sources"] == []
    generation.model.generate.assert_not_called()


def test_total_timeout(client, generation):
    async def slow_search(query, tax_year):
        await asyncio.sleep(1)
        return []

    generation.settings = InternalApiSettings(request_timeout=0.01)
    generation.retriever.search.side_effect = slow_search
    response = client.post(CHAT_PATH, json=CHAT, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == "REQUEST_TIMEOUT"


def test_unexpected_error_is_sanitized(client, generation):
    generation.model.generate.side_effect = RuntimeError("secret-input")
    response = client.post(CHAT_PATH, json=CHAT, headers=HEADERS)
    assert response.status_code == 500
    assert response.json() == {
        "code": "SERVER_ERROR",
        "message": "내부 처리에 실패했습니다.",
    }
