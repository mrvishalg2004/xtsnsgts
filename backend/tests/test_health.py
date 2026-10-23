import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data
    assert data["environment"] == "development"


def test_root_endpoint_returns_info(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "/docs" in data["docs"]
    assert "/api/health" in data["health"]
