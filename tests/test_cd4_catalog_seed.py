import sqlite3
import pytest
from backend.app.database import init_db, get_connection
from backend.app.seed import seed_database
from backend.app.specimen_validator import validate_specimen_for_test

def test_cd4_catalog_and_reference_ranges():
    conn = get_connection()
    init_db()
    seed_database()
    cur = conn.cursor()

    # Verify quantitative CD4 test exists
    cur.execute("SELECT id, name, result_type, default_unit, is_tracked, tracks_stock, consumable_name FROM tests WHERE name = 'Absolute CD4 Count (Cytometry)'")
    quant_row = cur.fetchone()
    assert quant_row is not None
    assert quant_row[2] == 'quantitative'
    assert quant_row[3] == 'cells/µL'
    assert quant_row[4] == 1
    assert quant_row[5] == 1
    assert "PIMA" in quant_row[6]

    # Verify RDT CD4 test exists
    cur.execute("SELECT id, name, result_type, default_unit, ref_range, options, is_tracked, tracks_stock, consumable_name FROM tests WHERE name = 'CD4 Count (Rapid Test Strip)'")
    rdt_row = cur.fetchone()
    assert rdt_row is not None
    assert rdt_row[2] == 'options'
    assert rdt_row[3] is None
    assert rdt_row[4] is None
    import json
    opts = json.loads(rdt_row[5])
    assert 'CD4 Count: Below 200 cells/µL' in opts
    assert 'CD4 Count: 200 cells/µL or above' in opts
    assert 'Invalid' in opts
    assert rdt_row[6] == 1
    assert rdt_row[7] == 1
    assert "VISITECT" in rdt_row[8]

    # Verify reference ranges
    cur.execute("SELECT normal_min, normal_max, critical_min, sanity_max, unit FROM reference_ranges WHERE parameter_name = 'Absolute CD4 Count (Cytometry)'")
    ref_row = cur.fetchone()
    assert ref_row is not None
    assert ref_row[0] == 500.0
    assert ref_row[1] == 1500.0
    assert ref_row[2] == 200.0
    assert ref_row[3] == 5000.0
    assert ref_row[4] == 'cells/µL'

    # Verify specimen acceptance
    assert validate_specimen_for_test("Absolute CD4 Count (Cytometry)", "EDTA Whole Blood") is True
    assert validate_specimen_for_test("Absolute CD4 Count (Cytometry)", "Capillary / Fingerstick Blood") is True
    assert validate_specimen_for_test("Absolute CD4 Count (Cytometry)", "Clean-Catch Midstream Urine") is False
    assert validate_specimen_for_test("CD4 Count (Rapid Test Strip)", "EDTA Whole Blood") is True
    assert validate_specimen_for_test("CD4 Count (Rapid Test Strip)", "Capillary / Fingerstick Blood") is True
    conn.close()
