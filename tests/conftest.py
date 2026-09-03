import pytest
import sqlite3
from backend.app.database import SCHEMA_SQL, init_db, get_connection

@pytest.fixture
def db_connection():
    """Provides an in-memory SQLite database initialized with SCHEMA_SQL."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_SQL)
    
    # Pre-seed SELF REQUEST
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clinicians WHERE name = 'SELF REQUEST'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO clinicians (name) VALUES ('SELF REQUEST')")
    conn.commit()
    
    yield conn
    conn.close()

from backend.app.main import app
from backend.app.database import get_db
from backend.app.auth import get_current_user

@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO clinicians (name) VALUES ('SELF REQUEST')")
    cur.execute("INSERT INTO specimen_types (name, is_active) VALUES ('Whole Blood (EDTA)', 1)")
    specimen_id = cur.lastrowid

    cur.execute("INSERT INTO sections (name, sort_order) VALUES ('Hematology', 1)")
    sec_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('CBC', ?, 1, 1)", (sec_id,))
    cbc_id = cur.lastrowid
    cur.execute("INSERT INTO tests (name, section_id, is_active, is_tracked) VALUES ('BS for MPS', ?, 1, 1)", (sec_id,))
    mps_id = cur.lastrowid
    
    cur.execute("INSERT INTO test_parameters (test_id, parameter_name, unit, ref_range, sort_order) VALUES (?, 'WBC', 'x10^9/L', '4.0-10.0', 1)", (cbc_id,))
    wbc_param_id = cur.lastrowid
    cur.execute("INSERT INTO test_parameters (test_id, parameter_name, unit, ref_range, sort_order) VALUES (?, 'Hemoglobin', 'g/dL', '12.0-16.0', 2)", (cbc_id,))
    hb_param_id = cur.lastrowid
    
    conn.commit()
    
    def override_get_db():
        yield conn
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "labtech1", "full_name": "Lab Technician", "role": "admin"}
    
    yield {
        "conn": conn,
        "section_id": sec_id,
        "specimen_id": specimen_id,
        "cbc_id": cbc_id,
        "mps_id": mps_id,
        "wbc_param_id": wbc_param_id,
        "hb_param_id": hb_param_id
    }
    
    app.dependency_overrides.clear()
    conn.close()

