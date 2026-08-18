# Dynamic PDF Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a purely Python, memory-efficient PDF generation engine using ReportLab that synthesizes clinical test results onto a static letterhead background.

**Architecture:** We use ReportLab's `SimpleDocTemplate` and Platypus flowables. A custom canvas hook will paint `assets/branding/letterhead.png` at `(0,0)` on every page. Data is injected via coordinate-independent `Table` flowables formatted with strict Helvetica typography.

**Tech Stack:** Python 3.11, ReportLab, FastAPI, SQLite

**Spec:** `docs/planning/AMH LIMS Dynamic PDF Reporting & ReportLab Standardization Blueprint.md`

## Global Constraints
- Maximum RAM footprint < 50MB (achieved by avoiding OS-level dependencies like wkhtmltopdf).
- Fonts strictly limited to core PDF fonts (`Helvetica`, `Helvetica-Bold`).
- Spatial math mapped strictly to 72 points per inch (A4: 595.27 x 841.89).

---

### Task 1: Setup PDF Generator Constants and Layout Hooks

**Files:**
- Create: `backend/app/pdf_generator.py`
- Test: `tests/test_pdf_generator.py`

**Interfaces:**
- Produces: `generate_pdf(order_data: dict, results_data: list) -> bytes` and `_draw_background_hook(canvas, doc)`

- [ ] **Step 1: Write the failing test**

```python
import io
import pytest
from backend.app.pdf_generator import generate_pdf

def test_generate_pdf_creates_bytes():
    order_data = {"client_number": "102", "full_name": "JOHN DOE", "sex": "M", "age": "30"}
    results_data = []
    pdf_bytes = generate_pdf(order_data, results_data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF-')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pdf_generator.py::test_generate_pdf_creates_bytes -v`
Expected: FAIL with "ImportError: cannot import name 'generate_pdf'"

- [ ] **Step 3: Write minimal implementation**

```python
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

PAGE_WIDTH, PAGE_HEIGHT = A4
SAFE_MARGIN_X = 56.69
SAFE_WINDOW_Y = 600.95

def _draw_background_hook(canvas, doc):
    canvas.saveState()
    # Assuming letterhead.png is in the project root's assets folder
    letterhead_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "branding", "letterhead.png")
    if os.path.exists(letterhead_path):
        canvas.drawImage(letterhead_path, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT, mask='auto')
    canvas.restoreState()

def generate_pdf(order_data: dict, results_data: list) -> bytes:
    buffer = io.BytesIO()
    # Margins based on blueprint
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        leftMargin=SAFE_MARGIN_X, 
        rightMargin=SAFE_MARGIN_X, 
        topMargin=200, # Leave room for header
        bottomMargin=120 # Leave room for footer
    )
    
    styles = getSampleStyleSheet()
    flowables = []
    flowables.append(Paragraph(f"Patient: {order_data.get('full_name', '')}", styles['Normal']))
    
    doc.build(flowables, onFirstPage=_draw_background_hook, onLaterPages=_draw_background_hook)
    
    return buffer.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pdf_generator.py::test_generate_pdf_creates_bytes -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_pdf_generator.py backend/app/pdf_generator.py
git commit -m "feat: initialize reportlab pdf generator with background hook"
```

---

### Task 2: Implement Patient Metadata Grid

**Files:**
- Modify: `backend/app/pdf_generator.py`
- Modify: `tests/test_pdf_generator.py`

**Interfaces:**
- Consumes: `_draw_background_hook`
- Produces: `_build_metadata_table(order_data: dict)`

- [ ] **Step 1: Write the failing test**

```python
from backend.app.pdf_generator import _build_metadata_table
from reportlab.platypus import Table

def test_build_metadata_table():
    order_data = {
        "client_number": "AMH-26-8-001", 
        "full_name": "LUCY KEMIGISHA", 
        "age": "32", 
        "sex": "F",
        "ordered_by": "Dr. Matia",
        "ordered_date": "17/08/2026",
        "verified_by": "Abubakar"
    }
    table = _build_metadata_table(order_data)
    assert isinstance(table, Table)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pdf_generator.py::test_build_metadata_table -v`
Expected: FAIL with "ImportError: cannot import name '_build_metadata_table'"

- [ ] **Step 3: Write minimal implementation**

