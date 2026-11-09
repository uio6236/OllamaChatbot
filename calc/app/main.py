from fastapi import FastAPI

from app.api.health import router as health_router

# 희망환급 Python 계산 서버
# TODO: 계산·혜택 진단·카드 처리 API 라우터 연결
app = FastAPI(
    title="희망환급 Calc API",
    version="0.1.0",
)

# 서버 기본 상태 확인 API
app.include_router(health_router)
