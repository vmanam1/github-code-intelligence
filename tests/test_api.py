import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    """Verify that root endpoint health status is online."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "GitHub Code Intelligence" in data["service"]

def test_list_repositories_api():
    """Verify that list repositories endpoint works."""
    response = client.get("/api/repositories/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_import_invalid_repo_url():
    """Verify that importing an invalid URL schema triggers validation errors."""
    response = client.post("/api/repositories/", json={"url": "invalid-url"})
    assert response.status_code == 400
    assert "Invalid repository URL" in response.json()["detail"]
