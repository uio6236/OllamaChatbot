"""로컬 경계·서버 측 인증·기존 API 경유를 Mock 모델로 검증한다."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_generation
from app.core.security import require_internal_token
from app.llm.ollama import OllamaUnavailableError
from app.main import app as internal_app
from app.services.generation import GenerationService, UnavailableRetriever
from devtools.server import MEMBERS, create_dev_app

ORIGIN = "http://127.0.0.1:8002"
HEADERS = {"Origin": ORIGIN}


@pytest.fixture
def dev_client(monkeypatch):
    monkeypatch.setenv("CHATBOT_ENV", "development")
    monkeypatch.setenv("CHATBOT_DEV_UI", "1")
    monkeypatch.setenv("CHATBOT_API_TOKEN", "server-only-secret-token")
    model = Mock()
    model.generate.return_value = '{"explanations": []}'
    generation = GenerationService(UnavailableRetriever(), model)
    old = internal_app.dependency_overrides.copy()
    internal_app.dependency_overrides[get_generation] = lambda: generation
    with TestClient(
        create_dev_app(),
        base_url=ORIGIN,
        client=("127.0.0.1", 1234),
        raise_server_exceptions=False,
    ) as client:
        yield client, model
    internal_app.dependency_overrides.clear()
    internal_app.dependency_overrides.update(old)


@pytest.mark.parametrize(
    "environment,flag", [("production", "1"), ("development", "0"), ("", "1"), ("", "")]
)
def test_disabled_environment_cannot_read_html_or_fixtures(
    monkeypatch, environment, flag
):
    monkeypatch.setenv("CHATBOT_ENV", environment)
    monkeypatch.setenv("CHATBOT_DEV_UI", flag)
    load = Mock(side_effect=AssertionError("더미 읽기 금지"))
    monkeypatch.setattr("devtools.server.load_member", load)
    with TestClient(
        create_dev_app(), base_url=ORIGIN, client=("127.0.0.1", 1)
    ) as client:
        for path in ("/", "/dev/members"):
            assert client.get(path).status_code == 404
        assert (
            client.post(
                "/dev/briefing", json={"member": "refund"}, headers=HEADERS
            ).status_code
            == 404
        )
    load.assert_not_called()


def test_operating_app_has_no_development_routes_even_with_flags(dev_client):
    with TestClient(internal_app) as client:
        assert client.get("/dev/members").status_code == 404
        assert (
            client.post("/dev/briefing", json={"member": "refund"}).status_code == 404
        )


def test_html_member_labels_and_no_token(dev_client):
    client, _ = dev_client
    response = client.get("/")
    assert response.status_code == 200
    assert "직접 Gemma 호출" in response.text
    assert "server-only-secret-token" not in response.text
    assert "X-Chatbot-Token" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    members = client.get("/dev/members").json()
    assert len(members) == 4
    assert all(set(member) == {"id", "label"} for member in members)


@pytest.mark.parametrize("member", list(MEMBERS))
def test_member_briefing_and_current_snapshot_followup(dev_client, member):
    client, model = dev_client
    briefing = client.post("/dev/briefing", json={"member": member}, headers=HEADERS)
    assert briefing.status_code == 200
    data = briefing.json()
    assert data["ok"]
    assert len(data["response"]["recommendations"]) == 1
    assert data["request"]["path"] == "/internal/recommendations"
    assert data["modelCall"]["verified"] is False
    assert "server-only-secret-token" not in briefing.text
    model.generate.assert_called_once()
    body = {
        "member": member,
        "message": "환급액과 공제 내역은?",
        "history": [
            {
                "role": "assistant",
                "content": data["response"]["recommendations"][0]["content"],
            }
        ],
    }
    followup = client.post("/dev/chat", json=body, headers=HEADERS).json()
    assert followup["ok"]
    assert followup["request"]["path"] == "/internal/chat-responses"
    assert (
        followup["request"]["body"]["taxResult"] == data["request"]["body"]["taxResult"]
    )
    assert followup["response"]["model"] is None


def test_internal_auth_is_actually_used_server_side(dev_client):
    client, _ = dev_client
    checks = []

    def spy_auth(token=None):
        checks.append(True)
        raise RuntimeError("브라우저에 노출하면 안 되는 내부 내용")

    internal_app.dependency_overrides[require_internal_token] = spy_auth
    response = client.post("/dev/briefing", json={"member": "refund"}, headers=HEADERS)
    assert checks
    assert not response.json()["ok"]
    assert "노출하면 안" not in response.text


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://evil.example"},
        {"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"},
    ],
)
def test_cross_origin_requests_rejected(dev_client, headers):
    client, model = dev_client
    assert (
        client.post(
            "/dev/briefing", json={"member": "refund"}, headers=headers
        ).status_code
        == 403
    )
    model.generate.assert_not_called()


def test_remote_client_and_untrusted_host_rejected(monkeypatch):
    monkeypatch.setenv("CHATBOT_ENV", "development")
    monkeypatch.setenv("CHATBOT_DEV_UI", "1")
    with TestClient(
        create_dev_app(), base_url=ORIGIN, client=("192.0.2.10", 1)
    ) as client:
        assert client.get("/").status_code == 403
    with TestClient(
        create_dev_app(), base_url="http://evil.example", client=("127.0.0.1", 1)
    ) as client:
        assert client.get("/dev/members").status_code == 403


@pytest.mark.parametrize(
    "payload", [{"member": "../../private"}, {"member": "refund", "token": "fake"}]
)
def test_fixture_allowlist_and_unknown_fields(dev_client, payload):
    client, model = dev_client
    assert (
        client.post("/dev/briefing", json=payload, headers=HEADERS).status_code == 422
    )
    model.generate.assert_not_called()


def test_disabled_after_start_and_history_limit(dev_client, monkeypatch):
    client, model = dev_client
    payload = {
        "member": "refund",
        "message": "금액은?",
        "history": [{"role": "user", "content": "가" * 4000}] * 4,
    }
    assert client.post("/dev/chat", json=payload, headers=HEADERS).status_code == 422
    monkeypatch.setenv("CHATBOT_ENV", "production")
    assert client.get("/").status_code == 404
    model.generate.assert_not_called()


def test_model_unavailable_returns_safe_error_and_no_token(dev_client):
    client, model = dev_client
    model.generate.side_effect = OllamaUnavailableError("민감한 내부 오류")
    result = client.post("/dev/briefing", json={"member": "refund"}, headers=HEADERS)
    body = result.json()
    assert body["httpStatus"] == 503
    assert body["response"]["code"] == "OLLAMA_UNAVAILABLE"
    assert "민감한 내부" not in result.text
    assert "server-only-secret-token" not in result.text


def test_proxy_timeout_is_reported_safely(dev_client, monkeypatch):
    client, _ = dev_client
    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        AsyncMock(side_effect=httpx.ReadTimeout("secret-token")),
    )
    result = client.post("/dev/briefing", json={"member": "refund"}, headers=HEADERS)
    assert result.json()["response"]["code"] == "DEV_TIMEOUT"
    assert "secret-token" not in result.text
