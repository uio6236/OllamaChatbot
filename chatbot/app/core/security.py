"""내부 서비스 토큰 검증. 회원 소유권 판단은 Spring Boot의 책임이다."""

import secrets
from typing import Annotated

from fastapi import Header

from app.core.config import InternalApiSettings
from app.core.errors import InternalApiError


def require_internal_token(
    token: Annotated[str | None, Header(alias="X-Chatbot-Token")] = None,
) -> None:
    expected = InternalApiSettings.token()
    if not expected.strip():
        raise InternalApiError(
            "AUTH_NOT_CONFIGURED", "내부 서비스 인증 설정이 준비되지 않았습니다."
        )
    if token is None or not secrets.compare_digest(
        token.encode("utf-8"), expected.encode("utf-8")
    ):
        raise InternalApiError(
            "INTERNAL_UNAUTHORIZED", "내부 서비스 인증에 실패했습니다.", 401
        )
