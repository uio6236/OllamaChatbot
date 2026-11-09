from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    """
    계산 서버 상태 확인 API 테스트.
    정상 요청에서 200과 status=OK가 반환되는지 확인한다.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
