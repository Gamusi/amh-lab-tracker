import datetime
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user

client = TestClient(app)

@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    # Pre-seed clinician 'SELF REQUEST'
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO clinicians (name) VALUES ('SELF REQUEST')")
    
    # Pre-seed a test section and test
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Hematology', 1)")
    sec_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('CBC', ?, 1, 1)", (sec_id,))
    cbc_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('BS for MPS', ?, 1, 1)", (sec_id,))
    mps_id = cur.lastrowid
    
    # Insert test parameters for CBC
    cur.execute("INSERT INTO test_parameters (test_id, parameter_name, unit, ref_range, sort_order) VALUES (?, 'WBC', 'x10^9/L', '4.0-10.0', 1)", (cbc_id,))
    wbc_param_id = cur.lastrowid
    cur.execute("INSERT INTO test_parameters (test_id, parameter_name, unit, ref_range, sort_order) VALUES (?, 'Hemoglobin', 'g/dL', '12.0-16.0', 2)", (cbc_id,))
    hb_param_id = cur.lastrowid
    
    conn.commit()
    
    def override_get_db():
        yield conn
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "labtech1", "full_name": "Lab Technician"}
    
    yield {
        "conn": conn,
        "section_id": sec_id,
        "cbc_id": cbc_id,
        "mps_id": mps_id,
        "wbc_param_id": wbc_param_id,
        "hb_param_id": hb_param_id
    }
    
    app.dependency_overrides.clear()
    conn.close()

