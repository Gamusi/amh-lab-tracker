import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_generate_pdf_endpoint():
    # Because endpoints depend on get_current_user, we need to bypass or mock auth.
    from backend.app.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "testuser"}
    
    payload = {
        "order_data": {"full_name": "JOHN DOE"},
        "results_data": []
    }
    
    try:
        response = client.post("/api/reports/generate-pdf", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b'%PDF-')
    finally:
        # Cleanup override
        app.dependency_overrides.clear()
