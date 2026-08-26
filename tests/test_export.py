import io
import csv
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user, require_admin

client = TestClient(app)

@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    cur = conn.cursor()
    # Pre-seed user
    cur.execute("INSERT INTO users (id, full_name, username, password_hash, role) VALUES (1, 'Admin User', 'admin1', 'hash', 'admin')")
    cur.execute("INSERT INTO users (id, full_name, username, password_hash, role) VALUES (2, 'Staff User', 'staff1', 'hash', 'staff')")
    
    # Pre-seed clinician
    cur.execute("INSERT INTO clinicians (id, name) VALUES (1, 'Dr. Sarah')")
    
    # Pre-seed section and tests
    cur.execute("INSERT INTO sections (id, name, sort_order) VALUES (1, 'Hematology', 1)")
    cur.execute("INSERT INTO tests (id, name, section_id, is_active, is_tracked) VALUES (1, 'CBC', 1, 1, 1)")
    cur.execute("INSERT INTO test_parameters (id, test_id, parameter_name, unit) VALUES (1, 1, 'WBC', 'x10^9/L')")
    cur.execute("INSERT INTO test_parameters (id, test_id, parameter_name, unit) VALUES (2, 1, 'Hemoglobin', 'g/dL')")
    
    cur.execute("INSERT INTO tests (id, name, section_id, is_active, is_tracked) VALUES (2, 'BS for MPS', 1, 1, 1)")
    conn.commit()
    
    def override_get_db():
        yield conn
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin1", "full_name": "Admin User", "role": "admin"}
    app.dependency_overrides[require_admin] = lambda: {"id": 1, "username": "admin1", "full_name": "Admin User", "role": "admin"}
    
    yield {
        "conn": conn
    }
    
    app.dependency_overrides.clear()
    conn.close()

