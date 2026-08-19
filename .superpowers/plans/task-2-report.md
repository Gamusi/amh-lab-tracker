# Task 2 Report: Backend Wards Configuration & Seed Updates

## What was implemented
1. **Database Schema:** Added `wards` table (`id`, `name`, `is_active`) to `SCHEMA_SQL` in `backend/app/database.py`.
2. **Schemas:** Created `WardBase`, `WardCreate`, `WardUpdate`, and `WardResponse` Pydantic models in `backend/app/schemas.py`.
3. **CRUD API Endpoints:** Implemented Ward endpoints in `backend/app/routers/config.py`:
   - `GET /api/config/wards` (with optional `active_only` filter, alphabetical ordering)
   - `POST /api/config/wards` (creates ward with duplicate/empty validation and audit log)
   - `PUT /api/config/wards/{ward_id}` (updates name/is_active status with validation and audit log)
   - `DELETE /api/config/wards/{ward_id}` (soft-deletes ward by setting `is_active = 0` and logs to audit log)
4. **Seed Script:** Updated `backend/app/seed.py` to seed default wards: "ANC", "MCH", "Emergency", "Theater", "Labour", "OPD", "IPD", "Pediatrics", "TB Clinic".
5. **Testing:** Added tests for schema validation, table existence, CRUD endpoints, and database seeding.

## Files Changed
- `backend/app/database.py`
- `backend/app/schemas.py`
- `backend/app/routers/config.py`
- `backend/app/seed.py`
- `tests/test_backend_api.py`
- `tests/test_database.py`

## Test Results
- Ran `pytest` across all test suites (`tests/test_backend_api.py`, `tests/test_database.py`, `tests/test_evaluator.py`, `tests/test_pdf_api.py`, `tests/test_pdf_generator.py`).
- Total: 29 passed, 0 failed.

## Commit
- `96f1f92 feat: add Wards configuration backend`
