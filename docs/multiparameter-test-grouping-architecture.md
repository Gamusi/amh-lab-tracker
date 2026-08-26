# Multi-Parameter & Diagnostic Panel Grouping Architecture

## 1. Executive Summary & Context

Clinical laboratory medicine relies heavily on composite diagnostic panels where a single clinical order encompasses multiple discrete biochemical, hematological, or microbiological parameters. Key panels in the M-LIS include:
- **Complete Blood Count (CBC)**: 22 distinct quantitative parameters spanning red cell, white cell, differential, and platelet indices. While automated hematology analyzers measure and derive these parameters as a single unified analytical process, it is critical to identify and track each parameter independently; in clinical pathology, deviations from normal are rarely uniform across all analytes—specific parameters deviate under disease states (e.g., isolated erythrocytosis, selective neutropenia, thrombocytopenia) while others remain entirely normal.
- **Urinalysis**: 10 chemical strip analytes (pH, Protein, Glucose, Leukocytes, Nitrites, Ketones, Urobilinogen, Bilirubin, Blood, Specific Gravity) combined with macroscopic and microscopic examination findings. Reported as one composite test with multiple separately measured parameters, each providing distinct clinical insight into renal function, systemic metabolism, hepatic clearance, and urinary tract infections.
- **Renal Function Tests (RFTs)**: Urea, Creatinine (with optional estimated Glomerular Filtration Rate).
- **Electrolyte Panel**: Sodium (Na⁺), Potassium (K⁺), Chloride (Cl⁻). Maintained as a separate diagnostic panel from RFTs to allow targeted electrolyte management or combined renal-metabolic profiling.
- **Liver Function Tests (LFTs)**: Total Bilirubin, Direct Bilirubin, ALT, AST, Alkaline Phosphatase, Total Protein, Albumin.
- **Lipid Profile**: Total Cholesterol, Triglycerides, HDL Cholesterol, LDL Cholesterol.
- **HIV Testing Service (HTS)**: Multi-step algorithm consisting of Screening Assay (Determine), Confirmatory Assay (Stat-Pak), and Tie-Breaker (SD Bioline).

This document details the architectural design, database modeling, business logic, verification strategy, and maintenance non-negotiables for grouping, ordering, entering, and reporting multi-parameter tests within the M-LIS LIMS.

---

## 2. Architectural Design Decisions & Technical Justification

### 2.1 Dual-Layer Hierarchy: Panels vs Discrete Parameters

#### Design Decision
The system separates test categorization into two relational levels:
1. **Parent Test Rollup (`tests.parent_rollup_id`)**: Enables hierarchical nesting within the test catalog so composite test packages or sub-panels can roll up under high-level departmental parent headings.
2. **Discrete Parameter Definitions (`test_parameters`)**: Maps specific sub-analytes belonging to a parent panel test, specifying individual parameter names, measurement units, reference intervals, panic thresholds, and sorting orders.

```
+-------------------------------------------------------------------+
| tests (Parent Panel, e.g. "Complete Blood Count (CBC)")           |
| - id: 1                                                           |
| - section_id: 1 (Hematology)                                      |
| - result_type: 'panel'                                            |
| - is_tracked: 0                                                   |
+---------------------------------+---------------------------------+
                                  | 1:N
                                  v
+-------------------------------------------------------------------+
| test_parameters (Discrete Analytes)                               |
| - id: 101 | parameter_name: "Total WBC Count"   | unit: "10³/µL"  |
| - id: 102 | parameter_name: "Neutrophils (%)"   | unit: "%"       |
| - id: 103 | parameter_name: "Hemoglobin (Hb)"   | unit: "g/dL"    |
| - id: ... | ... (22 sequential parameters)      | ...             |
+---------------------------------+---------------------------------+
```

#### Clinical & Technical Justification
- **Single-Click Ordering with Unified Panel Integrity**: Clinicians order a single composite panel (e.g., "Complete Blood Count (CBC)" or "Urinalysis") under a single visit order. The system never fragments multi-parameter tests into separate visits or separate test orders.
- **Granular Discrete Parameter Review**: At the workbench level, lab technologists enter and review results in a dedicated multi-field interface where each parameter displays its own value, unit, and machine/evaluator flag.
- **Normalized Storage & Scalability**: Storing parameter values as structured child rows in `test_results` linked to a single `test_orders.id` enables direct relational querying, automated reference range comparison, and audit tracking per parameter while keeping the visit structure unified.
- **Flexible Catalog Management**: Lab administrators can add, reorder, or update individual parameters of a panel (e.g., adjusting reference ranges or units) in `test_parameters` without breaking existing visit orders or historic reports.


---

### 2.2 Relational Data Modeling

#### Schema Definition (`backend/app/database.py`)

```sql
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    section_id INTEGER NOT NULL REFERENCES sections(id),
    is_tracked BOOLEAN NOT NULL DEFAULT 0,
    parent_rollup_id INTEGER REFERENCES tests(id),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    result_type TEXT DEFAULT 'qualitative', -- 'numeric', 'qualitative', 'semi_quantitative', 'options', 'panel'
    default_unit TEXT,
    secondary_unit TEXT,
    ref_range TEXT,
    panic_value_low FLOAT,
    panic_value_high FLOAT,
    options TEXT,
    UNIQUE(name, section_id)
);

CREATE TABLE IF NOT EXISTS test_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    parameter_name TEXT NOT NULL,
    unit TEXT,
    ref_range TEXT,
    panic_value_low FLOAT,
    panic_value_high FLOAT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL REFERENCES visits(id),
    test_id INTEGER NOT NULL REFERENCES tests(id),
    sample_id TEXT,
    ordered_by_user_id INTEGER REFERENCES users(id),
    ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'completed'
    order_category TEXT DEFAULT 'in-house'
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES test_orders(id) ON DELETE CASCADE,
    parameter_id INTEGER REFERENCES test_parameters(id),
    result_value TEXT,
    result_unit TEXT,
    is_positive BOOLEAN,
    entered_by_user_id INTEGER REFERENCES users(id),
    entered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified_by_user_id INTEGER REFERENCES users(id),
    verified_at DATETIME,
    edit_reason TEXT,
    edited_by_user_id INTEGER REFERENCES users(id),
    edited_at DATETIME
);
```

