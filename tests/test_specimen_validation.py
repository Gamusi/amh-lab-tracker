import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_connection, init_db
from backend.app.seed import seed_database
from backend.app.specimen_validator import (
    get_compatible_specimens_for_test,
    validate_test_specimen_selection,
    SPECIMEN_EDTA,
    SPECIMEN_CITRATE,
    SPECIMEN_URINE,
    SPECIMEN_STOOL,
    SPECIMEN_SPUTUM,
    SPECIMEN_SERUM_RED,
    SPECIMEN_PLASMA_FLUORIDE
)

client = TestClient(app)

from backend.app.database import get_db, SCHEMA_SQL
from backend.app.auth import get_current_user
from backend.app.seed import seed_database

client = TestClient(app)

@pytest.fixture
def test_app():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    seed_database(conn=conn)
    
    def override_get_db():
        yield conn
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin", "full_name": "Lab Admin", "role": "admin"}
    
    yield {"conn": conn, "client": client}
    
    app.dependency_overrides.clear()
    conn.close()

def test_compatible_specimens_catalog_matching():
    # CBC strictly EDTA
    assert get_compatible_specimens_for_test("Complete Blood Count (CBC)") == [SPECIMEN_EDTA]
    assert get_compatible_specimens_for_test("CBC") == [SPECIMEN_EDTA]

    # Coagulation profile strictly Sodium Citrate
    assert get_compatible_specimens_for_test("Prothrombin Time (PT/INR)") == [SPECIMEN_CITRATE]

    # Urinalysis strictly Clean-Catch Urine
    assert get_compatible_specimens_for_test("URINALYSIS") == [SPECIMEN_URINE]
    assert get_compatible_specimens_for_test("HCG (Urine)") == [SPECIMEN_URINE]

    # Stool strictly Random Stool / Feces
    assert get_compatible_specimens_for_test("STOOL ANALYSIS") == [SPECIMEN_STOOL]
    assert get_compatible_specimens_for_test("H.pylori Ag (Stool)") == [SPECIMEN_STOOL]

    # Sputum for TB
    assert SPECIMEN_SPUTUM in get_compatible_specimens_for_test("ZN Staining For AFBs")

    # Biochemistry
    assert SPECIMEN_SERUM_RED in get_compatible_specimens_for_test("Liver Function Tests (LFTs)")
    assert SPECIMEN_PLASMA_FLUORIDE in get_compatible_specimens_for_test("FBS (Fasting Blood Sugar)")


def test_specimen_selection_validator():
    tests = [
        {"name": "Complete Blood Count (CBC)", "section": "Hematology"},
        {"name": "URINALYSIS", "section": "Urinalysis Profile"}
    ]

    # Fails if only EDTA provided (missing urine)
    valid, errors, mapping = validate_test_specimen_selection(tests, [SPECIMEN_EDTA])
    assert not valid
    assert len(errors) == 1
    assert "URINALYSIS" in errors[0]

    # Succeeds if both EDTA and Urine provided
    valid, errors, mapping = validate_test_specimen_selection(tests, [SPECIMEN_EDTA, SPECIMEN_URINE])
    assert valid
    assert len(errors) == 0
    assert mapping["Complete Blood Count (CBC)"] == SPECIMEN_EDTA
    assert mapping["URINALYSIS"] == SPECIMEN_URINE


