import pytest
import sqlite3
from backend.app.database import SCHEMA_SQL
from backend.app.operations_analytics import calculate_operations_metrics
from backend.app.surveillance_analytics import calculate_surveillance_metrics

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
    yield conn
    conn.close()

def test_operations_analytics_blends_backlog(reporting_db):
    cur = reporting_db.cursor()
    # Insert historical backlog entries for July 2026
    cur.execute("""
        INSERT INTO daily_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-07-10', 1, 50, 5, 30, 10, 8, 2)
    """)
    cur.execute("""
        INSERT INTO daily_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-07-15', 2, 40, 12, 25, 5, 10, 0)
    """)
    reporting_db.commit()

    metrics = calculate_operations_metrics(reporting_db, period_type="Month", reference_date="2026-07-15")
    
    # Summary should include backlog 50 + 40 = 90
    assert metrics["summary"]["total_done"] == 90
    
    # Workload sources category breakdown
    cats = {c["category"]: c["count"] for c in metrics["categories_breakdown"]}
    assert cats.get("In-House", 0) == 55
    assert cats.get("Referral", 0) == 15
    assert cats.get("Outreach", 0) == 18
    assert cats.get("Self-Request", 0) == 2

def test_surveillance_analytics_blends_backlog(reporting_db):
    cur = reporting_db.cursor()
    cur.execute("""
        INSERT INTO daily_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-08-05', 1, 30, 4, 20, 5, 5, 0)
    """)
    cur.execute("""
        INSERT INTO daily_entries (entry_date, test_id, done, positive, in_house, referral, outreach, self_request)
        VALUES ('2026-08-08', 2, 60, 15, 50, 5, 5, 0)
    """)
    reporting_db.commit()

    metrics = calculate_surveillance_metrics(reporting_db, period_type="Month", reference_date="2026-08-10")
    
    # Tracked tests: 30 + 60 = 90
    assert metrics["summary"]["total_evaluated"] == 90
    # Positive incident cases: 4 + 15 = 19
    assert metrics["summary"]["total_incident_cases"] == 19
    assert metrics["summary"]["overall_incidence_rate"] == 21.1
