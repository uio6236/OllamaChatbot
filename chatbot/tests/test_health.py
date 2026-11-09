from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    """
    챗봇 서버 상태 확인 API 테스트.
    """

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
