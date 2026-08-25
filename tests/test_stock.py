import sqlite3
import datetime
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user, require_admin
from backend.app.routers.stock import deplete_kit_stock

client = TestClient(app)

@pytest.fixture
def stock_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)

    cur = conn.cursor()
    cur.execute("INSERT INTO users (full_name, username, password_hash, role) VALUES ('Admin Staff', 'admin', 'hash', 'admin')")
    admin_id = cur.lastrowid
    
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Serology & Clinical Immunology', 1)")
    sec_id = cur.lastrowid
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Urinalysis Profile', 2)")
    ua_sec_id = cur.lastrowid

    # Create Malaria RDT test
    cur.execute("""
        INSERT INTO tests (name, section_id, is_tracked, tracks_stock, consumable_name, result_type)
        VALUES ('Malaria RDT', ?, 1, 1, 'Malaria Rapid Diagnostic Test (RDT)', 'options')
    """, (sec_id,))
    malaria_id = cur.lastrowid

    # Create Urinalysis test
    cur.execute("""
        INSERT INTO tests (name, section_id, is_tracked, tracks_stock, consumable_name, result_type)
        VALUES ('URINALYSIS', ?, 1, 1, 'Siemens Multistix 10SG Reagent Strips', 'panel')
    """, (ua_sec_id,))
    ua_id = cur.lastrowid

    # Create HIV test with parameters
    cur.execute("""
        INSERT INTO tests (name, section_id, is_tracked, tracks_stock, consumable_name, result_type)
        VALUES ('HIV Testing', ?, 1, 1, 'HIV Diagnostic Kits', 'panel')
    """, (sec_id,))
    hiv_id = cur.lastrowid

    cur.execute("""
        INSERT INTO test_parameters (test_id, parameter_name, sort_order)
        VALUES (?, 'MHS HIV 1/2 Kwiq Test', 1)
    """, (hiv_id,))
    p1_id = cur.lastrowid

    cur.execute("""
        INSERT INTO test_parameters (test_id, parameter_name, sort_order)
        VALUES (?, 'HIV 1/2 Stat-Pak®', 2)
    """, (hiv_id,))
    p2_id = cur.lastrowid

    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": admin_id, "username": "admin", "full_name": "Admin Staff", "role": "admin"}
    app.dependency_overrides[require_admin] = lambda: {"id": admin_id, "username": "admin", "full_name": "Admin Staff", "role": "admin"}

    yield {
        "conn": conn,
        "admin_id": admin_id,
        "sec_id": sec_id,
        "malaria_id": malaria_id,
        "ua_id": ua_id,
        "hiv_id": hiv_id,
        "p1_id": p1_id,
        "p2_id": p2_id
    }

    app.dependency_overrides.clear()
    conn.close()


def test_generalized_stock_schema(stock_db):
    conn = stock_db["conn"]
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(diagnostic_kit_lots)")
    cols = [r["name"] for r in cur.fetchall()]
    assert "kit_name" in cols
    assert "category" in cols
    assert "current_quantity" in cols
    assert "min_threshold" in cols
    assert "expiry_date" in cols

    cur.execute("PRAGMA table_info(diagnostic_kit_transactions)")
    t_cols = [r["name"] for r in cur.fetchall()]
    assert "lot_id" in t_cols
    assert "transaction_type" in t_cols
    assert "quantity_delta" in t_cols


