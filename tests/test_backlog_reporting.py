import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user, require_admin
from backend.app.operations_analytics import calculate_operations_metrics
from backend.app.surveillance_analytics import calculate_surveillance_metrics

client = TestClient(app)

@pytest.fixture
def reporting_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    cur = conn.cursor()
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Hematology', 1)")
    sec_id = cur.lastrowid
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Microbiology', 2)")
    micro_sec_id = cur.lastrowid
    
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('CBC', ?, 1, 1)", (sec_id,))
    cbc_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('Malaria RDT', ?, 1, 1)", (micro_sec_id,))
    malaria_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('Urinalysis', ?, 1, 0)", (sec_id,))
    uri_id = cur.lastrowid
    
    conn.commit()

    def override_get_db():
        yield conn

    user = {"id": 1, "username": "admin", "full_name": "Admin User", "role": "admin"}
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user

    yield {
        "conn": conn,
        "cbc_id": cbc_id,
        "malaria_id": malaria_id,
        "uri_id": uri_id
    }

    app.dependency_overrides.clear()
    conn.close()

def test_operations_analytics_blends_backlog(reporting_db):
    cur = reporting_db["conn"].cursor()
    # Insert historical backlog entries into backlog_entries
    cur.execute("""
        INSERT INTO backlog_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-07-10', 1, 50, 5, 30, 10, 8, 2)
    """)
    cur.execute("""
        INSERT INTO backlog_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-07-15', 2, 40, 12, 25, 5, 10, 0)
    """)
    reporting_db["conn"].commit()

    metrics = calculate_operations_metrics(reporting_db["conn"], period_type="Month", reference_date="2026-07-15")
    
    # Summary should include backlog 50 + 40 = 90
    assert metrics["summary"]["total_done"] == 90
    
    # Workload sources category breakdown
    cats = {c["category"]: c["count"] for c in metrics["categories_breakdown"]}
    assert cats.get("In-House", 0) == 55
    assert cats.get("Referral", 0) == 15
    assert cats.get("Outreach", 0) == 18
    assert cats.get("Self-Request", 0) == 2

def test_surveillance_analytics_blends_backlog(reporting_db):
    cur = reporting_db["conn"].cursor()
    cur.execute("""
        INSERT INTO backlog_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-08-05', 1, 30, 4, 20, 5, 5, 0)
    """)
    cur.execute("""
        INSERT INTO backlog_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-08-08', 2, 60, 15, 50, 5, 5, 0)
    """)
    reporting_db["conn"].commit()

    metrics = calculate_surveillance_metrics(reporting_db["conn"], period_type="Month", reference_date="2026-08-10")
    
    # Tracked tests: 30 + 60 = 90
    assert metrics["summary"]["total_evaluated"] == 90
    # Positive incident cases: 4 + 15 = 19
    assert metrics["summary"]["total_incident_cases"] == 19
    assert metrics["summary"]["overall_incidence_rate"] == 21.1

def test_daily_log_blends_routine_and_backlog_while_backlog_shows_only_backlog(reporting_db):
    cur = reporting_db["conn"].cursor()
    # Routine test entered on 2026-09-02 (e.g. from lab reports in daily_entries)
    cur.execute("""
        INSERT INTO daily_entries (entry_date, test_id, done, positive, in_house)
        VALUES ('2026-09-02', 1, 5, 1, 5)
    """)
    # Backlog test entered on 2026-09-02 (in backlog_entries)
    cur.execute("""
        INSERT INTO backlog_entries (entry_date, test_id, done, positive, in_house)
        VALUES ('2026-09-02', 1, 15, 3, 15)
    """)
    reporting_db["conn"].commit()

    # 1. Backlog endpoint must show ONLY backlog entries (done = 15)
    backlog_res = client.get("/api/backlog?date=2026-09-02")
    assert backlog_res.status_code == 200
    b_data = backlog_res.json()
    b_test = next(t for sec in b_data["sections"] for t in sec["tests"] if t["test_id"] == 1)
    assert b_test["done"] == 15
    assert b_test["positive"] == 3

    # 2. Daily Log endpoint must show combined total (5 + 15 = 20)
    daily_res = client.get("/api/daily-log?date=2026-09-02")
    assert daily_res.status_code == 200
    d_data = daily_res.json()
    d_test = next(t for sec in d_data["sections"] for t in sec["tests"] if t["test_id"] == 1)
    assert d_test["done"] == 20
    assert d_test["positive"] == 4
