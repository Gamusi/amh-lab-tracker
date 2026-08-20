import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user, require_admin

client = TestClient(app)

@pytest.fixture
def config_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    cur = conn.cursor()
    cur.execute("INSERT INTO users (full_name, username, password_hash, role) VALUES ('Admin User', 'admin', 'hash', 'admin')")
    admin_id = cur.lastrowid
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Serology & Clinical Immunology', 1)")
    sec_id = cur.lastrowid
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Clinical Biochemistry', 2)")
    chem_sec_id = cur.lastrowid
    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": admin_id, "username": "admin", "full_name": "Admin User", "role": "admin"}
    app.dependency_overrides[require_admin] = lambda: {"id": admin_id, "username": "admin", "full_name": "Admin User", "role": "admin"}

    yield {
        "conn": conn,
        "sec_id": sec_id,
        "chem_sec_id": chem_sec_id
    }

    app.dependency_overrides.clear()
    conn.close()

def test_create_qualitative_test_auto_tracks(config_db):
    payload = {
        "name": "Rapid Strep A",
        "section_id": config_db["sec_id"],
        "result_type": "qualitative",
        "options": "Negative, Positive",
        "sort_order": 10
    }
    res = client.post("/api/config/tests", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_tracked"] is True or data["is_tracked"] == 1

def test_create_semi_quantitative_test_auto_tracks(config_db):
    payload = {
        "name": "Rapid Microalbumin",
        "section_id": config_db["sec_id"],
        "result_type": "semi_quantitative",
        "options": "Nil, Trace, 1+, 2+",
        "sort_order": 11
    }
    res = client.post("/api/config/tests", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_tracked"] is True or data["is_tracked"] == 1

def test_create_quantitative_test_defaults_untracked(config_db):
    payload = {
        "name": "Serum Calcium",
        "section_id": config_db["chem_sec_id"],
        "result_type": "quantitative",
        "default_unit": "mmol/L",
        "sort_order": 12
    }
    res = client.post("/api/config/tests", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_tracked"] is False or data["is_tracked"] == 0

def test_create_test_with_parent_sets_parent_rollup_id(config_db):
    conn = config_db["conn"]
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tests (name, section_id, is_active, is_tracked, result_type) VALUES ('CBC', ?, 1, 1, 'panel')",
        (config_db["sec_id"],)
    )
    parent_id = cur.lastrowid
    conn.commit()

    payload = {
        "name": "Hemoglobin (Hb)",
        "section_id": config_db["sec_id"],
        "result_type": "quantitative",
        "default_unit": "g/dL",
        "sort_order": 3,
        "parent_rollup_id": parent_id
    }
    res = client.post("/api/config/tests", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["parent_rollup_id"] == parent_id
