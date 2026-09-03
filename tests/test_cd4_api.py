import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user
from backend.app.seed import seed_database

client = TestClient(app)

@pytest.fixture
def test_app():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    seed_database(conn=conn)
    
    def override_get_db():
        yield conn
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin", "full_name": "Lab Admin", "role": "admin"}
    
    yield {"conn": conn, "client": client}
    
    app.dependency_overrides.clear()
    conn.close()

def test_block_invalid_cd4_rdt_release(test_app):
    conn = test_app["conn"]
    c = test_app["client"]
    cur = conn.cursor()
    # Create test client, visit, and order for CD4 Count (Rapid Test Strip)
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('CD4-TEST-001', 'JOHN DOE', 'Male')")
    c_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, lab_number) VALUES (?, 'MLIS-26-09-CD4')", (c_id,))
    v_id = cur.lastrowid
    cur.execute("SELECT id FROM tests WHERE name = 'CD4 Count (Rapid Test Strip)'")
    t_id = cur.fetchone()[0]
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v_id, t_id))
    o_id = cur.lastrowid
    conn.commit()

    # Try to save result as 'Invalid'
    res = c.post("/api/clients/results", json={
        "order_id": o_id,
        "result_value": "Invalid"
    })
    assert res.status_code == 400
    assert "Invalid RDT cassette run cannot be released" in res.json()["detail"]

def test_save_valid_cd4_rdt_below_200(test_app):
    conn = test_app["conn"]
    c = test_app["client"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('CD4-TEST-002', 'MARY K', 'Female')")
    c_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, lab_number) VALUES (?, 'MLIS-26-09-CD4-RDT')", (c_id,))
    v_id = cur.lastrowid
    cur.execute("SELECT id FROM tests WHERE name = 'CD4 Count (Rapid Test Strip)'")
    t_id = cur.fetchone()[0]
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v_id, t_id))
    o_id = cur.lastrowid
    conn.commit()

    res = c.post("/api/clients/results", json={
        "order_id": o_id,
        "result_value": "CD4 Count: Below 200 cells/µL"
    })
    assert res.status_code == 200

    # Verify result has L* flag and is_positive = 1
    cur.execute("SELECT clinical_flag, is_positive FROM test_results WHERE order_id = ?", (o_id,))
    row = cur.fetchone()
    assert row[0] == "L*"
    assert row[1] == 1

def test_save_valid_cd4_cytometry_below_200(test_app):
    conn = test_app["conn"]
    c = test_app["client"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('CD4-TEST-003', 'JANE DOE', 'Female')")
    c_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, lab_number) VALUES (?, 'MLIS-26-09-CD4-CYTO')", (c_id,))
    v_id = cur.lastrowid
    cur.execute("SELECT id FROM tests WHERE name = 'Absolute CD4 Count (Cytometry)'")
    t_id = cur.fetchone()[0]
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v_id, t_id))
    o_id = cur.lastrowid
    conn.commit()

    res = c.post("/api/clients/results", json={
        "order_id": o_id,
        "result_value": "186"
    })
    assert res.status_code == 200

    cur.execute("SELECT clinical_flag, is_positive FROM test_results WHERE order_id = ?", (o_id,))
    row = cur.fetchone()
    assert row[0] == "L*"
    assert row[1] == 1
