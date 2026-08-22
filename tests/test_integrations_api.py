import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import get_current_user
from backend.app.database import get_db, SCHEMA_SQL
import sqlite3

client = TestClient(app)

RAW_NIHON_SAMPLE = (
    "[host] [Send]\x02MEK-7222  \r   22\r01024\rCLOSED      \rCBC + Diff  \r01\r"
    "BLOOD           \r01  \r0002413   \rV03-02  \rV04-02  \rV03-01  \r01536\r1    \r   \r"
    "2026\r08\r17\r     \r14\r57\r05\r102            \r"
    " 4.1  \r30.4* \r55.3* \r10.0* \r 2.7* \r 1.6* \r"
    " 1.3* \r 2.3* \r 0.4* \r 0.1* \r 0.1* \r"
    "6.92H \r16.9  \r52.7H \r76.2L \r24.4L \r32.1  \r12.9  \r 175  \r0.13L \r 7.6  \r17.6H \r\x03\r\n"
    "[host] [Send]\x02EXP\r00512\rMEK-7222  \r01\r\x03\r\n"
)


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
