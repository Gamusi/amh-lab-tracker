import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import get_current_user
from backend.app.database import get_db, SCHEMA_SQL
import sqlite3

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    # Seed user, client, section, test, visit, orders
    conn.execute("INSERT INTO users (id, username, full_name, password_hash, role) VALUES (1, 'admin_user', 'Admin User', 'hash', 'admin')")
    conn.execute("INSERT INTO users (id, username, full_name, password_hash, role) VALUES (2, 'staff_user', 'Staff User', 'hash', 'staff')")
    conn.execute("INSERT INTO clients (id, client_number, full_name, age_category, sex) VALUES (1, 'JD-001', 'John Doe', 'Adult', 'Male')")
    conn.execute("INSERT INTO sections (id, name) VALUES (1, 'Hematology')")
    conn.execute("INSERT INTO tests (id, section_id, name, result_type) VALUES (1, 1, 'CBC', 'panel')")
    conn.execute("INSERT INTO tests (id, section_id, name, result_type) VALUES (2, 1, 'ESR', 'numeric')")
    
    # Visit 1
    conn.execute("INSERT INTO visits (id, client_id, ward_of_origin, is_deleted) VALUES (1, 1, 'OPD', 0)")
    conn.execute("INSERT INTO test_orders (id, visit_id, test_id, status) VALUES (1, 1, 1, 'pending')")
    conn.execute("INSERT INTO test_orders (id, visit_id, test_id, status) VALUES (2, 1, 2, 'pending')")
    
    # Visit 2
    conn.execute("INSERT INTO visits (id, client_id, ward_of_origin, is_deleted) VALUES (2, 1, 'IPD', 0)")
    conn.execute("INSERT INTO test_orders (id, visit_id, test_id, status) VALUES (3, 2, 1, 'completed')")
    conn.execute("INSERT INTO test_results (id, order_id, result_value) VALUES (1, 3, '12.5')")
    
    # Visit 3
    conn.execute("INSERT INTO visits (id, client_id, ward_of_origin, is_deleted) VALUES (3, 1, 'Maternity', 0)")
    conn.execute("INSERT INTO test_orders (id, visit_id, test_id, status) VALUES (4, 3, 2, 'pending')")

    conn.commit()

    def override_get_db():
        try:
            yield conn
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    conn.close()


def test_bulk_delete_orders_success():
    app.dependency_overrides[get_current_user] = lambda: {"id": 2, "username": "staff_user", "role": "staff"}
    res = client.request("DELETE", "/api/orders/bulk", json={"order_ids": [1, 2]})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "deleted"
    assert set(data["deleted_order_ids"]) == {1, 2}
    assert data["skipped_order_ids"] == []


def test_bulk_delete_orders_partial_skips_non_pending_and_missing():
    app.dependency_overrides[get_current_user] = lambda: {"id": 2, "username": "staff_user", "role": "staff"}
    # Order 1 is pending, Order 3 is completed, Order 99 does not exist
    res = client.request("DELETE", "/api/orders/bulk", json={"order_ids": [1, 3, 99]})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "deleted"
    assert data["deleted_order_ids"] == [1]
    assert set(data["skipped_order_ids"]) == {3, 99}


def test_bulk_delete_visits_admin_success():
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin_user", "role": "admin"}
    res = client.request("DELETE", "/api/visits/bulk", json={"visit_ids": [1, 2]})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "deleted"
    assert set(data["deleted_visit_ids"]) == {1, 2}
    assert data["skipped_visit_ids"] == []


def test_bulk_delete_visits_non_admin_forbidden():
    app.dependency_overrides[get_current_user] = lambda: {"id": 2, "username": "staff_user", "role": "staff"}
    res = client.request("DELETE", "/api/visits/bulk", json={"visit_ids": [1, 2]})
    assert res.status_code == 403
    assert "Only admins" in res.json()["detail"]


def test_bulk_delete_visits_partial_missing_or_already_deleted():
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin_user", "role": "admin"}
    # Visit 3 exists, Visit 99 does not
    res = client.request("DELETE", "/api/visits/bulk", json={"visit_ids": [3, 99]})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "deleted"
    assert data["deleted_visit_ids"] == [3]
    assert data["skipped_visit_ids"] == [99]
