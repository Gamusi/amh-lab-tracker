# UX Refactor and Reporting Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the frontend to strictly obey Ugandan Clinical Lab Reporting Standards without embedding business logic in the UI, make config tables collapsible and complete, and fix the 422 result entry API errors.

**Architecture:** 
1. Database Schema additions (Wards).
2. Backend API adjustments (`/api/wards`, `/api/results` schema decoupling).
3. Frontend UI changes (Collapsible Configs, Tailored Result Modals per test type).

**Tech Stack:** FastAPI, SQLite, Vanilla JS/HTML.

**Spec:** C:\Users\dell\Documents\amh-lab-tracker\docs\planning\ugandan-clinical-lab-reporting-standards.md

## Global Constraints
- **No Toasts:** Only use clean uncluttered modals. No browser toasts (`app.showToast` usage must be phased out for modals).
- **No Business Logic on Frontend:** The frontend is strictly an interaction layer. Evaluation logic happens on the backend.
- **Reporting Standards:** Obey `ugandan-clinical-lab-reporting-standards.md` precisely for Urinalysis, Widal, Positive/Negative, and Numeric inputs.

---

### Task 1: Update Best Practices
**Files:**
- Modify: `docs/BEST_PRACTICES.md`

- [ ] **Step 1: Append new rules**
Append the following exact rules to the file:
"1. No toast notifications for anything in the app. Only use clean, uncluttered modals for success/error states and prompts.
 2. The frontend is the interaction layer for users to interact with the backend; it must not contain any business logic."

- [ ] **Step 2: Commit**
```bash
git add docs/BEST_PRACTICES.md
git commit -m "docs: append toast and frontend business logic rules"
```

### Task 2: Backend Wards Configuration & Seed Updates
**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/config.py`
- Modify: `backend/app/seed.py`
- Test: `tests/test_backend_api.py`

**Interfaces:**
- Produces: `GET, POST, PUT, DELETE /api/config/wards` endpoints.

- [ ] **Step 1: Add Wards to Database**
In `database.py`, add a `wards` table (id, name, is_active).

- [ ] **Step 2: Add Ward Schemas**
In `schemas.py`, add `WardBase(BaseModel)`, `WardCreate(WardBase)`, `WardResponse(WardBase, id: int, is_active: bool)`.

- [ ] **Step 3: Implement Ward API endpoints**
In `routers/config.py`, implement CRUD endpoints for wards.

- [ ] **Step 4: Update Seed Script**
In `seed.py`, seed Wards: "ANC", "MCH", "Emergency", "Theater", "Labour", "OPD", "IPD", "Pediatrics", "TB Clinic".

- [ ] **Step 5: Test & Commit**
Verify via `pytest tests/test_backend_api.py`.
```bash
git add backend/app/
git commit -m "feat: add Wards configuration backend"
```

### Task 3: Backend Result Entry API Refactor
**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/clients.py`
- Test: `tests/test_backend_api.py`

**Interfaces:**
- Produces: Fixed `TestResultCreate` schema that doesn't blindly fail with 422, removing `is_positive` requirement from frontend. The backend computes `is_positive` using `evaluator.py`.

- [ ] **Step 1: Update TestResultCreate Schema**
Remove `is_positive` from `TestResultCreate`. Ensure `parameter_results` matches what the frontend will send.

- [ ] **Step 2: Update Result Entry Logic**
In `routers/clients.py` `enter_result`, call `evaluator.evaluate_result` on the `result_value` to determine if it is abnormal (which drives `is_positive` for DailyEntry logs). Use the Patient's DOB and Sex from the Visit's Client.

- [ ] **Step 3: Add Visit Test Appending**
In `routers/clients.py`, add `POST /api/visits/{visit_id}/orders` to allow adding tests to an existing visit before dispatch.

- [ ] **Step 4: Test & Commit**
```bash
git add backend/app/
git commit -m "feat: refactor result entry payload and evaluation"
```

### Task 4: Frontend "Create Visit" UX & Config Tab
**Files:**
- Modify: `frontend/static/index.html`
- Modify: `frontend/static/js/app.js`

- [ ] **Step 1: Update Visit UI**
In `app.js` `selectClient`, change "Select Tests..." text. Add a text input for `<input type="text" id="test-search" placeholder="Search tests..." onkeyup="app.filterTests(this.value)">`. Change Ward select to fetch from `/api/config/wards`.

- [ ] **Step 2: Config Tab Collapsibility & Sections**
In `app.js` `renderConfig`, fetch Clinicians and Wards. Render them in collapsible containers (e.g. `<details><summary>...</summary>...</details>`).

- [ ] **Step 3: Verify & Commit**
Ensure UI syntax is valid.
```bash
git add frontend/
git commit -m "feat: improve visit creation UX and config UI"
```

### Task 5: Tailored Result Entry Modals
**Files:**
- Modify: `frontend/static/index.html`
- Modify: `frontend/static/js/app.js`

- [ ] **Step 1: Update Modal HTML**
Create specialized modal forms in `index.html` or generated via `app.js` for:
- Qualitative (Positive/Negative)
- Widal (Positive/Negative + Titers)
- Quantitative (Value + Unit dropdown)
- Urinalysis (Full panel with defaults: Appearance=Clear, Color=Yellow, SG=1.015, pH=6.0, Proteins=Nil, Glucose=Nil, Bilirubin=Nil, Urobilinogen=Normal, Ketones=Nil, Blood=Nil, Nitrites=Negative, Leukocytes=Nil)

- [ ] **Step 2: Dynamic Modal Rendering**
In `app.js` `showEnterResultModal`, parse the `testName` and `parameters` to determine which form to display. Do not do surveillance logic here. Just capture the exact values the standards document dictates.

- [ ] **Step 3: Replace Toasts with Modals**
Remove `showToast` in `app.js` and implement a global generic `showNotificationModal(title, message, isError)` function.

- [ ] **Step 4: Commit**
```bash
git add frontend/
git commit -m "feat: implement tailored result entry modals and remove toasts"
```
