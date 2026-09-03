import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_cs_multi_phase_workflow_api(mock_db):
    conn = mock_db["conn"]
    cur = conn.cursor()
    cur.execute("INSERT INTO tests (name, section_id, is_tracked, result_type) VALUES ('Urine Culture & Sensitivity (C&S)', 1, 1, 'culture_panel')")
    test_id = cur.lastrowid
    cur.execute("INSERT INTO clients (client_number, full_name, sex, date_of_birth) VALUES ('AMH-CS-01', 'John Doe', 'Male', '1990-01-01')")
    client_id = cur.lastrowid
    cur.execute("INSERT INTO clinicians (name) VALUES ('DR. OPWANYA')")
    clin_id = cur.lastrowid
    cur.execute("INSERT INTO visits (client_id, clinician_id, ward_of_origin, lab_number) VALUES (?, ?, 'OPD', 'AMH-26-9-001')", (client_id, clin_id))
    visit_id = cur.lastrowid
    cur.execute("INSERT INTO test_orders (visit_id, test_id, status) VALUES (?, ?, 'pending')", (visit_id, test_id))
    order_id = cur.lastrowid
    conn.commit()

    # 1. Save Phase 1: Preliminary Micro
    p1_payload = {
        "phase": 1,
        "preliminary_micro": "Moderate pus cells, Gram-negative rods seen",
        "is_emergency_callback_done": True,
        "emergency_callback_recipient": "Dr. Opwanya via phone"
    }
    r1 = client.post(f"/api/culture/order/{order_id}/save", json=p1_payload)
    assert r1.status_code == 200

    # 2. Save Phase 2 & 3: Colony Count & Organism Identification with AST
    p2_payload = {
        "phase": 4,
        "preliminary_micro": "Moderate pus cells, Gram-negative rods seen",
        "colony_count_cfu": ">= 10^5",
        "growth_category": "significant",
        "incubation_hours": 24,
        "media_used": "CLED & MacConkey Agar",
        "isolates": [
            {
                "isolate_number": 1,
                "organism_name": "Escherichia coli",
                "colony_morphology": "Yellow lactose-fermenting colonies on CLED, pink on MacConkey",
                "is_pathogen": True,
                "ast_results": [
                    {"antimicrobial_class": "Penicillins", "agent_name": "Ampicillin", "measurement_type": "zone_mm", "measurement_value": 12.0, "raw_sir": "R"},
                    {"antimicrobial_class": "Beta-Lactam/Inh.", "agent_name": "Amoxicillin/Clavulanate", "measurement_type": "zone_mm", "measurement_value": 19.0, "raw_sir": "S"},
                    {"antimicrobial_class": "Cephalosporins", "agent_name": "Ceftriaxone", "measurement_type": "zone_mm", "measurement_value": 16.0, "raw_sir": "I"},
                    {"antimicrobial_class": "Fluoroquinolones", "agent_name": "Ciprofloxacin", "measurement_type": "zone_mm", "measurement_value": 22.0, "raw_sir": "S"},
                    {"antimicrobial_class": "Aminoglycosides", "agent_name": "Gentamicin", "measurement_type": "zone_mm", "measurement_value": 10.0, "raw_sir": "R"}
                ]
            }
        ],
        "is_esbl_positive": False
    }
    r2 = client.post(f"/api/culture/order/{order_id}/save", json=p2_payload)
    assert r2.status_code == 200

    # 3. Retrieve C&S details
    get_res = client.get(f"/api/culture/order/{order_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["phase"] == 4
    assert len(data["isolates"]) == 1
    assert data["isolates"][0]["organism_name"] == "Escherichia coli"
    assert len(data["isolates"][0]["ast_results"]) == 5
