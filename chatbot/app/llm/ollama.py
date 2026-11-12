"""ChatOllama 호출과 내부 오류 분류. 질문과 답변은 로그에 남기지 않는다."""

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langsmith import tracing_context
from ollama import ResponseError

from app.core.config import OllamaSettings


class OllamaError(RuntimeError):
    """LLM 처리 실패의 공통 오류."""


class OllamaUnavailableError(OllamaError):
    """Ollama 서버에 연결할 수 없음."""


class OllamaTimeoutError(OllamaError):
    """Ollama 응답 대기 시간 초과."""


class OllamaModelNotFoundError(OllamaError):
    """설정한 모델을 찾을 수 없음."""


class OllamaResponseError(OllamaError):
    """모델 서버 오류 또는 잘못된 응답."""


class OllamaService:
    def __init__(
        self,
        settings: OllamaSettings | None = None,
        *,
        num_ctx=None,
        num_predict=None,
        response_format=None,
    ):
        settings = settings or OllamaSettings.from_env()
        options = {}
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        if num_predict is not None:
            options["num_predict"] = num_predict
        if response_format is not None:
            options["format"] = response_format
        self._model = ChatOllama(
            base_url=str(settings.base_url),
            model=settings.model,
            temperature=0,
            client_kwargs={"timeout": httpx.Timeout(60.0, connect=3.0)},
            **options,
        )

    def generate(self, prompt: str) -> str:
        """단일 프롬프트를 호출한다. 세액 계산과 RAG는 수행하지 않는다."""
        if not prompt.strip():
            raise ValueError("질문은 비어 있을 수 없습니다.")
        return self._generate(prompt)

    def generate_grounded(self, system: str, payload: str) -> str:
        """지시와 미신뢰 데이터의 메시지 역할을 분리한다. 추적은 계속 끈다."""
        if not system.strip() or not payload.strip():
            raise ValueError("지시와 근거 데이터가 필요합니다.")
        return self._generate(
            [SystemMessage(content=system), HumanMessage(content=payload)]
        )

    def _generate(self, messages) -> str:
        try:
            # 실행 환경에 추적 변수가 있어도 입력을 외부 추적 서비스로 보내지 않는다.
            with tracing_context(enabled=False):
                response = self._model.invoke(messages)
        except httpx.TimeoutException:
            raise OllamaTimeoutError("Ollama 응답 시간이 초과되었습니다.") from None
        except (httpx.TransportError, ConnectionError):
            raise OllamaUnavailableError("Ollama 서버에 연결할 수 없습니다.") from None
        except ResponseError as exc:
            if exc.status_code == 404:
                raise OllamaModelNotFoundError(
                    "설정한 Ollama 모델을 찾을 수 없습니다."
                ) from None
            raise OllamaResponseError("Ollama 모델 처리에 실패했습니다.") from None
        except (ValueError, TypeError, KeyError):
            raise OllamaResponseError("Ollama 응답 형식이 올바르지 않습니다.") from None

        content = getattr(response, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError("Ollama가 유효한 텍스트를 반환하지 않았습니다.")
        return content.strip()
