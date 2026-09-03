import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user
from backend.app.seed import seed_database
from backend.app.surveillance_analytics import is_order_surveillance_incident

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

def test_cd4_surveillance_incident_quant():
    # Value < 200 -> Incident (AHD)
    results_ahd = [{"parameter_name": "Absolute CD4 Count (Cytometry)", "result_value": "142", "clinical_flag": "L*", "is_positive": 1}]
    assert is_order_surveillance_incident("Absolute CD4 Count (Cytometry)", results_ahd) is True

    # Value >= 200 -> Not an incident
    results_stable = [{"parameter_name": "Absolute CD4 Count (Cytometry)", "result_value": "620", "clinical_flag": None, "is_positive": 0}]
    assert is_order_surveillance_incident("Absolute CD4 Count (Cytometry)", results_stable) is False

def test_cd4_surveillance_incident_rdt():
    # Below 200 -> Incident
    results_rdt_pos = [{"parameter_name": "CD4 Count (Rapid Test Strip)", "result_value": "CD4 Count: Below 200 cells/µL", "clinical_flag": "L*", "is_positive": 1}]
    assert is_order_surveillance_incident("CD4 Count (Rapid Test Strip)", results_rdt_pos) is True

    # 200 or above -> Not an incident
    results_rdt_neg = [{"parameter_name": "CD4 Count (Rapid Test Strip)", "result_value": "CD4 Count: 200 cells/µL or above", "clinical_flag": None, "is_positive": 0}]
    assert is_order_surveillance_incident("CD4 Count (Rapid Test Strip)", results_rdt_neg) is False

def test_cd4_hmis_105_aggregation(test_app):
    c = test_app["client"]
    conn = test_app["conn"]
    cur = conn.cursor()

    # Enter 1 CD4 Cytometry < 200 (AHD positive)
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('CD4-H1', 'CLIENT ONE', 'Male')")
    c1_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, lab_number) VALUES (?, 'MLIS-H1')", (c1_id,))
    v1_id = cur.lastrowid
    cur.execute("SELECT id FROM tests WHERE name = 'Absolute CD4 Count (Cytometry)'")
    t1_id = cur.fetchone()[0]
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v1_id, t1_id))
    o1_id = cur.lastrowid
    conn.commit()

    c.post("/api/clients/results", json={"order_id": o1_id, "result_value": "150"})

    # Enter 1 CD4 RDT Below 200 (AHD positive)
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('CD4-H2', 'CLIENT TWO', 'Female')")
    c2_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, lab_number) VALUES (?, 'MLIS-H2')", (c2_id,))
    v2_id = cur.lastrowid
    cur.execute("SELECT id FROM tests WHERE name = 'CD4 Count (Rapid Test Strip)'")
    t2_id = cur.fetchone()[0]
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v2_id, t2_id))
    o2_id = cur.lastrowid
    conn.commit()

    c.post("/api/clients/results", json={"order_id": o2_id, "result_value": "CD4 Count: Below 200 cells/µL"})

    # Check HMIS 105 report
    res = c.get("/api/reports/hmis105")
    assert res.status_code == 200
    items = {item["disease_test"]: item for item in res.json()["surveillance_items"]}

    assert "Absolute CD4 Count (Cytometry)" in items
    assert items["Absolute CD4 Count (Cytometry)"]["tests_done"] == 1
    assert items["Absolute CD4 Count (Cytometry)"]["positive_cases"] == 1

    assert "CD4 Count (Rapid Test Strip)" in items
    assert items["CD4 Count (Rapid Test Strip)"]["tests_done"] == 1
    assert items["CD4 Count (Rapid Test Strip)"]["positive_cases"] == 1
