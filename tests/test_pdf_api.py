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

def test_get_client_report_pdf():
    from backend.app.database import get_db, SCHEMA_SQL
    import sqlite3
    
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    cur = conn.cursor()
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Hematology', 1)")
    section_id = cur.lastrowid
    
    cur.execute("INSERT INTO tests (name, section_id, is_active) VALUES ('CBC', ?, 1)", (section_id,))
    test_id = cur.lastrowid
    
    cur.execute("INSERT INTO clients (client_number, full_name, date_of_birth, sex) VALUES ('C001', 'Test Client', '1990-01-01', 'M')")
    client_id = cur.lastrowid
    
    cur.execute("INSERT INTO test_orders (client_id, test_id, status) VALUES (?, ?, 'completed')", (client_id, test_id))
    order_id = cur.lastrowid
    
    cur.execute("INSERT INTO test_results (order_id, result_value) VALUES (?, '12.5')", (order_id,))
    conn.commit()
    
    def override_get_db():
        yield conn
        
    app.dependency_overrides[get_db] = override_get_db
    from backend.app.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "testuser"}
    
    try:
        response = client.get(f"/api/reports/client/{client_id}/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b'%PDF-')
        
        # Test 404 logic
        response = client.get("/api/reports/client/9999/pdf")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        conn.close()
