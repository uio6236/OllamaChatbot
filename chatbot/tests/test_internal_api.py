"""HTTP 계약은 Mock으로 검증하며 운영 의존성은 변경하지 않는다."""

import asyncio
import copy
import json
from pathlib import Path
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
    if path == REC_PATH:
        # 최초 안내는 Calc 규칙으로 처리하므로 검색 준비 상태와 무관하다.
        from unittest.mock import patch

        with patch(
            "app.llm.ollama.OllamaService.generate",
            side_effect=OllamaUnavailableError("테스트 연결 실패"),
        ):
            response = client.post(path, json=payload, headers=HEADERS)
        assert response.status_code == 503
        assert response.json()["code"] == "OLLAMA_UNAVAILABLE"
        return
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


def test_calc_method_question_without_member_result_skips_rag(client, generation):
    payload = {
        **CHAT,
        "message": "월세 세액공제는 어떤 계산 방식인가요?",
    }
    generation.model.generate.return_value = (
        "Calc는 전달된 월세 입력과 귀속연도별 Oracle 기준을 사용하는 흐름입니다."
    )

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ANSWERED"
    assert "월세 세액공제" in body["answer"]
    assert body["model"] == generation.model_name
    assert body["sources"] == []
    generation.model.generate.assert_called_once()
    generation.retriever.search.assert_not_called()


def test_tax_snapshot_is_forwarded_without_recalculation(client, generation):
    payload = {
        **CHAT,
        "questionType": "TAX_RESULT",
        "message": "환급액과 공제 내역을 알려주세요.",
        "taxResult": TAX,
    }
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert "추가 납부액은 100원" in response.json()["answer"]
    assert "-10원" in response.json()["answer"]
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


def test_refund_fixture_is_explained_without_rag_or_model(client, generation):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "member_refund.json").read_text(
            encoding="utf-8"
        )
    )
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ANSWERED"
    assert "예상 환급액은 450,000원" in body["answer"]
    assert "근로소득공제" in body["answer"]
    assert body["model"] is None
    assert body["sources"] == []
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


def test_deduction_amount_comes_directly_from_calc_result(client, generation):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "member_sme_reduction.json").read_text(
            encoding="utf-8"
        )
    )
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert "1,000,000원" in response.json()["answer"]
    assert response.json()["model"] is None
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


def test_natural_deduction_list_question_uses_member_details(client, generation):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "member_refund.json").read_text(
            encoding="utf-8"
        )
    )
    payload["message"] = "어떤 공제와 감면을 받았나요?"

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["status"] == "ANSWERED"
    assert "연금계좌 세액공제: 300,000원" in response.json()["answer"]
    assert "근로소득공제: 11,500,000원" in response.json()["answer"]
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


@pytest.mark.parametrize(
    "fixture_name,question,raw,expected",
    [
        (
            "member_refund.json",
            "신용카드 소득공제는 어떻게 계산하나요?",
            "신용카드 소득공제는 카드 지출을 분류하여 공제율에 따라 계산하고, "
            "최저 사용금액을 차감한 후 최종 공제액을 결정합니다.",
            "공제율이 낮은 항목부터 최저 사용금액을 차감합니다.",
        ),
        (
            "member_sme_reduction.json",
            "중소기업 취업자 감면은 어떻게 적용되나요?",
            "중소기업 취업자 감면은 산출세액 × DB 감면율 중 작은 금액을 계산하여, "
            "그 금액 이하로 실제 감면액을 적용합니다.",
            "DB 한도 중 작은 금액",
        ),
        (
            "member_unapplied_deduction.json",
            "월세 공제액이 0원인 이유는 무엇인가요?",
            "월세 공제액이 0원인 이유는 연간 월세액이 DB 공제 대상 한도보다 작은 경우입니다.",
            "구체적인 원인을 특정할 수 없습니다",
        ),
    ],
)
def test_real_model_mistakes_are_replaced_with_grounded_rules(
    client, generation, fixture_name, question, raw, expected
):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / fixture_name).read_text(encoding="utf-8")
    )
    payload["message"] = question
    generation.model.generate.return_value = raw

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert expected in response.json()["answer"]
    assert raw not in response.json()["answer"]
    generation.retriever.search.assert_not_called()


def test_calc_method_question_uses_rule_and_gemma_without_rag(client, generation):
    payload = json.loads(
        (
            Path(__file__).parent / "fixtures" / "member_unapplied_deduction.json"
        ).read_text(encoding="utf-8")
    )
    generation.model.generate.return_value = (
        "Calc는 해당 항목의 조건과 다른 계산 경로를 비교합니다. "
        "전달된 결과만으로는 어느 조건이 원인인지 특정할 수 없습니다."
    )
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ANSWERED"
    assert "월세액 세액공제 0원" in body["answer"]
    assert "비교" in body["answer"]
    assert body["model"] == generation.model_name
    prompt = generation.model.generate.call_args.args[0]
    assert "월세 세액공제" in prompt
    assert '"deductionAmount": 0' in prompt
    generation.retriever.search.assert_not_called()


