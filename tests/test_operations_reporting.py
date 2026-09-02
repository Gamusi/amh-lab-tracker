import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import get_current_user
from backend.app.database import get_db

client = TestClient(app)

def test_operations_reporting_aggregates(db_connection):
    conn = db_connection
    cur = conn.cursor()

    def override_get_db():
        try:
            yield conn
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Seed user, section, and test
    cur.execute("INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role, is_active) VALUES (1, 'admin1', 'hash', 'Dr. Sarah Namutebi', 'admin', 1)")
    cur.execute("INSERT OR IGNORE INTO sections (id, name, sort_order) VALUES (1, 'Hematology', 1), (2, 'Clinical Biochemistry', 2)")
    cur.execute("INSERT INTO tests (name, section_id, is_active) VALUES ('Complete Blood Count (CBC)', 1, 1)")
    cbc_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active) VALUES ('Lipid Profile', 2, 1)")
    lipid_id = cur.lastrowid

    # Seed client and visit with ward of origin
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-OPS-1', 'Operations Test Client', 'Female')")
    cid = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin, lab_number, created_at) VALUES (?, 'Maternity', 'AMH-26-8-001', '2026-08-24 08:00:00')", (cid,))
    vid = cur.lastrowid

    # Order Routine CBC
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status, ordered_at, order_category) VALUES (?, ?, 'completed', '2026-08-24 08:05:00', 'in-house')", (vid, cbc_id))
    oid = cur.lastrowid

    cur.execute("""
        INSERT INTO test_results (order_id, result_value, entered_by_user_id, entered_at, verified_by_user_id, verified_at)
        VALUES (?, 'Completed', 1, '2026-08-24 08:35:00', 1, '2026-08-24 08:45:00')
    """, (oid,))
    conn.commit()

    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin1", "full_name": "Dr. Sarah Namutebi", "role": "admin"}
    res = client.get("/api/reports/operations?period_type=Month&reference_date=2026-08-24")
    assert res.status_code == 200
    data = res.json()

    # Formatted period
    assert data["period"]["formatted_period"] == "August, 2026"

    # 3 Core KPIs
    summary = data["summary"]
    assert summary["total_done"] >= 1
    assert summary["total_clients"] >= 1
    assert summary["menu_coverage_percent"] > 0

    # Categories breakdown (In-House, Referral, Outreach, Self-Request)
    assert len(data["categories_breakdown"]) == 4
    in_house = next((c for c in data["categories_breakdown"] if c["category"] == "In-House"), None)
    assert in_house is not None
    assert in_house["count"] >= 1

    # Sections breakdown with range
    assert len(data["sections_breakdown"]) >= 1
    hem_sec = next((s for s in data["sections_breakdown"] if s["section_name"] == "Hematology"), None)
    assert hem_sec is not None
    assert hem_sec["test_count"] >= 1

    # Ward of Origin breakdown
    assert any(w["ward"] == "Maternity" for w in data["wards_breakdown"])

    # Demand Dynamics: Top 5, Bottom 5, and Unrequested
    assert len(data["demand_dynamics"]["top_requested_tests"]) >= 1
    assert len(data["demand_dynamics"]["least_requested_tests"]) >= 1
    assert any(u["test_name"] == "Lipid Profile" for u in data["demand_dynamics"]["unrequested_tests"])

    # Appendix
    assert len(data["appendix_menu_activity"]) >= 2
    assert any(a["test_name"] == "Complete Blood Count (CBC)" and a["completed_count"] >= 1 for a in data["appendix_menu_activity"])

def test_operations_reporting_pdf_generation(db_connection):
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
    
    res = client.get("/api/reports/operations/pdf?period_type=Month&reference_date=2026-08-24")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1000

def test_operations_category_and_appendix(db_connection):
    conn = db_connection
    cur = conn.cursor()

    def override_get_db():
        try:
            yield conn
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    cur.execute("INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role, is_active) VALUES (1, 'admin1', 'hash', 'Dr. Sarah Namutebi', 'admin', 1)")
    cur.execute("INSERT OR IGNORE INTO sections (id, name, sort_order) VALUES (1, 'Hematology', 1)")
    cur.execute("INSERT INTO tests (name, section_id, is_active) VALUES ('CBC Outreach', 1, 1)")
    cbc_id = cur.lastrowid

    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('AMH-OUT-1', 'Outreach Client', 'Male')")
    cid = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin, lab_number, created_at) VALUES (?, 'Community Outreach', 'AMH-26-8-002', '2026-08-24 09:00:00')", (cid,))
    vid = cur.lastrowid

    cur.execute("INSERT INTO test_orders (visit_id, test_id, status, ordered_at, order_category) VALUES (?, ?, 'completed', '2026-08-24 09:05:00', 'outreach')", (vid, cbc_id))
    oid = cur.lastrowid

    cur.execute("""
        INSERT INTO test_results (order_id, result_value, entered_by_user_id, entered_at, verified_by_user_id, verified_at)
        VALUES (?, 'Completed', 1, '2026-08-24 09:20:00', 1, '2026-08-24 09:25:00')
    """, (oid,))
    conn.commit()

    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin1", "full_name": "Dr. Sarah Namutebi", "role": "admin"}
    res = client.get("/api/reports/operations?period_type=Month&reference_date=2026-08-24")
    assert res.status_code == 200
    data = res.json()

    outreach = next((c for c in data["categories_breakdown"] if c["category"] == "Outreach"), None)
    assert outreach is not None
    assert outreach["count"] >= 1
