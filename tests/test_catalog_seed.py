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
