### Task 2: Backend Wards Configuration & Seed Updates
**Files:**
- Modify: ackend/app/database.py
- Modify: ackend/app/schemas.py
- Modify: ackend/app/routers/config.py
- Modify: ackend/app/seed.py

- [ ] **Step 1: Add Wards to Database**
In ackend/app/database.py, inside init_db(), add a wards table:
`sql
CREATE TABLE IF NOT EXISTS wards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1
)
`

- [ ] **Step 2: Add Ward Schemas**
In ackend/app/schemas.py, add schemas for wards:
`python
class WardBase(BaseModel):
    name: str

class WardCreate(WardBase):
    pass

class WardResponse(WardBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
`

- [ ] **Step 3: Implement Ward API endpoints**
In ackend/app/routers/config.py, implement CRUD endpoints for wards:
GET /wards, POST /wards (creates a ward), PUT /wards/{ward_id} (updates name/is_active), DELETE /wards/{ward_id} (sets is_active=0).

- [ ] **Step 4: Update Seed Script**
In ackend/app/seed.py, after creating sections, seed Wards:
"ANC", "MCH", "Emergency", "Theater", "Labour", "OPD", "IPD", "Pediatrics", "TB Clinic".
`python
    wards = ["ANC", "MCH", "Emergency", "Theater", "Labour", "OPD", "IPD", "Pediatrics", "TB Clinic"]
    for w_name in wards:
        cur.execute("INSERT OR IGNORE INTO wards (name) VALUES (?)", (w_name,))
`

- [ ] **Step 5: Test & Commit**
Verify via python -m pytest tests/test_backend_api.py.
Commit the changes.
