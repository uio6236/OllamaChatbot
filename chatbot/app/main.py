from fastapi import FastAPI

from app.api.health import router as health_router

"""
희망환급 AI 챗봇 서버 시작 파일

TODO: 챗봇 질문 처리 API 추가
TODO: Ollama Gemma3 연동
TODO: RAG 검색 기능 연동
TODO: Spring Boot 내부 인증 연동
"""

app = FastAPI(
    title="희망환급 Chatbot API",
    version="0.1.0",
)

app.include_router(health_router)