def test_list_clinicians(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clinicians (name, is_active) VALUES ('Dr. Mugisha', 1)")
    cur.execute("INSERT INTO clinicians (name, is_active) VALUES ('Dr. Inactive', 0)")
    conn.commit()
    
    response = client.get("/api/clinicians")
    assert response.status_code == 200
    data = response.json()
    names = [c["name"] for c in data]
    assert "SELF REQUEST" in names
    assert "Dr. Mugisha" in names
    assert "Dr. Inactive" not in names

def test_create_visit_success(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-001', 'Alice Nabirye', 'Female')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO clinicians (name) VALUES ('Dr. Okello')")
    clinician_id = cur.lastrowid
    conn.commit()
    
    payload = {
        "client_id": client_id,
        "clinician_id": clinician_id,
        "ward_of_origin": "Maternity",
        "test_ids": [mock_db["cbc_id"], mock_db["mps_id"]],
        "sample_id": "SAMP-101"
    }
    
    response = client.post("/api/visits", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert "visit_id" in data
    
    visit_id = data["visit_id"]
    cur.execute("SELECT * FROM visits WHERE id = ?", (visit_id,))
    v_row = cur.fetchone()
    assert v_row is not None
    assert v_row["client_id"] == client_id
    assert v_row["clinician_id"] == clinician_id
    assert v_row["ward_of_origin"] == "Maternity"
    assert v_row["lab_number"] is None  # Initialized as NULL before result entry
    
    cur.execute("SELECT * FROM test_orders WHERE visit_id = ?", (visit_id,))
    orders = cur.fetchall()
    assert len(orders) == 2
    assert {o["test_id"] for o in orders} == {mock_db["cbc_id"], mock_db["mps_id"]}
    for o in orders:
        assert o["status"] == "pending"
        assert o["ordered_by_user_id"] == 1

def test_create_visit_validations(mock_db):
    # Non-existent client
    res = client.post("/api/visits", json={"client_id": 9999, "test_ids": [mock_db["cbc_id"]]})
    assert res.status_code == 404
    assert "Client not found" in res.json()["detail"]
    
    # Valid client, invalid clinician
    conn = mock_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-002', 'Ben Mukasa', 'Male')")
    cid = cur.lastrowid
    conn.commit()
    
    res = client.post("/api/visits", json={"client_id": cid, "clinician_id": 9999, "test_ids": [mock_db["cbc_id"]]})
    assert res.status_code == 400
    assert "Clinician not found" in res.json()["detail"]
    
    # Empty test_ids
    res = client.post("/api/visits", json={"client_id": cid, "test_ids": []})
    assert res.status_code == 400
    
    # Invalid test_id
    res = client.post("/api/visits", json={"client_id": cid, "test_ids": [9999]})
    assert res.status_code == 404

def test_enter_result_sets_verification_and_sequential_lab_number(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    
    # Create client and visit 1
    cur.execute("INSERT INTO clients (client_number, full_name, date_of_birth, sex) VALUES ('AMH-100', 'Grace Nalubega', '1995-05-10', 'Female')")
    c1_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin) VALUES (?, 'OPD')", (c1_id,))
    v1_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v1_id, mock_db["mps_id"]))
    order1_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v1_id, mock_db["cbc_id"]))
    order2_id = cur.lastrowid
    conn.commit()
    
    # Enter single result for Order 1
    res1 = client.post("/api/results", json={
        "order_id": order1_id,
        "result_value": "Negative",
        "is_positive": False
    })
    assert res1.status_code == 200
    res1_data = res1.json()
    assert res1_data["status"] == "result_saved"
    
    ym_str = datetime.date.today().strftime("%y-%m")
    expected_lab_no_1 = f"amh-{ym_str}-1"
    assert res1_data["lab_number"] == expected_lab_no_1
    
    # Check visit 1 lab number is now assigned
    cur.execute("SELECT lab_number FROM visits WHERE id = ?", (v1_id,))
    v1_row = cur.fetchone()
    assert v1_row["lab_number"] == expected_lab_no_1
    
    # Check test result verified fields
    cur.execute("SELECT * FROM test_results WHERE order_id = ?", (order1_id,))
    tr1 = cur.fetchone()
    assert tr1["entered_by_user_id"] == 1
    assert tr1["verified_by_user_id"] == 1
    assert tr1["verified_at"] is not None
    
    # Check order status
    cur.execute("SELECT status FROM test_orders WHERE id = ?", (order1_id,))
    assert cur.fetchone()["status"] == "completed"
    
    # Enter parameter results for Order 2 (same visit)
    res2 = client.post("/api/results", json={
        "order_id": order2_id,
        "parameter_results": [
            {"parameter_id": mock_db["wbc_param_id"], "result_value": "6.5", "is_positive": False},
            {"parameter_id": mock_db["hb_param_id"], "result_value": "13.8", "is_positive": False}
        ]
    })
    assert res2.status_code == 200
    # Lab number should remain the same for the visit, NOT incremented again
    assert res2.json()["lab_number"] == expected_lab_no_1
    
    cur.execute("SELECT lab_number FROM visits WHERE id = ?", (v1_id,))
    assert cur.fetchone()["lab_number"] == expected_lab_no_1
    
    # Check sequence tracker value is still 1
    seq_name = f"lab_number_{ym_str.replace('-', '_')}"
    cur.execute("SELECT last_value FROM sequence_tracker WHERE seq_name = ?", (seq_name,))
    assert cur.fetchone()["last_value"] == 1
    
    # Now create Visit 2 for another client in the same month
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-101', 'David Kintu', 'Male')")
    c2_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin) VALUES (?, 'Emergency')", (c2_id,))
    v2_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (v2_id, mock_db["mps_id"]))
    order3_id = cur.lastrowid
    conn.commit()
    
    # Enter result for Visit 2 -> sequence should increment to 2
    res3 = client.post("/api/results", json={
        "order_id": order3_id,
        "result_value": "Positive (+++)",
        "is_positive": True
    })
    assert res3.status_code == 200
    expected_lab_no_2 = f"amh-{ym_str}-2"
    assert res3.json()["lab_number"] == expected_lab_no_2
    
    cur.execute("SELECT lab_number FROM visits WHERE id = ?", (v2_id,))
    assert cur.fetchone()["lab_number"] == expected_lab_no_2
    
    cur.execute("SELECT last_value FROM sequence_tracker WHERE seq_name = ?", (seq_name,))
    assert cur.fetchone()["last_value"] == 2

