import datetime
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SCHEMA_SQL, _ensure_transfusion_schema
from backend.app.auth import get_current_user
from backend.app.pdf_generator import generate_pdf, generate_blood_bag_label

client = TestClient(app)

@pytest.fixture
def transfusion_e2e_setup():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    _ensure_transfusion_schema(conn)

    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO clinicians (name) VALUES ('DR. MUGISHA')")
    cur.execute("INSERT INTO specimen_types (name, is_active) VALUES ('Whole Blood (EDTA)', 1)")
    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Blood Transfusion & Immunohematology', 1)")
    sec_id = cur.lastrowid

    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked, result_type) VALUES ('Blood group (ABO & Rh typing)', ?, 1, 0, 'options')", (sec_id,))
    bg_test_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked, result_type) VALUES ('Compatibility Testing (Cross-matching)', ?, 1, 1, 'options')", (sec_id,))
    cm_test_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked, result_type) VALUES ('Direct coombs (Direct Antiglobulin Test)', ?, 1, 0, 'options')", (sec_id,))
    dat_test_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked, result_type) VALUES ('Indirect coombs (Antibody Screen)', ?, 1, 0, 'options')", (sec_id,))
    iat_test_id = cur.lastrowid

    # Client
    cur.execute("INSERT INTO clients (client_number, full_name, date_of_birth, sex) VALUES ('AMH-C26-0812', 'OKELLO PATRICK', '1992-04-15', 'Male')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, lab_number, ward_of_origin) VALUES (?, 'MLIS-26-09-0812', 'SURGICAL WARD')", (client_id,))
    visit_id = cur.lastrowid

    conn.commit()
    _ensure_transfusion_schema(conn)

    app.dependency_overrides[get_db] = lambda: conn
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin_tech", "full_name": "Senior Lab Technologist", "role": "admin"}

    yield {
        "conn": conn,
        "client_id": client_id,
        "visit_id": visit_id,
        "bg_test_id": bg_test_id,
        "cm_test_id": cm_test_id,
        "dat_test_id": dat_test_id,
        "iat_test_id": iat_test_id
    }

    app.dependency_overrides.clear()
    conn.close()

def test_full_blood_transfusion_workflow(transfusion_e2e_setup):
    setup = transfusion_e2e_setup
    conn = setup["conn"]
    cur = conn.cursor()

    # 1. Order and enter Blood Grouping: A Rh(D) Positive
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (setup["visit_id"], setup["bg_test_id"]))
    bg_order_id = cur.lastrowid
    conn.commit()

    # Query seeded parameters
    cur.execute("SELECT id, parameter_name FROM test_parameters WHERE test_id = ?", (setup["bg_test_id"],))
    bg_params = {r["parameter_name"]: r["id"] for r in cur.fetchall()}

    # Submit concordant Group A Rh(D) Positive
    bg_res = client.post("/api/clients/results", json={
        "order_id": bg_order_id,
        "parameter_results": [
            {"parameter_id": bg_params["Forward Anti-A"], "result_value": "Agglutination (+)"},
            {"parameter_id": bg_params["Forward Anti-B"], "result_value": "No Agglutination (-)"},
            {"parameter_id": bg_params["Forward Anti-D"], "result_value": "Agglutination (+)"},
            {"parameter_id": bg_params["Reverse A1-cells"], "result_value": "No Agglutination (-)"},
            {"parameter_id": bg_params["Reverse B-cells"], "result_value": "Agglutination (+)"}
        ]
    })
    assert bg_res.status_code == 200

    # 2. Order Cross-matching
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (setup["visit_id"], setup["cm_test_id"]))
    cm_order_id = cur.lastrowid
    conn.commit()

    future_exp = (datetime.date.today() + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
    past_exp = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%Y-%m-%d")

    # 2a. Attempt biological incompatibility: Client is A Pos, Donor is B Pos
    bio_fail = client.post(f"/api/clients/orders/{cm_order_id}/crossmatch", json={
        "donor_unit_id": "UG-BTS-2026-INCOMP-1",
        "donor_blood_group": "B Rh(D) Positive",
        "product_type": "Packed Red Blood Cells (PRBC)",
        "expiry_date": future_exp,
        "phase_is": "Negative",
        "phase_thermophase": "Negative",
        "phase_ahg": "Negative"
    })
    assert bio_fail.status_code == 400
    assert "ABSOLUTE SAFETY BLOCK" in bio_fail.json()["detail"]

    # 2b. Attempt expired unit
    exp_fail = client.post(f"/api/clients/orders/{cm_order_id}/crossmatch", json={
        "donor_unit_id": "UG-BTS-2026-EXP-1",
        "donor_blood_group": "A Rh(D) Positive",
        "product_type": "Packed Red Blood Cells (PRBC)",
        "expiry_date": past_exp,
        "phase_is": "Negative",
        "phase_thermophase": "Negative",
        "phase_ahg": "Negative"
    })
    assert exp_fail.status_code == 400
    assert "EXPIRED" in exp_fail.json()["detail"]

    # 2c. Record serologically incompatible unit (AHG agglutination 2+)
    incompat_res = client.post(f"/api/clients/orders/{cm_order_id}/crossmatch", json={
        "donor_unit_id": "UG-BTS-2026-INCOMP-AHG",
        "donor_blood_group": "A Rh(D) Positive",
        "product_type": "Packed Red Blood Cells (PRBC)",
        "expiry_date": future_exp,
        "phase_is": "Negative",
        "phase_thermophase": "Negative",
        "phase_ahg": "2+"
    })
    assert incompat_res.status_code == 200
    inc_data = incompat_res.json()
    assert inc_data["compatibility_status"] == "INCOMPATIBLE"
    assert inc_data["release_status"] == "UNSAFE FOR TRANSFUSION"
    assert inc_data["is_locked"] == 1

    # Attempt to print label for incompatible unit -> should be forbidden
    inc_label_res = client.get(f"/api/reports/crossmatch/{inc_data['id']}/bag-label")
    assert inc_label_res.status_code == 400

    # 2d. Record fully compatible unit: O Rh(D) Positive PRBC
    compat_res = client.post(f"/api/clients/orders/{cm_order_id}/crossmatch", json={
        "donor_unit_id": "UG-BTS-2026-COMPAT-99",
        "donor_blood_group": "O Rh(D) Positive",
        "product_type": "Packed Red Blood Cells (PRBC)",
        "expiry_date": future_exp,
        "phase_is": "Negative",
        "phase_thermophase": "Negative",
        "phase_ahg": "Negative"
    })
    assert compat_res.status_code == 200
    comp_data = compat_res.json()
    assert comp_data["compatibility_status"] == "COMPATIBLE"
    assert comp_data["release_status"] == "RELEASED FOR INFUSION"

    # Download blood bag label for compatible unit
    lbl_res = client.get(f"/api/reports/crossmatch/{comp_data['id']}/bag-label")
    assert lbl_res.status_code == 200
    assert lbl_res.headers["content-type"] == "application/pdf"
    assert len(lbl_res.content) > 500

    # 3. Generate Full Visit Lab PDF Report
    pdf_res = client.get(f"/api/reports/visit/{setup['visit_id']}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000
