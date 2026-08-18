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