def test_visit_pdf_report_generation(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    
    cur.execute("INSERT INTO clients (client_number, full_name, date_of_birth, sex) VALUES ('AMH-200', 'Sarah Namutebi', '1998-03-15', 'Female')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO clinicians (name) VALUES ('Dr. Kato')")
    clinician_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, clinician_id, ward_of_origin) VALUES (?, ?, 'GOPD')", (client_id, clinician_id))
    visit_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (visit_id, mock_db["cbc_id"]))
    order_id = cur.lastrowid
    conn.commit()
    
    # Save result (which verifies and generates lab number)
    res = client.post("/api/results", json={
        "order_id": order_id,
        "result_value": "14.2 g/dL"
    })
    assert res.status_code == 200
    
    # Fetch PDF report by visit_id
    pdf_res = client.get(f"/api/reports/visit/{visit_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b'%PDF-')
    
    # Backward compatibility: fetch by client_id
    client_pdf_res = client.get(f"/api/reports/client/{client_id}/pdf")
    assert client_pdf_res.status_code == 200
    assert client_pdf_res.headers["content-type"] == "application/pdf"
    assert client_pdf_res.content.startswith(b'%PDF-')
    
    # 404 for non-existent visit
    not_found_res = client.get("/api/reports/visit/99999/pdf")
    assert not_found_res.status_code == 404

def test_wards_crud_endpoints(mock_db):
    # 1. GET empty wards list
    res = client.get("/api/config/wards")
    assert res.status_code == 200
    assert res.json() == []

    # 2. POST create ward
    res = client.post("/api/config/wards", json={"name": "Maternity"})
    assert res.status_code == 200
    w1 = res.json()
    assert w1["name"] == "Maternity"
    assert w1["is_active"] is True
    assert "id" in w1

    # Create second ward
    res = client.post("/api/config/wards", json={"name": "Emergency"})
    assert res.status_code == 200
    w2 = res.json()
    assert w2["name"] == "Emergency"

    # Validation: Duplicate name
    res = client.post("/api/config/wards", json={"name": "maternity"})
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]

    # Validation: Empty name
    res = client.post("/api/config/wards", json={"name": "   "})
    assert res.status_code == 400

    # 3. GET list wards (alphabetical order)
    res = client.get("/api/config/wards")
    assert res.status_code == 200
    ward_names = [w["name"] for w in res.json()]
    assert ward_names == ["Emergency", "Maternity"]

    # 4. PUT update ward name
    res = client.put(f"/api/config/wards/{w1['id']}", json={"name": "Maternity Ward"})
    assert res.status_code == 200
    assert res.json()["name"] == "Maternity Ward"

    # PUT validation: duplicate name
    res = client.put(f"/api/config/wards/{w1['id']}", json={"name": "Emergency"})
    assert res.status_code == 400

    # 5. DELETE ward (soft delete is_active=0)
    res = client.delete(f"/api/config/wards/{w2['id']}")
    assert res.status_code == 200
    assert res.json() == {"status": "deleted"}

    # Verify soft delete in active_only query
    res = client.get("/api/config/wards?active_only=true")
    assert res.status_code == 200
    active_names = [w["name"] for w in res.json()]
    assert active_names == ["Maternity Ward"]

    # 6. Not found cases
    res = client.put("/api/config/wards/99999", json={"name": "Ghost Ward"})
    assert res.status_code == 404

    res = client.delete("/api/config/wards/99999")
    assert res.status_code == 404

def test_clinicians_crud_endpoints(mock_db):
    # 1. GET clinicians list (contains pre-seeded SELF REQUEST)
    res = client.get("/api/config/clinicians")
    assert res.status_code == 200
    names = [c["name"] for c in res.json()]
    assert "SELF REQUEST" in names

    # 2. POST create clinician
    res = client.post("/api/config/clinicians", json={"name": "Dr. Sarah"})
    assert res.status_code == 200
    c1 = res.json()
    assert c1["name"] == "Dr. Sarah"
    assert c1["is_active"] is True

    # Duplicate name validation
    res = client.post("/api/config/clinicians", json={"name": "dr. sarah"})
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]

    # Empty name validation
    res = client.post("/api/config/clinicians", json={"name": "   "})
    assert res.status_code == 400

    # 3. PUT update clinician
    res = client.put(f"/api/config/clinicians/{c1['id']}", json={"name": "Dr. Sarah Namubiru"})
    assert res.status_code == 200
    assert res.json()["name"] == "Dr. Sarah Namubiru"

    # 4. DELETE soft-delete clinician
    res = client.delete(f"/api/config/clinicians/{c1['id']}")
    assert res.status_code == 200
    assert res.json() == {"status": "deleted"}

    # Verify active_only filter
    res = client.get("/api/config/clinicians?active_only=true")
    assert res.status_code == 200
    active_names = [c["name"] for c in res.json()]
    assert "Dr. Sarah Namubiru" not in active_names

    # 5. Not found cases
    res = client.put("/api/config/clinicians/99999", json={"name": "Ghost"})
    assert res.status_code == 404
    res = client.delete("/api/config/clinicians/99999")
    assert res.status_code == 404


def test_seed_database_wards(tmp_path, monkeypatch):
    from backend.app.seed import seed_database
    from backend.app.database import get_connection

    test_db_file = str(tmp_path / "seed_test.db")
    monkeypatch.setattr("backend.app.database.DB_PATH", test_db_file)

    seed_database()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name, is_active FROM wards ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()

    seeded_wards = {r["name"] for r in rows}
    expected_wards = {"ANC", "MCH", "Emergency", "Theater", "Labour", "OPD", "IPD", "Pediatrics", "TB Clinic"}
    assert expected_wards.issubset(seeded_wards)
    for r in rows:
        assert r["is_active"] == 1

