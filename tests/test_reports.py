import datetime
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user

client = TestClient(app)

@pytest.fixture
def reports_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    cur = conn.cursor()
    cur.execute("INSERT INTO users (full_name, username, password_hash, role) VALUES ('Staff Tech', 'staff', 'hash', 'staff')")
    staff_id = cur.lastrowid
    
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Hematology', 1)")
    sec1_id = cur.lastrowid
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Serology & Clinical Immunology', 2)")
    sec2_id = cur.lastrowid

    # CBC: tracked (Severe Anemia)
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('CBC', ?, 1, 1)", (sec1_id,))
    cbc_id = cur.lastrowid
    # ESR: untracked
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('E.S.R', ?, 1, 0)", (sec1_id,))
    esr_id = cur.lastrowid
    # Malaria RDT: tracked
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('Malaria RDT', ?, 1, 1)", (sec2_id,))
    mrdt_id = cur.lastrowid

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # Insert daily entries
    cur.execute("INSERT INTO daily_entries (entry_date, test_id, done, positive, entered_by_user_id) VALUES (?, ?, 20, 3, ?)", (today_str, cbc_id, staff_id))
    cur.execute("INSERT INTO daily_entries (entry_date, test_id, done, positive, entered_by_user_id) VALUES (?, ?, 15, NULL, ?)", (today_str, esr_id, staff_id))
    cur.execute("INSERT INTO daily_entries (entry_date, test_id, done, positive, entered_by_user_id) VALUES (?, ?, 30, 8, ?)", (today_str, mrdt_id, staff_id))
    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": staff_id, "username": "staff", "full_name": "Staff Tech", "role": "staff"}

    yield {
        "conn": conn,
        "today_str": today_str
    }

    app.dependency_overrides.clear()
    conn.close()

def test_periodic_report_aggregates_tracked_findings(reports_db):
    res = client.get(f"/api/reports?period_type=Day&reference_date={reports_db['today_str']}")
    assert res.status_code == 200
    data = res.json()
    assert data["grand_total_done"] == 65 # 20 + 15 + 30
    assert data["grand_total_positive"] == 11 # 3 + 8 (untracked ESR positive ignored)
    
    sec1 = next(s for s in data["sections"] if s["section_name"] == "Hematology")
    assert sec1["section_total_done"] == 35
    assert sec1["section_total_positive"] == 3

    cbc_row = next(t for t in sec1["tests"] if t["test_name"] == "CBC")
    assert cbc_row["done"] == 20
    assert cbc_row["positive"] == 3
    assert cbc_row["positivity_rate"] == 15.0 # (3/20)*100

    esr_row = next(t for t in sec1["tests"] if t["test_name"] == "E.S.R")
    assert esr_row["done"] == 15
    assert esr_row["positive"] is None
    assert esr_row["positivity_rate"] is None
