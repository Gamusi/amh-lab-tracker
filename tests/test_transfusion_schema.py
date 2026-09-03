import sqlite3
import pytest
from backend.app.database import get_connection

def test_donor_crossmatches_table_exists():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='donor_crossmatches'")
    assert cur.fetchone() is not None

def test_blood_group_parameters_seeded():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT tp.parameter_name 
        FROM test_parameters tp
        JOIN tests t ON tp.test_id = t.id
        WHERE LOWER(t.name) LIKE '%blood group%'
        ORDER BY tp.sort_order
    """)
    params = [r[0] for r in cur.fetchall()]
    assert "Forward Anti-A" in params
    assert "Forward Anti-B" in params
    assert "Forward Anti-D" in params
    assert "Reverse A1-cells" in params
    assert "Reverse B-cells" in params
    assert "Consolidated Blood Group" in params

def test_coombs_parameters_seeded():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT tp.parameter_name 
        FROM test_parameters tp
        JOIN tests t ON tp.test_id = t.id
        WHERE LOWER(t.name) LIKE '%direct coombs%'
        ORDER BY tp.sort_order
    """)
    dat_params = [r[0] for r in cur.fetchall()]
    assert "DAT Qualitative Status" in dat_params
    assert "Reaction Strength" in dat_params
    assert "Reagent Specificity" in dat_params
