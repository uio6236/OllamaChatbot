"""명시적으로 활성화한 루프백 개발 화면. 실행: python -m devtools.server."""

import asyncio
import ipaddress
import json
import os
import secrets
import time
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.errors import handle_unexpected_error, handle_validation_error
from app.main import app as internal_app
from app.schemas.chat import ChatRequest
from app.schemas.common import HistoryMessage
from app.schemas.recommendation import RecommendationRequest

ROOT = Path(__file__).resolve().parents[1]
MEMBERS = {
    "additional": ("추가 납부", "member_additional_payment.json"),
    "refund": ("환급", "member_refund.json"),
    "rent": ("월세 미적용", "member_unapplied_deduction.json"),
    "sme": ("중소기업 감면", "member_sme_reduction.json"),
}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def enabled() -> bool:
    return (
        os.getenv("CHATBOT_ENV") == "development" and os.getenv("CHATBOT_DEV_UI") == "1"
    )


class MemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    member: Annotated[str, StringConstraints(min_length=1, max_length=30)]


class MessageRequest(MemberRequest):
    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]
    history: Annotated[list[HistoryMessage], Field(max_length=10)]


def load_member(member: str) -> ChatRequest:
    # 브라우저 입력으로 파일명을 구성하지 않는다.
    return ChatRequest.model_validate(
        json.loads(
            (ROOT / "tests" / "fixtures" / MEMBERS[member][1]).read_text(
                encoding="utf-8"
            )
        )
    )


def failure(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


async def forward(path: str, body: dict) -> dict:
    """기존 내부 API를 서버 측에서 호출하고 인증 헤더는 반환하지 않는다."""
    started = time.monotonic()
    try:
        async with asyncio.timeout(55):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=internal_app, raise_app_exceptions=False
                ),
                base_url="http://internal.local",
                timeout=55,
            ) as client:
                response = await client.post(
                    path,
                    json=body,
                    headers={"X-Chatbot-Token": os.getenv("CHATBOT_API_TOKEN", "")},
                )
                result = response.json()
    except (TimeoutError, httpx.TimeoutException):
        return {
            "ok": False,
            "httpStatus": 503,
            "response": {
                "code": "DEV_TIMEOUT",
                "message": "응답 대기 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
            },
        }
    except (httpx.HTTPError, ValueError):
        return {
            "ok": False,
            "httpStatus": 503,
            "response": {
                "code": "DEV_API_UNAVAILABLE",
                "message": "내부 API 응답을 확인할 수 없습니다.",
            },
        }
    return {
        "ok": response.is_success,
        "httpStatus": response.status_code,
        "request": {"path": path, "body": body},
        "response": result,
        "elapsedMs": round((time.monotonic() - started) * 1000),
        "modelCall": {
            "verified": False,
            "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다.",
        },
    }


def create_dev_app() -> FastAPI:
    app = FastAPI(
        title="희망환급 로컬 테스트", docs_url=None, redoc_url=None, openapi_url=None
    )

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if not enabled():
            return failure(
                "DEV_DISABLED", "개발용 테스트 화면이 비활성화되어 있습니다.", 404
            )
        try:
            local = (
                request.client is not None
                and ipaddress.ip_address(request.client.host).is_loopback
            )
        except ValueError:
            local = False
        if not local or request.url.hostname not in LOCAL_HOSTS:
            return failure("LOCAL_ONLY", "루프백 주소에서만 사용할 수 있습니다.", 403)
        if request.method == "POST":
            if (
                request.headers.get("origin") != str(request.base_url).rstrip("/")
                or request.headers.get("sec-fetch-site") == "cross-site"
            ):
                return failure(
                    "DEV_ORIGIN", "같은 로컬 테스트 화면에서 요청해 주세요.", 403
                )
            if (
                request.headers.get("content-type", "").split(";", 1)[0]
                != "application/json"
            ):
                return failure("DEV_CONTENT_TYPE", "JSON 요청만 허용합니다.", 415)
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                "Referrer-Policy": "no-referrer",
            }
        )
        return response

    # 비활성 환경에서는 HTML 경로도, 더미를 읽는 핸들러도 등록하지 않는다.
    if not enabled():
        return app
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(
            (Path(__file__).parent / "chat.html").read_text(encoding="utf-8")
        )

    @app.get("/dev/members")
    async def members():
        return [{"id": key, "label": value[0]} for key, value in MEMBERS.items()]

    @app.post("/dev/briefing")
    async def briefing(request: MemberRequest):
        if request.member not in MEMBERS:
            return failure("DEV_MEMBER", "선택한 더미 회원을 확인해 주세요.", 422)
        member = load_member(request.member)
        body = RecommendationRequest(
            taxYear=member.tax_year, taxResult=member.tax_result
        )
        return await forward(
            "/internal/recommendations", body.model_dump(by_alias=True)
        )

    @app.post("/dev/chat")
    async def chat(request: MessageRequest):
        if request.member not in MEMBERS:
            return failure("DEV_MEMBER", "선택한 더미 회원을 확인해 주세요.", 422)
        member = load_member(request.member)
        # ChatRequest 기존의 문맥 길이·입력 계약을 그대로 재사용한다.
        payload = {
            **member.model_dump(by_alias=True),
            "message": request.message,
            "history": [m.model_dump(by_alias=True) for m in request.history],
        }
        try:
            body = ChatRequest.model_validate(payload)
        except ValueError:
            return failure(
                "VALIDATION", "질문 길이와 최근 대화 이력을 확인해 주세요.", 422
            )
        return await forward("/internal/chat-responses", body.model_dump(by_alias=True))

    return app


if __name__ == "__main__":
    if not enabled():
        raise SystemExit(
            "CHATBOT_ENV=development, CHATBOT_DEV_UI=1 설정이 모두 필요합니다."
        )
    # 지정된 토큰은 유지하고, 미설정 시 이 개발 프로세스에서만 임시 토큰을 쓴다.
    if not os.getenv("CHATBOT_API_TOKEN", "").strip():
        os.environ["CHATBOT_API_TOKEN"] = secrets.token_urlsafe(32)
    os.environ["OLLAMA_MODEL"] = "gemma3:4b"
    import uvicorn

    uvicorn.run(create_dev_app(), host="127.0.0.1", port=8002, proxy_headers=False)
