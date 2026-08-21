# Nihon Kohden CBC Analyzer Parser & Dedicated Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a backend raw text parser for the Nihon Kohden MEK-7222 CBC analyzer, an integration API endpoint, an in-modal paste/capture workflow in the frontend with manual review fallback, and a dedicated ReportLab CBC report page styled according to `docs/reference/rptrchemcour.pdf`.

**Architecture:** A standalone Python parser extracts the 22 CBC parameters, sample metadata, and hardware flags from raw text. A FastAPI endpoint serves this to the frontend, which populates the existing CBC entry modal for human verification before saving. On PDF generation, visits containing CBC render the test on its own dedicated full-page layout with grouped indices and client metadata.

**Tech Stack:** Python 3.14, FastAPI, ReportLab 4.x, SQLite, Vanilla JavaScript / HTML5 / CSS3.

**Spec:** [`docs/superpowers/specs/2026-08-21-nihon-kohden-cbc-integration-design.md`](file:///c:/Users/dell/Documents/amh-lab-tracker/docs/superpowers/specs/2026-08-21-nihon-kohden-cbc-integration-design.md)

## Global Constraints

- No emojis anywhere in code, UI, comments, or commit messages.
- Always use the term "Client", never "Patient".
- No toast notifications; use clean modals only.
- Frontend is an interaction layer only; all parsing and business logic resides in backend.
- Calibrated hardware flags and raw numbers preserved without mutation.
- TDD required: tests before implementation for each task.

---

### Task 1: Nihon Kohden MEK-7222 Output Parser

**Files:**
- Create: `backend/app/parsers/__init__.py`
- Create: `backend/app/parsers/nihon_kohden.py`
- Test: `tests/test_nihon_kohden_parser.py`

**Interfaces:**
- Produces: `parse_nihon_kohden_output(raw_text: str) -> dict`
  - Output dict structure:
    ```python
    {
        "status": "success",
        "sample_id": "0002413",
        "timestamp": "2026-08-17 14:57:05",
        "device_model": "MEK-7222",
        "parameters": [
            {"name": "Total WBC Count (White Blood Cells)", "value": "4.1", "flag": None, "unit": "10³/µL"},
            {"name": "Neutrophils (%) [Relative Count]", "value": "30.4", "flag": "*", "unit": "%"},
            ...
        ]
    }
    ```

- [ ] **Step 1: Write the failing test**

```python
import pytest
from backend.app.parsers.nihon_kohden import parse_nihon_kohden_output

RAW_NIHON_SAMPLE = """[host] [Send] MEK-7222     2201024CLOSED      CBC + Diff  01BLOOD           01  0002413   V03-02  V04-02  V03-01  015361       20260817     145705102             4.1  30.4* 55.3* 10.0*  2.7*  1.6*  1.3*  2.3*  0.4*  0.1*  0.1* 6.92H 16.9  52.7H 76.2L 24.4L 32.1  12.9   175  0.13L  7.6  17.6H                                                                                                                                                                                                                           +  +  +              +
[host] [Send] EXP00512MEK-7222  01                                                                                                                                                                                                                          00                                 4.0 9.028.078.017.057.0 0.010.0 0.010.0 0.0 2.0 1.1 7.0 0.7 5.1 0.0 0.9 0.0 0.9 0.0 0.23.765.7012.018.033.552.080.0 10028.032.031.035.011.614.0 150 3500.160.33 7.011.015.017.0"""

def test_parse_valid_nihon_kohden_output():
    res = parse_nihon_kohden_output(RAW_NIHON_SAMPLE)
    assert res["status"] == "success"
    assert res["sample_id"] == "0002413"
    assert "2026-08-17" in res["timestamp"]
    assert len(res["parameters"]) == 22

    params_by_name = {p["name"]: p for p in res["parameters"]}
    
    assert params_by_name["Total WBC Count (White Blood Cells)"]["value"] == "4.1"
    assert params_by_name["Total WBC Count (White Blood Cells)"]["flag"] is None

    assert params_by_name["Neutrophils (%) [Relative Count]"]["value"] == "30.4"
    assert params_by_name["Neutrophils (%) [Relative Count]"]["flag"] == "*"

    assert params_by_name["Red Blood Cells (RBC)"]["value"] == "6.92"
    assert params_by_name["Red Blood Cells (RBC)"]["flag"] == "H"

    assert params_by_name["Mean Cell Volume (MCV)"]["value"] == "76.2"
    assert params_by_name["Mean Cell Volume (MCV)"]["flag"] == "L"

def test_parse_invalid_text_raises_or_returns_error():
    res = parse_nihon_kohden_output("random invalid garbage text")
    assert res["status"] == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nihon_kohden_parser.py -v`  
Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement parser**

Write `backend/app/parsers/nihon_kohden.py` with parameter ordering and regex tokenization matching the 22 parameters.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_nihon_kohden_parser.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/parsers/ tests/test_nihon_kohden_parser.py
git commit -m "feat(parser): add nihon kohden mek-7222 raw output parser"
```

---

### Task 2: Analyzer Parsing API Endpoint

**Files:**
- Create: `backend/app/routers/integrations.py`
- Modify: `backend/app/main.py:30-45`
- Test: `tests/test_integrations_api.py`

**Interfaces:**
- Endpoint: `POST /api/integrations/parse-analyzer-output`
- Request Schema:
  ```python
  class AnalyzerParseRequest(BaseModel):
      analyzer_type: str = "nihon_kohden"
      raw_text: str
  ```
- Response: Returns parsed output dict or HTTP 400 with detail.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import get_current_user
from backend.app.database import get_db

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_integrations_api.py -v`  
Expected: FAIL with 404 Not Found.

- [ ] **Step 3: Implement endpoint and register router**

Create `backend/app/routers/integrations.py` and register in `backend/app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_integrations_api.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/integrations.py backend/app/main.py tests/test_integrations_api.py
git commit -m "feat(api): add parse-analyzer-output endpoint"
```

---

### Task 3: CBC In-Modal Analyzer Paste & Auto-Populate UI

**Files:**
- Modify: `frontend/static/index.html:220-250`
- Modify: `frontend/static/js/app.js:1760-1830`

**Interfaces:**
- In `showEnterResultModal(orderId, testId, testName, ...)`:
  - If testName contains `Complete Blood Count (CBC)` or `CBC`:
    - Display `[ Paste from Analyzer ]` action bar.
    - Toggle paste container with textarea and `[ Parse & Populate ]` button.
    - Call `POST /api/integrations/parse-analyzer-output` on click.
    - For each matched parameter, set corresponding input `.value` and badge/flag indicator.
    - User can manually edit/review and submit via standard "Save Result".

- [ ] **Step 1: Add paste container to modal in `index.html`**
- [ ] **Step 2: Add `toggleAnalyzerPaste()` and `parseAndPopulateAnalyzerData()` in `app.js`**
- [ ] **Step 3: Wire parameter mapping to populate child inputs by parameter name**
- [ ] **Step 4: Verify manual verification and submission flow**
- [ ] **Step 5: Commit**

```bash
git add frontend/static/index.html frontend/static/js/app.js
git commit -m "feat(ui): add paste from analyzer option for CBC result entry"
```

---

### Task 4: Dedicated CBC ReportLab PDF Generation Page

**Files:**
- Modify: `backend/app/pdf_generator.py`
- Test: `tests/test_pdf_cbc_report.py`

**Interfaces:**
- `_build_cbc_report_page(order_data: dict, cbc_results: list) -> list`:
  - Renders `HAEMATOLOGY CBC REPORT` title box.
  - Client metadata table (Name, Age, Sex, Lab No, Date, Ref Clinician, Specimen, Ward).
  - 4 Categorized Table Groups:
    1. Main & Indices (WBC, RBC, Hb, HCT, MCV, MCH, MCHC, PLT)
    2. Differential Relative Count (%)
    3. Differential Absolute Count ($10^9/\mu\text{L}$)
    4. RBC & Platelet Indices (RDW, PCT, MPV, PDW)
  - Columns: `Test`, `Result`, `Units`, `Flag`, `Ref. Ranges`.
  - Dynamic biological reference intervals for pediatric vs adult male/female.
  - Technologist signature footer.
- `generate_pdf()` detects if CBC is in results; appends `PageBreak()` and the dedicated CBC layout if present.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from backend.app.pdf_generator import generate_pdf

def test_generate_pdf_with_cbc_dedicated_page():
    order_data = {
        "full_name": "WANELOBA DANIEL",
        "client_number": "AMH-C26-0094",
        "lab_number": "94",
        "age": "12y",
        "sex": "Male",
        "ordered_date": "2026-08-15",
        "requested_by": "DR. TUGUME",
        "ward_of_origin": "OPD"
    }
    results_data = [
        {
            "department": "Hematology",
            "tests": [
                {
                    "test_name": "Complete Blood Count (CBC)",
                    "result": "Completed",
                    "parameters": [
                        {"name": "Total WBC Count (White Blood Cells)", "result": "3.7", "unit": "10^3 / uL", "flag": "Low", "reference": "6.0-14.0"},
                        {"name": "Red Blood Cells (RBC)", "result": "4.56", "unit": "10^6 / uL", "flag": "", "reference": "4.00 -5.20"},
                        {"name": "Hemoglobin (Hb)", "result": "12.1", "unit": "g/dL", "flag": "", "reference": "11.5-15.5"},
                        {"name": "Hematocrit (HCT)", "result": "37.2", "unit": "%", "flag": "", "reference": "35.0-45.0"},
                        {"name": "Mean Cell Volume (MCV)", "result": "81.6", "unit": "fL", "flag": "", "reference": "77.0-95.0"},
                        {"name": "Mean Cell Hb (MCH)", "result": "26.5", "unit": "pg", "flag": "", "reference": "23.0-31.0"},
                        {"name": "Mean Cell Hb Conc (MCHC)", "result": "32.5", "unit": "g/dL", "flag": "", "reference": "28.0-33.0"},
                        {"name": "Platelets Count (PLT)", "result": "85", "unit": "10^3 / uL", "flag": "Low", "reference": "150-400"},
                        {"name": "Neutrophils (%) [Relative Count]", "result": "47.7", "unit": "%", "flag": "", "reference": "40.0-65.0"},
                        {"name": "Lymphocytes (%) [Relative Count]", "result": "30.6", "unit": "%", "flag": "", "reference": "19.2-49.5"},
                        {"name": "Monocytes (%) [Relative Count]", "result": "3.8", "unit": "%", "flag": "Low", "reference": "4.5-12.1"},
                        {"name": "Eosinophils (%) [Relative Count]", "result": "17.1", "unit": "%", "flag": "High", "reference": "1.0-12.0"},
                        {"name": "Basophils (%) [Relative Count]", "result": "0.8", "unit": "%", "flag": "", "reference": "0.0-1.0"},
                        {"name": "Neutrophils (Absolute Count)", "result": "1.8", "unit": "10^9 / uL", "flag": "Low", "reference": "2.00-6.00"},
                        {"name": "Lymphocytes (Absolute Count)", "result": "1.1", "unit": "10^9 / uL", "flag": "Low", "reference": "5.00-8.50"},
                        {"name": "Monocytes (Absolute Count)", "result": "0.1", "unit": "10^9 / uL", "flag": "Low", "reference": "0.70-1.50"},
                        {"name": "Eosinophils (Absolute Count)", "result": "0.6", "unit": "10^9 / uL", "flag": "", "reference": "0.30-0.80"},
                        {"name": "Basophils (Absolute Count)", "result": "0.0", "unit": "10^9 / uL", "flag": "", "reference": "0.0-0.5"},
                        {"name": "RBC Distribution Width (RDW)", "result": "13.2", "unit": "%", "flag": "", "reference": "11.0-16.0"},
                        {"name": "Thrombocrit (PCT)", "result": "0.06", "unit": "%", "flag": "Low", "reference": "0.16-0.33"},
                        {"name": "Mean Platelet Volume (MPV)", "result": "6.8", "unit": "fL", "flag": "", "reference": "6.0 - 10.0"},
                        {"name": "PLT Distribution Width (PDW)", "result": "20.9", "unit": "%", "flag": "High", "reference": "12.0 - 18.0"}
                    ]
                }
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b'%PDF-')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pdf_cbc_report.py -v`

- [ ] **Step 3: Implement dedicated CBC report layout in `pdf_generator.py`**
- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pdf_cbc_report.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pdf_generator.py tests/test_pdf_cbc_report.py
git commit -m "feat(pdf): implement dedicated HAEMATOLOGY CBC REPORT page in reportlab"
```

---

### Task 5: End-to-End Test Suite Verification

**Files:**
- Test: Full pytest suite across repository.

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest -v`  
Expected: All tests pass (0 failures).

- [ ] **Step 2: Commit any final integration polish**
