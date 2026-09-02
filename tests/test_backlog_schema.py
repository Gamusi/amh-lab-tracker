import sqlite3
import pytest
from backend.app.database import get_connection

def test_daily_entries_has_category_columns():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(daily_entries)")
    cols = [r[1] for r in cur.fetchall()]
    conn.close()
    
    assert "in_house" in cols
    assert "referral" in cols
    assert "outreach" in cols
    assert "self_request" in cols