def test_unverified_numbers_from_model_are_replaced_with_calc_rule_text(
    client, generation
):
    payload = json.loads(
        (
            Path(__file__).parent / "fixtures" / "member_unapplied_deduction.json"
        ).read_text(encoding="utf-8")
    )
    generation.model.generate.return_value = "법령에 따라 2026년에 50%를 적용합니다."

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)
    answer = response.json()["answer"]

    assert response.status_code == 200
    assert "2026" not in answer
    assert "50%" not in answer
    assert "Calc 구현 규칙" in answer
    assert "결과만으로는" in answer
    generation.retriever.search.assert_not_called()


def test_unverified_zero_reason_from_model_is_replaced_with_rule_text(
    client, generation
):
    payload = json.loads(
        (
            Path(__file__).parent / "fixtures" / "member_unapplied_deduction.json"
        ).read_text(encoding="utf-8")
    )
    generation.model.generate.return_value = (
        "무주택 세대주가 아니라 월세 공제가 적용되지 않았습니다."
    )

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)
    answer = response.json()["answer"]

    assert response.status_code == 200
    assert "Calc 구현 규칙" in answer
    assert "구체적인 원인을 특정할 수 없습니다" in answer
    assert "무주택 세대주가 아니라" not in answer
    generation.retriever.search.assert_not_called()


def test_law_question_is_not_guessed_or_sent_to_rag(client, generation):
    payload = json.loads(
        (
            Path(__file__).parent / "fixtures" / "member_unapplied_deduction.json"
        ).read_text(encoding="utf-8")
    )
    payload["message"] = "월세 세액공제에 적용되는 법령 조항이 무엇인가요?"

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["status"] == "INSUFFICIENT_EVIDENCE"
    assert "법령이나 법적 자격을 검증하지 않습니다" in response.json()["answer"]
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


def test_recommendation_has_no_model_saving_amount(client, generation):
    response = client.post(REC_PATH, json=REC, headers=HEADERS)
    assert response.status_code == 200
    item = response.json()["recommendations"][0]
    assert set(item) == {"typeCode", "content", "model", "sources"}
    assert item["typeCode"] is None


@pytest.mark.parametrize(
    "fixture_name",
    [
        "member_additional_payment.json",
        "member_refund.json",
        "member_sme_reduction.json",
        "member_unapplied_deduction.json",
    ],
)
def test_initial_message_http_contract_for_member_fixtures(
    client, generation, fixture_name
):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / fixture_name).read_text(encoding="utf-8")
    )
    response = client.post(
        REC_PATH,
        json={"taxYear": payload["taxYear"], "taxResult": payload["taxResult"]},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert set(response.json()) == {"status", "recommendations"}
    assert len(response.json()["recommendations"]) == 1
    message = response.json()["recommendations"][0]
    assert set(message) == {"typeCode", "content", "model", "sources"}
    assert "기납부세액" in message["content"]
    assert (
        "확인해 볼 사항" in message["content"]
        or "추가 검토할 사유를 확인하지 못해" in message["content"]
    )
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_called_once()


def test_unknown_rule_detail_amount_uses_supplied_result(client, generation):
    payload = {**CHAT, "questionType": "TAX_RESULT", "taxResult": copy.deepcopy(TAX)}
    payload["taxResult"]["details"][0]["kind"] = "INCOME_DEDUCTION"
    payload["message"] = "테스트 조정 항목 금액은 얼마인가요?"

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert "-10원" in response.json()["answer"]
    assert response.json()["model"] is None
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


def test_empty_details_are_not_described_as_zero_deductions(client, generation):
    payload = {**CHAT, "questionType": "TAX_RESULT", "taxResult": copy.deepcopy(TAX)}
    payload["taxResult"]["details"] = []
    payload["message"] = "환급 결과를 설명해주세요."

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert "상세 내역이 없습니다" in response.json()["answer"]
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


def test_long_method_answer_falls_back_before_response_limit(client, generation):
    payload = json.loads(
        (
            Path(__file__).parent / "fixtures" / "member_unapplied_deduction.json"
        ).read_text(encoding="utf-8")
    )
    generation.model.generate.return_value = "계산 흐름을 설명합니다. " * 700

    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert "Calc 구현 규칙" in response.json()["answer"]
    generation.retriever.search.assert_not_called()


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


def test_input_snapshot_conflict_returns_safe_validation_error(client, generation):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "member_refund.json").read_text(
            encoding="utf-8"
        )
    )
    payload["taxResult"]["inputs"]["pensionSaving"] = 123456
    response = client.post(
        REC_PATH,
        json={"taxYear": payload["taxYear"], "taxResult": payload["taxResult"]},
        headers=HEADERS,
    )
    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION",
        "message": "요청 데이터 형식을 확인해주세요.",
    }
    assert "123456" not in response.text
    generation.model.generate.assert_not_called()


