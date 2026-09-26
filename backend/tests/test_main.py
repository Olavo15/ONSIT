from fastapi.testclient import TestClient
from app.main import app
from app.workers.tasks import run_async_investigation

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Plataforma de OSINT" in response.json()["message"]

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_sources():
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    assert len(response.json()) >= 5

def test_create_investigation_endpoint():
    response = client.post("/api/v1/investigations", json={
        "title": "Teste CNPJ",
        "indicators": [{"type": "CNPJ", "value": "00000000000191"}]
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] in ["PENDING", "PROCESSING", "COMPLETED"]
