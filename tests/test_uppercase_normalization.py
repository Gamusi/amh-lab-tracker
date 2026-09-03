import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user
import sqlite3

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)

    # Pre-seed facility settings
    conn.execute("INSERT OR IGNORE INTO facility_settings (id, facility_name, facility_acronym) VALUES (1, 'Al-shafie Medical Hospital', 'AMH')")

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin", "role": "admin"}
    yield {"conn": conn}
    app.dependency_overrides.clear()
    conn.close()


def test_create_client_converts_name_to_uppercase():
    res = client.post("/api/clients", json={
        "full_name": "john doe junior",
        "age_string": "25y",
        "age_category": "Adult",
        "sex": "Male",
        "phone": "0701234567"
    })
    assert res.status_code == 200
    data = res.json()
    client_id = data["client_id"]

    res_get = client.get(f"/api/clients/{client_id}")
    assert res_get.status_code == 200
    assert res_get.json()["full_name"] == "JOHN DOE JUNIOR"


def test_update_client_converts_name_to_uppercase():
    res = client.post("/api/clients", json={
        "full_name": "ALICE NABIRYE",
        "age_string": "30y",
        "age_category": "Adult",
        "sex": "Female"
    })
    client_id = res.json()["client_id"]

    res_put = client.put(f"/api/clients/{client_id}", json={
        "full_name": "alice nabirye mukasa"
    })
    assert res_put.status_code == 200
    assert res_put.json()["full_name"] == "ALICE NABIRYE MUKASA"


def test_create_clinician_converts_to_uppercase():
    res = client.post("/api/config/clinicians", json={"name": "dr. jane smith", "is_active": True})
    assert res.status_code == 200
    assert res.json()["name"] == "DR. JANE SMITH"


def test_create_ward_converts_to_uppercase():
    res = client.post("/api/config/wards", json={"name": "pediatric ward"})
    assert res.status_code == 200
    assert res.json()["name"] == "PEDIATRIC WARD"


def test_create_visit_converts_ward_to_uppercase(setup_test_db):
    conn = setup_test_db["conn"]
    # Seed client and clinician
    c_res = client.post("/api/clients", json={
        "full_name": "PATIENT ONE",
        "age_string": "40y",
        "age_category": "Adult",
        "sex": "Male"
    })
    cid = c_res.json()["client_id"]
    clin_res = client.post("/api/config/clinicians", json={"name": "DR. TEST", "is_active": True})
    clin_id = clin_res.json()["id"]
    
    # Seed test and specimen
    conn.execute("INSERT INTO sections (id, name) VALUES (1, 'Hematology')")
    conn.execute("INSERT INTO tests (id, section_id, name) VALUES (1, 1, 'CBC')")
    conn.execute("INSERT INTO specimen_types (id, name, is_active) VALUES (1, 'EDTA Whole Blood', 1)")
    conn.commit()

    v_res = client.post("/api/visits", json={
        "client_id": cid,
        "clinician_id": clin_id,
        "ward_of_origin": "emergency room",
        "specimen_type_id": 1,
        "test_ids": [1]
    })
    assert v_res.status_code == 200
    vid = v_res.json()["visit_id"]

    v_get = client.get(f"/api/visits/{vid}")
    assert v_get.status_code == 200
    assert v_get.json()["ward_of_origin"] == "EMERGENCY ROOM"