@pytest.mark.parametrize(
    "fixture_name,question,expected,unexpected",
    [
        (
            "member_refund.json",
            "연금저축 납입 입력액은 얼마인가요?",
            "2,000,000원",
            "300,000원",
        ),
        ("member_refund.json", "irp 납입 입력액은 얼마인가요?", "0원", "2,000,000원"),
        (
            "member_unapplied_deduction.json",
            "월 월세 입력액은 얼마인가요?",
            "500,000원",
            "6,000,000원",
        ),
        (
            "member_sme_reduction.json",
            "중소기업 감면 신청 입력값은 무엇인가요?",
            "신청값: Y",
            "1,000,000원",
        ),
    ],
)
def test_original_input_question_is_not_answered_with_applied_amount(
    client, generation, fixture_name, question, expected, unexpected
):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / fixture_name).read_text(encoding="utf-8")
    )
    payload["message"] = question
    payload["history"] = [
        {"role": "assistant", "content": "다른 회원의 입력은 987654321원입니다."}
    ]
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "전달된 원본 입력값" in answer
    assert expected in answer
    assert unexpected not in answer
    assert "987654321" not in answer
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


@pytest.mark.parametrize("inputs", [None, {}, {"pensionSaving": None}])
def test_missing_original_input_is_not_filled_from_history_or_base_amount(
    client, generation, inputs
):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "member_refund.json").read_text(
            encoding="utf-8"
        )
    )
    payload["taxResult"]["inputs"] = inputs
    payload["message"] = "연금저축 납입 입력액은 얼마인가요?"
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "INSUFFICIENT_EVIDENCE"
    assert "2,000,000" not in response.json()["answer"]
    generation.model.generate.assert_not_called()


def test_interleaved_member_followups_use_each_current_snapshot(client, generation):
    names = [
        "member_additional_payment.json",
        "member_refund.json",
        "member_unapplied_deduction.json",
        "member_sme_reduction.json",
    ]
    payloads = [
        json.loads(
            (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")
        )
        for name in names
    ]
    for _ in range(2):
        for index, payload in enumerate(payloads):
            current = copy.deepcopy(payload)
            current["message"] = "현재 회원의 환급액과 공제 내역을 다시 알려주세요."
            foreign = payloads[(index + 1) % len(payloads)]["taxResult"]
            current["history"] = [
                {
                    "role": "assistant",
                    "content": json.dumps(foreign) + " 환급액은 987654321원입니다.",
                }
            ]
            response = client.post(CHAT_PATH, json=current, headers=HEADERS)
            assert response.status_code == 200
            answer = response.json()["answer"]
            result = current["taxResult"]
            for value in (
                abs(result["expectedRefund"]),
                result["withheldTax"],
                result["decidedTax"],
            ):
                assert f"{value:,}원" in answer
            assert "987654321" not in answer
    generation.retriever.search.assert_not_called()
    generation.model.generate.assert_not_called()


def test_ambiguous_followup_does_not_guess_from_assistant_history(client, generation):
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "member_refund.json").read_text(
            encoding="utf-8"
        )
    )
    payload["message"] = "그건 얼마인가요?"
    payload["history"] = [
        {"role": "assistant", "content": "방금 말한 금액은 987654321원입니다."}
    ]
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "INSUFFICIENT_EVIDENCE"
    assert "987654321" not in response.text
    generation.model.generate.assert_not_called()


@pytest.mark.parametrize(
    "message",
    ["오늘 날씨 알려줘", "IRP에 100만원 더 넣으면 얼마인가요?", "상속세 신고 방법은?"],
)
def test_policy_responses_keep_http_contract_and_require_auth(
    client, generation, message
):
    payload = {**CHAT, "message": message}
    assert client.post(CHAT_PATH, json=payload).status_code == 401
    response = client.post(CHAT_PATH, json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert set(response.json()) == {"status", "answer", "model", "sources"}
    assert response.json()["model"] is None
    generation.model.generate.assert_not_called()
    generation.retriever.search.assert_not_called()


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
    if path == REC_PATH:
        # 검색 근거 대신 제공된 계산 결과와 정보 부족 안내를 하나의 메시지로 반환한다.
        body = response.json()
        assert body["status"] == "ANSWERED"
        assert len(body["recommendations"]) == 1
        assert (
            "입력값과 공제·감면 상세 결과를 확인"
            in body["recommendations"][0]["content"]
        )
        generation.retriever.search.assert_not_called()
        return
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
