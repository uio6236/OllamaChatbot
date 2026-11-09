"""내부 API 오류. 외부 공통 봉투와 추적번호를 생성하지 않는다."""

from fastapi import Request
from fastapi.responses import JSONResponse


class InternalApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 503):
        self.code = code
        self.message = message
        self.status_code = status_code


async def handle_internal_error(request: Request, exc: InternalApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


async def handle_validation_error(request: Request, exc: Exception):
    # 기본 검증 오류의 input에는 질문·금액·토큰이 들어갈 수 있다.
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION", "message": "요청 데이터 형식을 확인해주세요."},
    )


async def handle_unexpected_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": "SERVER_ERROR", "message": "내부 처리에 실패했습니다."},
    )
