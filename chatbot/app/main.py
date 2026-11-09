import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.recommendations import router as recommendation_router
from app.core.config import InternalApiSettings
from app.core.errors import (
    InternalApiError,
    handle_internal_error,
    handle_unexpected_error,
    handle_validation_error,
)

"""
희망환급 AI 챗봇 서버 시작 파일

TODO: RAG 검색 기능 연동
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not InternalApiSettings.token().strip():
        logging.getLogger(__name__).error(
            "CHATBOT_API_TOKEN 미설정: 내부 POST는 차단됩니다. Health는 유지합니다."
        )
    yield


app = FastAPI(
    title="희망환급 Chatbot API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(recommendation_router)
app.add_exception_handler(InternalApiError, handle_internal_error)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(Exception, handle_unexpected_error)
