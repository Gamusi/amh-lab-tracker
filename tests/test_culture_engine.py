import sqlite3
import pytest
from backend.app.database import init_db, get_connection

def test_culture_schema_tables_exist(tmp_path, monkeypatch):
    test_db = str(tmp_path / 'test_cs.db')
    monkeypatch.setenv('MLIS_DB_PATH', test_db)
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('culture_orders', 'culture_isolates', 'culture_ast_results')")
    tables = {r[0] for r in cur.fetchall()}
    assert 'culture_orders' in tables
    assert 'culture_isolates' in tables
    assert 'culture_ast_results' in tables
    conn.close()
