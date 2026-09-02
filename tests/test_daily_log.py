import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user, require_admin

client = TestClient(app)

@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    cur = conn.cursor()
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Hematology', 1)")
    sec_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('CBC', ?, 1, 1)", (sec_id,))
    cbc_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('Malaria RDT', ?, 1, 1)", (sec_id,))
    malaria_id = cur.lastrowid
    
    # Insert client & visit
    cur.execute("INSERT INTO clients (client_number, full_name, sex) VALUES ('CLI-001', 'Test Client', 'Male')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin, order_category, created_at) VALUES (?, 'Ward 1', 'in-house', '2026-07-25 09:00:00')", (client_id,))
    visit_id = cur.lastrowid
    
    # Completed live orders for Malaria RDT
    cur.execute("""
        INSERT INTO test_orders (visit_id, test_id, status, order_category, ordered_at)
        VALUES (?, ?, 'completed', 'in-house', '2026-07-25 09:15:00')
    """, (visit_id, malaria_id))
    order_id = cur.lastrowid
    
    # Add positive result for order
    cur.execute("""
        INSERT INTO test_results (order_id, is_positive, clinical_flag, entered_at)
        VALUES (?, 1, 'Abnormal', '2026-07-25 09:30:00')
    """, (order_id,))
    
    conn.commit()

    def override_get_db():
        yield conn

    user = {"id": 1, "username": "admin", "full_name": "Admin User", "role": "admin"}
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user

    yield {
        "conn": conn,
        "sec_id": sec_id,
        "cbc_id": cbc_id,
        "malaria_id": malaria_id
    }

    app.dependency_overrides.clear()
    conn.close()

def test_daily_log_aggregates_live_orders_and_backlog(mock_db):
    date_str = "2026-07-25"
    malaria_id = mock_db["malaria_id"]
    cbc_id = mock_db["cbc_id"]

    # 1. Before backlog: Daily Log should have 1 Malaria RDT done (1 positive from live order) and 0 CBC done
    res1 = client.get(f"/api/daily-log?date={date_str}")
    assert res1.status_code == 200
    d1 = res1.json()
    
    t_malaria = next(t for sec in d1["sections"] for t in sec["tests"] if t["test_id"] == malaria_id)
    assert t_malaria["done"] == 1
    assert t_malaria["positive"] == 1
    
    t_cbc = next(t for sec in d1["sections"] for t in sec["tests"] if t["test_id"] == cbc_id)
    assert t_cbc["done"] == 0

    # 2. Add manual backlog entries: 10 Malaria RDT (3 positive) and 5 CBC (1 positive)
    b_res = client.post("/api/backlog", json={
        "entry_date": date_str,
        "entries": [
            {
                "test_id": malaria_id,
                "done": 10,
                "positive": 3,
                "in_house": 8,
                "referral": 2,
                "outreach": 0,
                "self_request": 0
            },
            {
                "test_id": cbc_id,
                "done": 5,
                "positive": 1,
                "in_house": 5,
                "referral": 0,
                "outreach": 0,
                "self_request": 0
            }
        ]
    })
    assert b_res.status_code == 200

    # 3. Check Daily Log combines Live + Backlog:
    # Malaria RDT: 1 live + 10 backlog = 11 done; 1 live positive + 3 backlog positive = 4 positive
    # CBC: 0 live + 5 backlog = 5 done; 0 live positive + 1 backlog positive = 1 positive
    res2 = client.get(f"/api/daily-log?date={date_str}")
    assert res2.status_code == 200
    d2 = res2.json()
    
    t_malaria_after = next(t for sec in d2["sections"] for t in sec["tests"] if t["test_id"] == malaria_id)
    assert t_malaria_after["done"] == 11
    assert t_malaria_after["positive"] == 4
    
    t_cbc_after = next(t for sec in d2["sections"] for t in sec["tests"] if t["test_id"] == cbc_id)
    assert t_cbc_after["done"] == 5
    assert t_cbc_after["positive"] == 1

    # Overall today_check
    assert d2["today_check"]["total_done"] == 16
    assert d2["today_check"]["total_positive"] == 5