---

### 2.3 Result Entry & Clinical Evaluator Workflow

#### Data Flow
1. **Order Initialization**: When a visit is registered with test IDs `[test_id]`, `test_orders` records are generated with `status = 'pending'`.
2. **Modal Rendering**: When the technologist clicks "Enter Result", the system queries `GET /api/config/tests/{test_id}/parameters`.
   - If the test has parameters (`result_type == 'panel'`), the UI dynamically constructs a form displaying all child parameters sorted by `sort_order`.
   - If the test is an atomic single-result test, a single result input with relevant dropdown options or numerical units is displayed.
3. **Submission**: The frontend submits payload `TestResultCreate` to `POST /api/clients/orders/{order_id}/results`:
   ```json
   {
     "order_id": 42,
     "parameter_results": [
       { "parameter_id": 1, "result_value": "4.2" },
       { "parameter_id": 2, "result_value": "26.5" },
       { "parameter_id": 3, "result_value": "45.6" }
     ],
     "edit_reason": null
   }
   ```
4. **Backend Processing & Auto-Evaluation**:
   - Backend iterates over `parameter_results`.
   - For each parameter, calls `evaluate_result(parameter_name, result_value, client.dob, client.sex, entry_date)`.
   - Populates `test_results` rows linked to the parent `order_id` and corresponding `parameter_id`.
   - Updates `test_orders.status = 'completed'`.
   - Automatically generates a sequential daily lab number if not already assigned to the visit.
   - Logs audit trail entry with technologist ID and timestamp.

---

### 2.4 Surveillance & HMIS Positivity Tracking Standards

In compliance with `docs/BEST_PRACTICES.md` Section E:
- **Composite Panels (`result_type = 'panel'`)**: `is_tracked = 0` by default. General panels represent clinical work volume rather than singular infectious disease occurrences.
- **Specific Clinical Findings**: If a sub-parameter represents an epidemic or surveillance indicator (such as severe anemia for CBC or diabetic hyperglycemia for Blood Sugar), the evaluation engine evaluates the threshold against client age/gender reference intervals.
- **Automated Read-Only Daily Log Ledger**: The Daily Surveillance Ledger computes counts and positivity rates dynamically by querying completed orders. No manual editing or override buttons exist on the surveillance ledger.

---

## 3. Technology Stack & Component Mapping

| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| **Backend API Framework** | FastAPI (Python 3.14) | High-performance async REST routing, request validation, dependency injection for DB sessions and authentication. |
| **Data Persistence** | SQLite 3 (WAL mode) | Relational storage with foreign key cascades, transactional integrity, and in-memory test execution. |
| **Evaluation Engine** | Pure Python (`evaluator.py`) | Age- and sex-stratified normal, abnormal, and critical panic value interpretation using `reference_ranges.json`. |
| **Frontend UI Interaction** | Vanilla JavaScript (ES6+) | Interaction layer only. Renders dynamic modal parameter grids (`modal-param-row`), handles selection toggles, and communicates with backend APIs. |
| **PDF Generation Engine** | ReportLab (`pdf_generator.py`) | Categorized tabular formatting, multi-column layout, client demographic letterhead, and keep-together pagination. |

---

## 4. Non-Negotiables for Maintaining Architecture

1. **Client vs Patient Terminology**: Always use the term **'Client'** throughout code, documentation, schema names, and UI labels.
2. **Frontend Interaction Boundary**: The frontend must remain an interaction layer only. No business logic, reference range calculations, or validation gatekeeping may be performed on the client side.
3. **Zero Emoji & Minimal UI Design**: No emojis anywhere in code, comments, commit messages, or UI. Use Lucide icons exclusively. Avoid pill badges or decorative tags in favor of plain text and clean tables.
4. **Cascade Integrity**: Deleting or modifying a parent panel in the catalog must validate dependent child parameters and historical test results before committing.
5. **Surveillance Ledger Immutability**: The Daily Log must remain an automated, calculated reflection of saved workbench results. Manual input fields must never be added to the surveillance ledger.

---

## 5. Potential Future Improvements

1. **Dynamic Administrative Panel Builder**: Web-based drag-and-drop builder allowing lab directors to create custom multi-parameter panels and define parameter sequences directly from the settings interface.
2. **Automated Reflex Testing Rules**: Engine rule triggers where abnormal panel results automatically generate follow-up diagnostic orders (e.g., automated Urine Microscopy order generated when Urinalysis strip detects Leukocytes or Protein).
3. **Standard Terminology Mapping (LOINC / SNOMED CT)**: Assign standard LOINC codes to all panel definitions and sub-parameters to facilitate national digital health interoperability (e.g., Ugandan e-HMIS / DHIS2 integration).
4. **Calculated Parameter Automation**: Automatic backend derivation of computed parameters (e.g., automated calculation of eGFR from Creatinine/Age/Sex, or automated computation of Absolute Differential counts from Total WBC and Relative Percentages).