def test_api_specimen_validation_endpoint(test_app):
    c = test_app["client"]
    # Retrieve specimen IDs and test IDs
    r_tests = c.get("/api/config/tests")
    assert r_tests.status_code == 200
    tests_data = r_tests.json()
    cbc = next(t for t in tests_data if "CBC" in t["name"] or "Complete Blood Count" in t["name"])
    
    r_specs = c.get("/api/config/specimens")
    assert r_specs.status_code == 200
    specs_data = r_specs.json()
    edta_spec = next(s for s in specs_data if "EDTA" in s["name"])
    urine_spec = next(s for s in specs_data if "Urine" in s["name"])

    # Valid: CBC with EDTA
    res_valid = c.post("/api/config/specimens/validate", json={
        "test_ids": [cbc["id"]],
        "specimen_type_ids": [edta_spec["id"]]
    })
    assert res_valid.status_code == 200
    assert res_valid.json()["is_valid"] is True

    # Invalid: CBC with Urine
    res_invalid = c.post("/api/config/specimens/validate", json={
        "test_ids": [cbc["id"]],
        "specimen_type_ids": [urine_spec["id"]]
    })
    assert res_invalid.status_code == 200
    assert res_invalid.json()["is_valid"] is False
    assert len(res_invalid.json()["errors"]) > 0


def test_create_multi_specimen_visit(test_app):
    c = test_app["client"]
    # Create client
    c_res = c.post("/api/clients", json={
        "full_name": "TEST SPECIMEN CLIENT",
        "age_string": "30y",
        "age_category": "Adult",
        "sex": "Female",
        "phone": "0700000001"
    })
    assert c_res.status_code == 200
    client_id = c_res.json()["client_id"]

    # Get or create clinician
    clin_res = c.get("/api/config/clinicians")
    if clin_res.status_code == 200 and clin_res.json():
        clin_id = clin_res.json()[0]["id"]
    else:
        new_clin = c.post("/api/config/clinicians", json={"name": "Dr. Test Clinician", "is_active": True})
        clin_id = new_clin.json()["id"]

    # Get CBC and Urinalysis
    r_tests = c.get("/api/config/tests")
    tests_data = r_tests.json()
    cbc = next(t for t in tests_data if "CBC" in t["name"] or "Complete Blood Count" in t["name"])
    ua = next(t for t in tests_data if "URINALYSIS" in t["name"] or "Urinalysis" in t["name"])

    r_specs = c.get("/api/config/specimens")
    specs_data = r_specs.json()
    edta_spec = next(s for s in specs_data if "EDTA" in s["name"])
    urine_spec = next(s for s in specs_data if "Urine" in s["name"])

    # Attempt create visit with mismatch specimen (only Urine for CBC + UA) -> must fail
    fail_res = c.post("/api/visits", json={
        "client_id": client_id,
        "clinician_id": clin_id,
        "ward_of_origin": "OPD",
        "specimen_type_ids": [urine_spec["id"]],
        "test_ids": [cbc["id"], ua["id"]],
        "order_category": "in-house"
    })
    assert fail_res.status_code == 400
    assert "Specimen" in fail_res.json()["detail"]

    # Create visit with valid multi-specimens: [EDTA, Urine]
    ok_res = c.post("/api/visits", json={
        "client_id": client_id,
        "clinician_id": clin_id,
        "ward_of_origin": "OPD",
        "specimen_type_ids": [edta_spec["id"], urine_spec["id"]],
        "test_ids": [cbc["id"], ua["id"]],
        "order_category": "in-house"
    })
    assert ok_res.status_code == 200
    visit_id = ok_res.json()["visit_id"]

    # Verify orders in DB received their respective specimen IDs
    conn = test_app["conn"]
    cur = conn.cursor()
    cur.execute("SELECT test_id, specimen_type_id FROM test_orders WHERE visit_id = ?", (visit_id,))
    orders = cur.fetchall()
    assert len(orders) == 2
    for o in orders:
        if o["test_id"] == cbc["id"]:
            assert o["specimen_type_id"] == edta_spec["id"]
        elif o["test_id"] == ua["id"]:
            assert o["specimen_type_id"] == urine_spec["id"]