def test_receive_stock_lot_and_duplicate_prevention(stock_db):
    payload = {
        "kit_name": "Malaria Rapid Diagnostic Test (RDT)",
        "category": "Parasitology",
        "lot_number": "MAL-2026-01",
        "expiry_date": "2027-12-31",
        "initial_quantity": 100,
        "min_threshold": 25
    }
    res = client.post("/api/stock/receive", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "lot_id" in data

    # Attempting duplicate lot number for same kit must fail
    dup_res = client.post("/api/stock/receive", json=payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]


def test_fefo_auto_depletion_order(stock_db):
    conn = stock_db["conn"]

    # Receive Lot A expiring in 2027 (later)
    client.post("/api/stock/receive", json={
        "kit_name": "Malaria Rapid Diagnostic Test (RDT)",
        "category": "Parasitology",
        "lot_number": "LOT-LATER",
        "expiry_date": "2027-12-31",
        "initial_quantity": 50
    })

    # Receive Lot B expiring in 2026 (earlier, but unexpired)
    client.post("/api/stock/receive", json={
        "kit_name": "Malaria Rapid Diagnostic Test (RDT)",
        "category": "Parasitology",
        "lot_number": "LOT-EARLIER",
        "expiry_date": "2026-11-30",
        "initial_quantity": 30
    })

    # Deplete 1 unit - FEFO must pick LOT-EARLIER first
    res = deplete_kit_stock(conn, kit_name="Malaria Rapid Diagnostic Test (RDT)", count=1)
    assert res["lot_number"] == "LOT-EARLIER"
    assert res["current_quantity"] == 29

    # Verify database quantity
    cur = conn.cursor()
    cur.execute("SELECT current_quantity FROM diagnostic_kit_lots WHERE lot_number = 'LOT-EARLIER'")
    assert cur.fetchone()[0] == 29

    cur.execute("SELECT current_quantity FROM diagnostic_kit_lots WHERE lot_number = 'LOT-LATER'")
    assert cur.fetchone()[0] == 50


def test_expiry_lockout_safety_gate(stock_db):
    conn = stock_db["conn"]

    # Insert an expired lot
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO diagnostic_kit_lots (kit_name, category, lot_number, expiry_date, initial_quantity, current_quantity, min_threshold, is_active)
        VALUES ('Expired Test Kit', 'Serology', 'EXP-001', '2020-01-01', 50, 50, 10, 1)
    """)
    conn.commit()

    with pytest.raises(Exception) as exc_info:
        deplete_kit_stock(conn, kit_name="Expired Test Kit", count=1)
    assert "Safety Block" in str(exc_info.value)


def test_stock_adjust_and_wastage_logging(stock_db):
    res = client.post("/api/stock/receive", json={
        "kit_name": "HBsAg Rapid Test Strip",
        "category": "Serology",
        "lot_number": "HBV-001",
        "expiry_date": "2027-10-31",
        "initial_quantity": 50
    })
    lot_id = res.json()["lot_id"]

    # Log QC / Wastage deduction of 3 units
    adjust_payload = {
        "lot_id": lot_id,
        "transaction_type": "WASTAGE_QC",
        "quantity_delta": -3,
        "reason": "Weekly Internal QC Run"
    }
    adj_res = client.post("/api/stock/adjust", json=adjust_payload)
    assert adj_res.status_code == 200
    assert adj_res.json()["new_quantity"] == 47

    # Missing reason must be rejected
    bad_adj = client.post("/api/stock/adjust", json={
        "lot_id": lot_id,
        "transaction_type": "WASTAGE_QC",
        "quantity_delta": -1,
        "reason": ""
    })
    assert bad_adj.status_code == 400


def test_stock_alerts_computation(stock_db):
    today = datetime.date.today()
    near_exp = (today + datetime.timedelta(days=20)).isoformat()
    future_exp = (today + datetime.timedelta(days=300)).isoformat()

    # 1. Low stock lot (quantity 10 <= min_threshold 25)
    client.post("/api/stock/receive", json={
        "kit_name": "Low Stock Kit",
        "category": "General",
        "lot_number": "LS-01",
        "expiry_date": future_exp,
        "initial_quantity": 10,
        "min_threshold": 25
    })

    # 2. Near expiry lot
    client.post("/api/stock/receive", json={
        "kit_name": "Near Expiry Kit",
        "category": "General",
        "lot_number": "NE-01",
        "expiry_date": near_exp,
        "initial_quantity": 100,
        "min_threshold": 20
    })

    alerts_res = client.get("/api/stock/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()

    alert_types = [a["alert_type"] for a in alerts]
    assert "LOW_STOCK" in alert_types
    assert "NEAR_EXPIRY" in alert_types


def test_test_config_with_stock_tracking(stock_db):
    payload = {
        "name": "H. Pylori Stool Ag",
        "section_id": stock_db["sec_id"],
        "result_type": "qualitative",
        "options": "Negative, Positive",
        "tracks_stock": True,
        "consumable_name": "H. Pylori Stool Ag / Serum Ab Cassette"
    }
    res = client.post("/api/config/tests", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tracks_stock"] is True
    assert data["consumable_name"] == "H. Pylori Stool Ag / Serum Ab Cassette"


def test_end_to_end_result_entry_stock_depletion(stock_db):
    conn = stock_db["conn"]
    cur = conn.cursor()

    # Pre-seed stock for Malaria RDT
    client.post("/api/stock/receive", json={
        "kit_name": "Malaria Rapid Diagnostic Test (RDT)",
        "category": "Parasitology",
        "lot_number": "MAL-E2E-1",
        "expiry_date": "2027-12-31",
        "initial_quantity": 50
    })

    # Register client and visit
    cur.execute("INSERT INTO clients (client_number, full_name, age_category, sex) VALUES ('AMH-C1', 'John Doe', 'Adult', 'Male')")
    cid = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, ward_of_origin) VALUES (?, 'OPD')", (cid,))
    vid = cur.lastrowid

    # Order Malaria RDT
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (vid, stock_db["malaria_id"]))
    oid = cur.lastrowid
    conn.commit()

    # Enter Result
    res_entry = client.post("/api/results", json={
        "order_id": oid,
        "result_value": "Positive",
        "result_unit": None
    })
    assert res_entry.status_code == 200

    # Verify stock deducted by 1
    cur.execute("SELECT current_quantity FROM diagnostic_kit_lots WHERE lot_number = 'MAL-E2E-1'")
    assert cur.fetchone()[0] == 49

    # Verify transaction logged
    cur.execute("SELECT transaction_type, quantity_delta, order_id FROM diagnostic_kit_transactions WHERE order_id = ?", (oid,))
    tx = cur.fetchone()
    assert tx["transaction_type"] == "TEST_USAGE"
    assert tx["quantity_delta"] == -1


def test_stock_reconciliation_endpoint(stock_db):
    res = client.get("/api/stock/reconciliation")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
