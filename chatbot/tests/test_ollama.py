"""실제 Ollama 서버 없이 설정과 모델 호출 경계를 검증한다."""

from unittest.mock import patch

import httpx
import pytest
from langchain_core.messages import AIMessage
from langsmith import get_tracing_context
from ollama import ResponseError
from pydantic import ValidationError

from app.core.config import OllamaSettings
from app.llm.ollama import (
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaService,
    OllamaTimeoutError,
    OllamaUnavailableError,
)


def test_default_settings(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    settings = OllamaSettings.from_env()
    assert str(settings.base_url) == "http://127.0.0.1:11434/"
    assert settings.model == "gemma3:4b"


def test_environment_settings_reach_client(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:12345")
    monkeypatch.setenv("OLLAMA_MODEL", "custom:4b")
    with patch("app.llm.ollama.ChatOllama") as factory:
        factory.return_value.invoke.return_value = AIMessage(content=" 연결 성공 ")
        assert OllamaService().generate("연결 확인") == "연결 성공"
        kwargs = factory.call_args.kwargs
        assert kwargs["base_url"] == "http://localhost:12345/"
        assert kwargs["model"] == "custom:4b"
        assert kwargs["client_kwargs"]["timeout"].connect == 3
        assert kwargs["client_kwargs"]["timeout"].read == 60
        factory.return_value.invoke.assert_called_once_with("연결 확인")


@pytest.mark.parametrize(
    "name,value",
    [("OLLAMA_BASE_URL", "invalid"), ("OLLAMA_MODEL", "  ")],
)
def test_invalid_settings(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        OllamaSettings.from_env()


@pytest.fixture
def mocked_service():
    with patch("app.llm.ollama.ChatOllama") as factory:
        yield OllamaService(OllamaSettings()), factory.return_value


def test_empty_prompt_does_not_call_model(mocked_service):
    service, model = mocked_service
    with pytest.raises(ValueError):
        service.generate("  ")
    model.invoke.assert_not_called()


def test_external_tracing_is_disabled_during_call(mocked_service, monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    service, model = mocked_service

    def respond(prompt):
        assert get_tracing_context()["enabled"] is False
        return AIMessage(content="연결 성공")

    model.invoke.side_effect = respond
    assert service.generate("연결 확인") == "연결 성공"


@pytest.mark.parametrize(
    "failure,expected",
    [
        (httpx.ConnectError("민감한 내부 주소"), OllamaUnavailableError),
        (ConnectionError("민감한 내부 주소"), OllamaUnavailableError),
        (httpx.ReadTimeout("민감한 질문"), OllamaTimeoutError),
        (httpx.ConnectTimeout("민감한 내부 주소"), OllamaTimeoutError),
        (ResponseError("민감한 모델 오류", status_code=404), OllamaModelNotFoundError),
        (ResponseError("민감한 모델 오류", status_code=500), OllamaResponseError),
        (ValueError("민감한 응답"), OllamaResponseError),
    ],
)
def test_errors_are_classified_without_sensitive_details(
    mocked_service, failure, expected
):
    service, model = mocked_service
    model.invoke.side_effect = failure
    with pytest.raises(expected) as caught:
        service.generate("연결 확인")
    assert "민감한" not in str(caught.value)


@pytest.mark.parametrize("content", ["", "  ", [], None, 123])
def test_invalid_response_is_rejected(mocked_service, content):
    service, model = mocked_service
    model.invoke.return_value.content = content
    with pytest.raises(OllamaResponseError):
        service.generate("연결 확인")
