from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """
    계산 서버의 HTTP 응답 상태 확인.

    TODO: 추후 DB 연결 상태와는 별도로 관리
    """
    return {"status": "OK"}