def test_clients_export_csv_and_json(test_db):
    conn = test_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex, age_years, phone, created_at) VALUES ('AMH-EXP-01', 'Alice Nabirye', 'Female', 28, '0771234567', '2026-08-01 10:00:00')")
    cur.execute("INSERT INTO clients (client_number, full_name, sex, age_years, phone, created_at) VALUES ('AMH-EXP-02', 'Bob Kato', 'Male', 35, '0777654321', '2026-08-02 11:30:00')")
    conn.commit()
    
    # CSV Export
    res_csv = client.get("/api/export/clients?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "attachment; filename=clients_export_" in res_csv.headers["content-disposition"]
    reader = list(csv.DictReader(io.StringIO(res_csv.text)))
    assert len(reader) >= 2
    assert any(r["client_number"] == "AMH-EXP-01" for r in reader)
    assert any(r["full_name"] == "Alice Nabirye" for r in reader)
    
    # JSON Export
    res_json = client.get("/api/export/clients?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    items = json.loads(res_json.text)
    assert isinstance(items, list)
    assert len(items) >= 2
    assert any(item["client_number"] == "AMH-EXP-02" for item in items)

def test_results_export_csv_and_json(test_db):
    conn = test_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex, age_years) VALUES ('AMH-C26-001', 'Grace Mukasa', 'Female', 42)")
    cid = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, clinician_id, ward_of_origin, lab_number, created_at) VALUES (?, 1, 'Maternity', 'AMH-26-8-001', '2026-08-10 09:00:00')", (cid,))
    vid = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, 1, 'completed')", (vid,))
    oid = cur.lastrowid
    cur.execute("INSERT INTO test_results (order_id, parameter_id, result_value, result_unit, clinical_flag, is_positive, entered_by_user_id) VALUES (?, 1, '7.5', 'x10^9/L', 'NORMAL', 0, 1)", (oid,))
    conn.commit()
    
    # CSV Export
    res_csv = client.get("/api/export/results?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    reader = list(csv.DictReader(io.StringIO(res_csv.text)))
    assert len(reader) >= 1
    row = reader[0]
    assert row["lab_number"] == "AMH-26-8-001"
    assert row["full_name"] == "Grace Mukasa"
    assert row["parameter_name"] == "WBC"
    assert row["result_value"] == "7.5"
    
    # JSON Export
    res_json = client.get("/api/export/results?format=json")
    assert res_json.status_code == 200
    items = json.loads(res_json.text)
    assert len(items) >= 1
    assert items[0]["lab_number"] == "AMH-26-8-001"
    assert items[0]["clinician_name"] == "Dr. Sarah"

def test_non_admin_export_rejected(test_db):
    app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(pytest.importorskip("fastapi").HTTPException(status_code=403, detail="Admin privileges required"))
    
    res = client.get("/api/export/clients")
    assert res.status_code == 403
    
    res2 = client.get("/api/export/results")
    assert res2.status_code == 403

def test_import_clients_round_trip(test_db):
    csv_payload = (
        "client_number,full_name,date_of_birth,age_years,age_category,sex,phone,created_at\n"
        "AMH-IMP-01,Test Client One,1990-01-01,36,Adult,Male,0700111222,2026-08-01 08:00:00\n"
        "AMH-IMP-02,Test Client Two,,24,Adult,Female,0700333444,2026-08-02 09:00:00\n"
    )
    
    # Test Dry Run
    res_dry = client.post("/api/import/clients?dry_run=true", content=csv_payload)
    assert res_dry.status_code == 200
    dry_data = res_dry.json()
    assert dry_data["total"] == 2
    assert dry_data["inserted"] == 2
    assert dry_data["dry_run"] is True
    
    # Verify records not persisted
    conn = test_db["conn"]
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM clients WHERE client_number LIKE 'AMH-IMP%'")
    assert cur.fetchone()["c"] == 0
    
    # Test Actual Import
    res_import = client.post("/api/import/clients", content=csv_payload)
    assert res_import.status_code == 200
    import_data = res_import.json()
    assert import_data["inserted"] == 2
    
    cur.execute("SELECT * FROM clients WHERE client_number = 'AMH-IMP-01'")
    c1 = cur.fetchone()
    assert c1 is not None
    assert c1["full_name"] == "Test Client One"
    assert c1["sex"] == "Male"

    # Test Update existing on second import
    update_payload = [
        {"client_number": "AMH-IMP-01", "full_name": "Test Client One Renamed", "phone": "0799999999"}
    ]
    res_upd = client.post("/api/import/clients", json=update_payload)
    assert res_upd.status_code == 200
    assert res_upd.json()["updated"] == 1
    
    cur.execute("SELECT * FROM clients WHERE client_number = 'AMH-IMP-01'")
    c1_upd = cur.fetchone()
    assert c1_upd["full_name"] == "Test Client One Renamed"
    assert c1_upd["phone"] == "0799999999"

def test_import_results_round_trip(test_db):
    results_json = [
        {
            "lab_number": "AMH-26-8-999",
            "visit_date": "2026-08-20 14:00:00",
            "ward_of_origin": "OPD",
            "order_category": "in-house",
            "client_number": "AMH-IMP-99",
            "full_name": "Imported Results Client",
            "sex": "Female",
            "age_years": 29,
            "clinician_name": "Dr. Sarah",
            "test_name": "CBC",
            "parameter_name": "Hemoglobin",
            "result_value": "13.2",
            "result_unit": "g/dL",
            "clinical_flag": "NORMAL",
            "is_positive": 0,
            "entered_by": "admin1"
        }
    ]
    
    res = client.post("/api/import/results", json=results_json)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["inserted"] == 1
    
    conn = test_db["conn"]
    cur = conn.cursor()
    cur.execute("SELECT * FROM visits WHERE lab_number = 'AMH-26-8-999'")
    v = cur.fetchone()
    assert v is not None
    
    cur.execute("SELECT tr.* FROM test_results tr JOIN test_orders ord ON tr.order_id = ord.id WHERE ord.visit_id = ?", (v["id"],))
    tr = cur.fetchone()
    assert tr is not None
    assert tr["result_value"] == "13.2"
    assert tr["result_unit"] == "g/dL"

def test_audit_logging_on_export_and_import(test_db):
    client.get("/api/export/clients?format=csv")
    client.post("/api/import/clients", json=[{"full_name": "Audit Client"}])
    
    conn = test_db["conn"]
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_log WHERE action IN ('BULK_EXPORT', 'BULK_IMPORT')")
    logs = cur.fetchall()
    assert len(logs) >= 2