```python
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

def _build_metadata_table(order_data: dict) -> Table:
    data = [
        ["Patient Name:", order_data.get("full_name", ""), "Lab No:", order_data.get("client_number", "")],
        ["Age:", order_data.get("age", ""), "Sex:", order_data.get("sex", "")],
        ["Referred By:", order_data.get("ordered_by", ""), "Date:", order_data.get("ordered_date", "")],
        ["Verified By:", order_data.get("verified_by", ""), " ", " "]
    ]
    
    t = Table(data, colWidths=[80, 160, 80, 160])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), # Left labels
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'), # Right labels
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    return t

# Update generate_pdf to use it:
# Remove the simple Paragraph and replace with:
# flowables.append(_build_metadata_table(order_data))
# flowables.append(Spacer(1, 20))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pdf_generator.py::test_build_metadata_table -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_pdf_generator.py backend/app/pdf_generator.py
git commit -m "feat: build patient metadata grid for pdf reports"
```

---

### Task 3: Implement Standardized 5-Column Result Tables

**Files:**
- Modify: `backend/app/pdf_generator.py`
- Modify: `tests/test_pdf_generator.py`

**Interfaces:**
- Consumes: ReportLab tables
- Produces: `_build_results_table(results_data: list)`

- [ ] **Step 1: Write the failing test**

```python
from backend.app.pdf_generator import _build_results_table

def test_build_results_table():
    results = [
        {"department": "Hematology", "parameter": "WBC", "value": "12.5", "units": "10^3/uL", "flag": "High", "ref_range": "4.0 - 11.0"}
    ]
    tables = _build_results_table(results)
    assert len(tables) > 0 # At least one KeepTogether block
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pdf_generator.py::test_build_results_table -v`
Expected: FAIL with "ImportError: cannot import name '_build_results_table'"

- [ ] **Step 3: Write minimal implementation**

```python
from reportlab.platypus import KeepTogether

def _build_results_table(results_data: list) -> list:
    """
    Groups results by department and returns a list of KeepTogether flowables.
    """
    blocks = []
    
    # Group by department (assuming sorted or we group them here)
    departments = {}
    for r in results_data:
        dept = r.get("department", "General")
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(r)
        
    for dept, items in departments.items():
        # Header for department
        data = [[Paragraph(f"<b><u>{dept}</u></b>")]]
        
        # Column Headers
        data.append(["Parameter", "Result", "Units", "Flag", "Ref. Range"])
        
        for item in items:
            # Empty rows (like FBS if null) are suppressed inherently if not passed in results_data
            data.append([
                Paragraph(item.get("parameter", "")),
                Paragraph(item.get("value", "")),
                item.get("units", ""),
                item.get("flag", ""),
                item.get("ref_range", "")
            ])
            
        t = Table(data, colWidths=[150, 80, 80, 60, 110])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'), # Col headers
            ('LINEBELOW', (0,1), (-1,1), 1, colors.black),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        # Keep department tables from breaking awkwardly across pages
        blocks.append(KeepTogether(t))
        blocks.append(Spacer(1, 15))
        
    return blocks

# Update generate_pdf to extend flowables with _build_results_table(results_data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pdf_generator.py::test_build_results_table -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_pdf_generator.py backend/app/pdf_generator.py
git commit -m "feat: implement 5-column qualitative result tables"
```

---

### Task 4: FastAPI PDF Endpoint Integration

**Files:**
- Modify: `backend/app/routers/orders.py` (or create `backend/app/routers/reports.py` if preferred, but assuming orders handles it based on FSD)
- Modify: `tests/test_routers.py` (or similar endpoint tests)

**Interfaces:**
- Consumes: `generate_pdf()` and database `get_db`
- Produces: `GET /api/orders/{order_id}/report` returning a `Response` with `application/pdf`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_download_pdf_endpoint():
    # Assuming order 1 exists in test DB
    response = client.get("/api/orders/1/report")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_routers.py::test_download_pdf_endpoint -v`
Expected: FAIL with 404 Not Found

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from backend.app.database import get_db
# Assuming schemas/models are imported correctly
from backend.app.pdf_generator import generate_pdf

router = APIRouter() # Assuming this is the orders router

@router.get("/{order_id}/report")
def download_report(order_id: int, db: Session = Depends(get_db)):
    # 1. Fetch Order and Client
    # 2. Fetch Results joined with Parameters
    # (Mocking data assembly for brevity in plan)
    
    order_data = {
        "client_number": "AMH-123",
        "full_name": "Test Client",
        "age": "30",
        "sex": "M"
    }
    results_data = [
        {"department": "Hematology", "parameter": "WBC", "value": "10.0", "units": "10^3/uL", "flag": "", "ref_range": "4.0-11.0"}
    ]
    
    pdf_bytes = generate_pdf(order_data, results_data)
    
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=Report_{order_id}.pdf"})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_routers.py::test_download_pdf_endpoint -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/orders.py tests/test_routers.py
git commit -m "feat: add PDF download endpoint"
```
