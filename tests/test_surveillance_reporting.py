import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import get_current_user
from backend.app.database import get_db

client = TestClient(app)

def test_surveillance_reporting_aggregates(db_connection):
    conn = db_connection
    cur = conn.cursor()

    def override_get_db():
        try:
            yield conn
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Seed user, sections, and tracked tests
    cur.execute("INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role, is_active) VALUES (1, 'admin1', 'hash', 'Dr. Sarah Namutebi', 'admin', 1)")
    cur.execute("INSERT OR IGNORE INTO sections (id, name, sort_order) VALUES (1, 'Hematology', 1), (3, 'Serology & Clinical Immunology', 3)")
    
    # Tracked test 1: Malaria RDT (Binary)
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('Malaria RDT', 3, 1, 1)")
    malaria_id = cur.lastrowid

    # Tracked test 2: CBC (Panel with test_parameters)
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('Complete Blood Count (CBC)', 1, 1, 1)")
    cbc_id = cur.lastrowid
    cur.execute("INSERT INTO test_parameters (test_id, parameter_name, unit, sort_order) VALUES (?, 'Hemoglobin (Hb)', 'g/dL', 1)", (cbc_id,))
    hb_param_id = cur.lastrowid

    # Untracked test: ESR
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('ESR', 1, 1, 0)")
    esr_id = cur.lastrowid

    # Seed Client 1 with Positive Malaria
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-SURV-1', 'Surveillance Client 1', 'Female')")
    cid1 = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin, lab_number, created_at) VALUES (?, 'Maternity', 'AMH-26-8-001', '2026-08-24 08:00:00')", (cid1,))
    vid1 = cur.lastrowid

    cur.execute("INSERT INTO test_orders (visit_id, test_id, status, ordered_at, order_category) VALUES (?, ?, 'completed', '2026-08-24 08:05:00', 'in-house')", (vid1, malaria_id))
    oid1 = cur.lastrowid
    cur.execute("""
        INSERT INTO test_results (order_id, result_value, is_positive, entered_by_user_id, entered_at, verified_by_user_id, verified_at)
        VALUES (?, 'Positive', 1, 1, '2026-08-24 08:35:00', 1, '2026-08-24 08:45:00')
    """, (oid1,))

    # Seed Client 2 with CBC Severe / Critical Anemia (Hb = 6.5 < 8.0) -> MUST count as positive incident
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-SURV-2', 'Surveillance Client 2', 'Male')")
    cid2 = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin, lab_number, created_at) VALUES (?, 'Outpatient / GOPD', 'AMH-26-8-002', '2026-08-24 09:00:00')", (cid2,))
    vid2 = cur.lastrowid

    cur.execute("INSERT INTO test_orders (visit_id, test_id, status, ordered_at, order_category) VALUES (?, ?, 'completed', '2026-08-24 09:05:00', 'in-house')", (vid2, cbc_id))
    oid2 = cur.lastrowid
    cur.execute("""
        INSERT INTO test_results (order_id, parameter_id, result_value, is_positive, clinical_flag, entered_by_user_id, entered_at, verified_by_user_id, verified_at)
        VALUES (?, ?, '6.5', 1, 'L*', 1, '2026-08-24 09:20:00', 1, '2026-08-24 09:25:00')
    """, (oid2, hb_param_id))

    # Seed Client 3 with CBC Mild Anemia (Hb = 11.8, flag L) -> MUST NOT count as positive incident
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-SURV-3', 'Surveillance Client 3', 'Female')")
    cid3 = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin, lab_number, created_at) VALUES (?, 'Outpatient / GOPD', 'AMH-26-8-003', '2026-08-24 10:00:00')", (cid3,))
    vid3 = cur.lastrowid

    cur.execute("INSERT INTO test_orders (visit_id, test_id, status, ordered_at, order_category) VALUES (?, ?, 'completed', '2026-08-24 10:05:00', 'in-house')", (vid3, cbc_id))
    oid3 = cur.lastrowid
    cur.execute("""
        INSERT INTO test_results (order_id, parameter_id, result_value, is_positive, clinical_flag, entered_by_user_id, entered_at, verified_by_user_id, verified_at)
        VALUES (?, ?, '11.8', 0, 'L', 1, '2026-08-24 10:20:00', 1, '2026-08-24 10:25:00')
    """, (oid3, hb_param_id))

    conn.commit()

    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin1", "full_name": "Dr. Sarah Namutebi", "role": "admin"}
    res = client.get("/api/reports/surveillance?period_type=Month&reference_date=2026-08-24")
    assert res.status_code == 200
    data = res.json()

    # Formatted period
    assert data["period"]["formatted_period"] == "August, 2026"

    # Core KPIs
    summary = data["summary"]
    assert summary["total_evaluated"] == 3 # 1 Malaria + 2 CBCs
    assert summary["total_incident_cases"] == 2 # 1 Malaria + 1 Critical Anemia (Hb 6.5). Mild Anemia (Hb 11.8) is NOT incident.
    assert round(summary["overall_incidence_rate"], 1) == 66.7

    # Disease / Condition Ledger
    ledger = data["surveillance_ledger"]
    cbc_item = next((item for item in ledger if item["test_name"] == "Complete Blood Count (CBC)"), None)
    assert cbc_item is not None
    assert cbc_item["evaluated"] == 2
    assert cbc_item["positive"] == 1
    assert cbc_item["negative"] == 1
    assert cbc_item["incidence_rate"] == 50.0

def test_surveillance_reporting_pdf_generation(db_connection):
    conn = db_connection
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role, is_active) VALUES (1, 'admin1', 'hash', 'Dr. Sarah Namutebi', 'admin', 1)")
    conn.commit()

    def override_get_db():
        try:
            yield conn
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin1", "full_name": "Dr. Sarah Namutebi", "role": "admin"}
    
    res = client.get("/api/reports/surveillance/pdf?period_type=Month&reference_date=2026-08-24")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1000
