import pytest
import sqlite3
from backend.app.database import SCHEMA_SQL
from backend.app.seed import TESTS, SECTIONS, seed_database
from backend.app.database import get_connection, init_db

def test_qualitative_and_semi_qualitative_tests_tracking_configuration():
    # Verify seed definitions in TESTS dictionary
    for t in TESTS:
        if t.get("parent_name"):
            continue
        name = t["name"]
        res_type = t["result_type"]
        is_tracked = bool(t["is_tracked"])
        
        # Binary / Infectious assays must be tracked
        if name in ("Malaria RDT", "HBsAg (Hepatitis B)", "HIV (MoH Three-Test Algorithm)", "TB LAM (Urine Tuberculosis LAM)", "COVID19RDT", "CrAg (Cryptococcal Antigen)", "HCV Ab (Hepatitis C)", "TPHA (Confirmatory Syphilis Test)"):
            assert is_tracked is True, f"{name} must be tracked"
            assert res_type in ("qualitative", "options", "panel")

        # Standard biochemistry panels must be untracked by default
        if name in ("LFTS", "RFTS", "CARDIAC", "ELECTROLYTES"):
            assert is_tracked is False, f"Panel {name} must be untracked by default"

        # Surveillance glucometry and composite panels must be tracked
        if name in ("CBC", "URINALYSIS", "STOOL ANALYSIS", "FBS (Fasting Blood Sugar)", "RBS (Random Blood Sugar)"):
            assert is_tracked is True, f"{name} must be tracked"


def test_urinalysis_seed_subparameters():
    from backend.app.seed import PANELS
    ua_children = [t for t in TESTS if t.get("parent_name") == "URINALYSIS"]
    assert len(ua_children) == 17
    assert len(PANELS["URINALYSIS"]) == 17

    # Check Macroscopy (sort_order 1-2)
    macro = [t for t in ua_children if t["sort_order"] in (1, 2)]
    assert len(macro) == 2
    assert {t["name"] for t in macro} == {"Color", "Turbidity"}

    # Check Microscopy (sort_order 3-7)
    micro = [t for t in ua_children if 3 <= t["sort_order"] <= 7]
    assert len(micro) == 5
    assert {t["name"] for t in micro} == {
        "Pus Cells (WBCs)", "Red Blood Cells (RBCs)", "Epithelial Cells", "Casts", "Crystals"
    }
    for t in micro:
        assert "Not Seen" in t["options"]

    # Check Dipstick (sort_order 8-17)
    dip = [t for t in ua_children if 8 <= t["sort_order"] <= 17]
    assert len(dip) == 10
    dip_names = {t["name"] for t in dip}
    assert "Specific Gravity (S.G)" in dip_names
    assert "PH" in dip_names
    assert "Proteins (Albuminuria Screening)" in dip_names
    assert "Glucose (Glucosuria Screening)" in dip_names