def test_add_orders_to_visit(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-301', 'Test Client', 'Male')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin) VALUES (?, 'OPD')", (client_id,))
    visit_id = cur.lastrowid
    conn.commit()

    # Success: Add test orders to visit
    res = client.post(f"/api/visits/{visit_id}/orders", json={"test_ids": [mock_db["cbc_id"], mock_db["mps_id"]]})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "orders_added"
    assert data["visit_id"] == visit_id
    assert len(data["order_ids"]) == 2

    # Check orders in DB
    cur.execute("SELECT * FROM test_orders WHERE visit_id = ?", (visit_id,))
    orders = cur.fetchall()
    assert len(orders) == 2

    # Validation: Non-existent visit
    res_404 = client.post("/api/visits/99999/orders", json={"test_ids": [mock_db["cbc_id"]]})
    assert res_404.status_code == 404

    # Validation: Empty test_ids
    res_empty = client.post(f"/api/visits/{visit_id}/orders", json={"test_ids": []})
    assert res_empty.status_code == 400

    # Validation: Invalid test_id
    res_invalid_test = client.post(f"/api/visits/{visit_id}/orders", json={"test_ids": [99999]})
    assert res_invalid_test.status_code == 404

def test_enter_result_auto_positive_evaluation_text(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-302', 'Tracked Client', 'Female')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin) VALUES (?, 'OPD')", (client_id,))
    visit_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (visit_id, mock_db["mps_id"]))
    order_pos_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (visit_id, mock_db["mps_id"]))
    order_neg_id = cur.lastrowid
    conn.commit()

    # Enter positive result (without passing is_positive in request)
    res_pos = client.post("/api/results", json={
        "order_id": order_pos_id,
        "result_value": "Reactive"
    })
    assert res_pos.status_code == 200
    cur.execute("SELECT is_positive FROM test_results WHERE order_id = ?", (order_pos_id,))
    assert cur.fetchone()["is_positive"] == 1

    # Enter negative result (without passing is_positive in request)
    res_neg = client.post("/api/results", json={
        "order_id": order_neg_id,
        "result_value": "Negative"
    })
    assert res_neg.status_code == 200
    cur.execute("SELECT is_positive FROM test_results WHERE order_id = ?", (order_neg_id,))
    assert cur.fetchone()["is_positive"] == 0

def test_enter_result_auto_positive_evaluation_numeric(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    # Pre-seed WBC test
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('WBC', ?, 1, 1)", (mock_db["section_id"],))
    wbc_test_id = cur.lastrowid

    # 35 year old Male
    cur.execute("INSERT INTO clients (client_number, full_name, date_of_birth, sex) VALUES ('AMH-303', 'Adult Male', '1990-01-01', 'Male')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin) VALUES (?, 'OPD')", (client_id,))
    visit_id = cur.lastrowid

    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (visit_id, wbc_test_id))
    order_high_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (visit_id, wbc_test_id))
    order_norm_id = cur.lastrowid
    conn.commit()

    # WBC 15.0 -> High (normal adult WBC 4.0 - 11.0)
    res_high = client.post("/api/results", json={
        "order_id": order_high_id,
        "result_value": "15.0"
    })
    assert res_high.status_code == 200
    cur.execute("SELECT is_positive FROM test_results WHERE order_id = ?", (order_high_id,))
    assert cur.fetchone()["is_positive"] == 1

    # WBC 6.5 -> Normal
    res_norm = client.post("/api/results", json={
        "order_id": order_norm_id,
        "result_value": "6.5"
    })
    assert res_norm.status_code == 200
    cur.execute("SELECT is_positive FROM test_results WHERE order_id = ?", (order_norm_id,))
    assert cur.fetchone()["is_positive"] == 0

def test_enter_result_parameter_results_auto_evaluation(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    # 35 year old Female -> normal Hb is 12.0 - 15.5
    cur.execute("INSERT INTO clients (client_number, full_name, date_of_birth, sex) VALUES ('AMH-304', 'Adult Female', '1990-01-01', 'Female')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin) VALUES (?, 'OPD')", (client_id,))
    visit_id = cur.lastrowid

    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (visit_id, mock_db["cbc_id"]))
    order_id = cur.lastrowid
    conn.commit()

    # Hb is 9.5 (Low for female -> abnormal), WBC is 7.0 (Normal)
    res = client.post("/api/results", json={
        "order_id": order_id,
        "parameter_results": [
            {"parameter_id": mock_db["wbc_param_id"], "result_value": "7.0"},
            {"parameter_id": mock_db["hb_param_id"], "result_value": "9.5"}
        ]
    })
    assert res.status_code == 200

    cur.execute("SELECT parameter_id, is_positive FROM test_results WHERE order_id = ?", (order_id,))
    rows = {r["parameter_id"]: r["is_positive"] for r in cur.fetchall()}
    assert rows[mock_db["wbc_param_id"]] == 0
    assert rows[mock_db["hb_param_id"]] == 1


