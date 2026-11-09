from fastapi import APIRouter

# 챗봇 서버 상태 확인 API 라우터
router = APIRouter()


@router.get("/health")
def health():
    """
    챗봇 서버의 HTTP 응답 상태 확인.

    TODO: 추후 Ollama 및 RAG 준비 상태 별도 점검
    """
    return {"status": "OK"}