def test_serum_tests_reject_whole_blood(test_app):
    c = test_app["client"]
    # Create client
    c_res = c.post("/api/clients", json={
        "full_name": "BIOCHEM SPECIMEN CLIENT",
        "age_string": "45y",
        "age_category": "Adult",
        "sex": "Male",
        "phone": "0700000002"
    })
    assert c_res.status_code == 200
    client_id = c_res.json()["client_id"]

    clin_res = c.get("/api/config/clinicians")
    if clin_res.status_code == 200 and clin_res.json():
        clin_id = clin_res.json()[0]["id"]
    else:
        new_clin = c.post("/api/config/clinicians", json={"name": "Dr. Test Clinician", "is_active": True})
        clin_id = new_clin.json()["id"]

    # Get LFTs and Lipid Profile (Serum tests)
    r_tests = c.get("/api/config/tests")
    tests_data = r_tests.json()
    lft = next(t for t in tests_data if "Liver Function" in t["name"] or "LFT" in t["name"])
    
    r_specs = c.get("/api/config/specimens")
    specs_data = r_specs.json()
    edta_spec = next(s for s in specs_data if "EDTA" in s["name"])
    serum_spec = next(s for s in specs_data if "Serum" in s["name"])

    # Attempt to order LFTs with ONLY EDTA Whole Blood -> MUST FAIL
    fail_res = c.post("/api/visits", json={
        "client_id": client_id,
        "clinician_id": clin_id,
        "ward_of_origin": "OPD",
        "specimen_type_ids": [edta_spec["id"]],
        "test_ids": [lft["id"]],
        "order_category": "in-house"
    })
    assert fail_res.status_code == 400
    assert "Specimen" in fail_res.json()["detail"]

    # Order LFTs with Serum (Red Top) -> MUST SUCCEED
    ok_res = c.post("/api/visits", json={
        "client_id": client_id,
        "clinician_id": clin_id,
        "ward_of_origin": "OPD",
        "specimen_type_ids": [serum_spec["id"]],
        "test_ids": [lft["id"]],
        "order_category": "in-house"
    })
    assert ok_res.status_code == 200


def test_create_visit_with_explicit_test_orders(test_app):
    c = test_app["client"]
    c_res = c.post("/api/clients", json={
        "full_name": "PER TEST ORDER CLIENT",
        "age_string": "28y",
        "age_category": "Adult",
        "sex": "Female",
        "phone": "0700000003"
    })
    client_id = c_res.json()["client_id"]

    clin_res = c.get("/api/config/clinicians")
    if clin_res.status_code == 200 and clin_res.json():
        clin_id = clin_res.json()[0]["id"]
    else:
        new_clin = c.post("/api/config/clinicians", json={"name": "Dr. Per Test Clinician", "is_active": True})
        clin_id = new_clin.json()["id"]

    r_tests = c.get("/api/config/tests").json()
    cbc = next(t for t in r_tests if "CBC" in t["name"])
    lft = next(t for t in r_tests if "LFT" in t["name"] or "Liver" in t["name"])

    r_specs = c.get("/api/config/specimens").json()
    edta_spec = next(s for s in r_specs if "EDTA" in s["name"])
    serum_spec = next(s for s in r_specs if "Serum" in s["name"])

    # Provide explicit per-test order array
    res = c.post("/api/visits", json={
        "client_id": client_id,
        "clinician_id": clin_id,
        "ward_of_origin": "Female Ward",
        "test_orders": [
            {"test_id": cbc["id"], "specimen_type_id": edta_spec["id"]},
            {"test_id": lft["id"], "specimen_type_id": serum_spec["id"]}
        ],
        "order_category": "in-house"
    })
    assert res.status_code == 200
    visit_id = res.json()["visit_id"]

    conn = test_app["conn"]
    cur = conn.cursor()
    cur.execute("SELECT test_id, specimen_type_id FROM test_orders WHERE visit_id = ?", (visit_id,))
    orders = {r["test_id"]: r["specimen_type_id"] for r in cur.fetchall()}
    assert orders[cbc["id"]] == edta_spec["id"]
    assert orders[lft["id"]] == serum_spec["id"]
