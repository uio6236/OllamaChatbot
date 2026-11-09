"""OS 환경변수에서 Ollama 연결 설정을 읽는다."""

import os

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class InternalApiSettings(BaseModel):
    """토큰은 출력하지 않으며 OS 환경변수만 사용한다."""

    model_timeout: float = 45.0
    request_timeout: float = 50.0

    @staticmethod
    def token() -> str:
        return os.environ.get("CHATBOT_API_TOKEN", "")


class OllamaSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: HttpUrl = "http://127.0.0.1:11434"
    model: str = "gemma3:4b"

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Ollama 모델 이름은 비어 있을 수 없습니다.")
        return value.strip()

    @classmethod
    def from_env(cls) -> "OllamaSettings":
        return cls(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=os.environ.get("OLLAMA_MODEL", "gemma3:4b"),
        )
