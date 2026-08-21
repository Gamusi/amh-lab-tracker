import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import get_current_user
from backend.app.database import get_db, SCHEMA_SQL
import sqlite3

client = TestClient(app)

RAW_NIHON_SAMPLE = """[host] [Send] MEK-7222     2201024CLOSED      CBC + Diff  01BLOOD           01  0002413   V03-02  V04-02  V03-01  015361       20260817     145705102             4.1  30.4* 55.3* 10.0*  2.7*  1.6*  1.3*  2.3*  0.4*  0.1*  0.1* 6.92H 16.9  52.7H 76.2L 24.4L 32.1  12.9   175  0.13L  7.6  17.6H"""

def test_parse_analyzer_output_endpoint():
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "labtech1", "role": "staff"}
    res = client.post("/api/integrations/parse-analyzer-output", json={
        "analyzer_type": "nihon_kohden",
        "raw_text": RAW_NIHON_SAMPLE
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["sample_id"] == "0002413"
    assert len(data["parameters"]) == 22
    app.dependency_overrides.clear()

def test_parse_analyzer_output_invalid():
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "labtech1", "role": "staff"}
    res = client.post("/api/integrations/parse-analyzer-output", json={
        "analyzer_type": "nihon_kohden",
        "raw_text": "invalid payload text"
    })
    assert res.status_code == 400
    assert "detail" in res.json()
    app.dependency_overrides.clear()
