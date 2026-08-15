import datetime, sqlite3
from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/patients", tags=["Patients & Reports"])

class PatientCreate(BaseModel):
    patient_number: str
    full_name: str
    age_years: Optional[int] = None
    date_of_birth: Optional[str] = None
    sex: str # Male / Female
    phone: Optional[str] = None

class TestOrderCreate(BaseModel):
    patient_id: int
    test_id: int
    sample_id: Optional[str] = None
    sample_type: Optional[str] = "Venous Blood"
    ref_doctor_ward: Optional[str] = "OPD"

class ParameterResultItem(BaseModel):
    parameter_id: int
    result_value: str
    is_positive: Optional[bool] = False

class TestResultCreate(BaseModel):
    order_id: int
    result_value: Optional[str] = None
    is_positive: Optional[bool] = False
    parameter_results: Optional[List[ParameterResultItem]] = None

@router.get("")
def list_patients(query: Optional[str] = None, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    if query:
        q = f"%{query}%"
        cur.execute("SELECT * FROM patients WHERE full_name LIKE ? OR patient_number LIKE ? OR phone LIKE ? ORDER BY id DESC LIMIT 50", (q, q, q))
    else:
        cur.execute("SELECT * FROM patients ORDER BY id DESC LIMIT 50")
    return [dict(r) for r in cur.fetchall()]

@router.post("")
def create_patient(req: PatientCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE patient_number = ?", (req.patient_number,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Patient number already exists")
    
    cur.execute("""
        INSERT INTO patients (patient_number, full_name, date_of_birth, sex, phone)
        VALUES (?, ?, ?, ?, ?)
    """, (req.patient_number, req.full_name, req.date_of_birth, req.sex, req.phone))
    
    pid = cur.lastrowid
    conn.commit()
    return {"status": "created", "patient_id": pid}

@router.post("/orders")
def create_order(req: TestOrderCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE id = ?", (req.patient_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Patient not found")
        
    cur.execute("SELECT id FROM tests WHERE id = ?", (req.test_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Test not found")

    cur.execute("""
        INSERT INTO test_orders (patient_id, test_id, sample_id, ordered_by_user_id, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (req.patient_id, req.test_id, req.sample_id, current_user["id"]))
    
    oid = cur.lastrowid
    conn.commit()
    return {"status": "ordered", "order_id": oid}

def increment_daily_entry(cur: sqlite3.Cursor, entry_date: str, test_id: int, is_positive: bool, user_id: int):
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("SELECT id, is_tracked, parent_rollup_id FROM tests WHERE id = ?", (test_id,))
    t_obj = cur.fetchone()
    if not t_obj:
        return

    is_tr = bool(t_obj["is_tracked"])
    parent_id = t_obj["parent_rollup_id"]

    cur.execute("SELECT done, positive FROM daily_entries WHERE entry_date = ? AND test_id = ?", (entry_date, test_id))
    existing = cur.fetchone()

    if existing:
        new_done = existing["done"] + 1
        new_pos = existing["positive"]
        if is_tr:
            curr_pos = new_pos if new_pos is not None else 0
            new_pos = curr_pos + (1 if is_positive else 0)
        cur.execute("""
            UPDATE daily_entries
            SET done = ?, positive = ?, updated_by_user_id = ?, updated_at = ?
            WHERE entry_date = ? AND test_id = ?
        """, (new_done, new_pos, user_id, now_str, entry_date, test_id))
    else:
        new_pos = (1 if is_positive else 0) if is_tr else None
        cur.execute("""
            INSERT INTO daily_entries (entry_date, test_id, done, positive, entered_by_user_id, entered_at)
            VALUES (?, ?, 1, ?, ?, ?)
        """, (entry_date, test_id, new_pos, user_id, now_str))

    # HIV Rapid Testing Algorithm Rollup (e.g. Determine -> HTS master count)
    if parent_id:
        increment_daily_entry(cur, entry_date, parent_id, is_positive, user_id)

@router.post("/results")
def enter_result(req: TestResultCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, patient_id, test_id FROM test_orders WHERE id = ?", (req.order_id,))
    order = cur.fetchone()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    overall_positive = req.is_positive or False

    # Insert main result or parameter results
    if req.parameter_results:
        for pr in req.parameter_results:
            if pr.is_positive:
                overall_positive = True
            cur.execute("""
                INSERT INTO test_results (order_id, parameter_id, result_value, is_positive, entered_by_user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (req.order_id, pr.parameter_id, pr.result_value, pr.is_positive, current_user["id"]))
    else:
        cur.execute("SELECT id FROM test_results WHERE order_id = ? AND parameter_id IS NULL", (req.order_id,))
        res_row = cur.fetchone()
        if res_row:
            cur.execute("""
                UPDATE test_results
                SET result_value = ?, is_positive = ?, entered_by_user_id = ?, verified_at = ?
                WHERE id = ?
            """, (req.result_value, req.is_positive, current_user["id"], now_str, res_row["id"]))
        else:
            cur.execute("""
                INSERT INTO test_results (order_id, parameter_id, result_value, is_positive, entered_by_user_id)
                VALUES (?, NULL, ?, ?, ?)
            """, (req.order_id, req.result_value, req.is_positive, current_user["id"]))

    cur.execute("UPDATE test_orders SET status = 'completed' WHERE id = ?", (req.order_id,))

    # Auto-increment DailyEntry counts (with HIV algorithm rollup support)
    increment_daily_entry(cur, today_str, order["test_id"], overall_positive, current_user["id"])

    conn.commit()
    return {"status": "result_saved", "order_id": req.order_id, "auto_incremented_daily_log": True}

@router.get("/report/{order_id}")
def get_printable_patient_report(order_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            o.id as order_id, o.sample_id, o.ordered_at, o.status,
            p.patient_number, p.full_name as patient_name, p.date_of_birth, p.sex, p.phone,
            t.name as test_name, t.is_tracked, s.name as section_name,
            u.full_name as technician_name
        FROM test_orders o
        JOIN patients p ON o.patient_id = p.id
        JOIN tests t ON o.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        LEFT JOIN users u ON o.ordered_by_user_id = u.id
        WHERE o.id = ?
    """, (order_id,))
    
    order_info = cur.fetchone()
    if not order_info:
        raise HTTPException(status_code=404, detail="Patient report order not found")

    cur.execute("""
        SELECT r.id, r.parameter_id, tp.parameter_name, tp.unit, tp.ref_range, r.result_value, r.is_positive
        FROM test_results r
        LEFT JOIN test_parameters tp ON r.parameter_id = tp.id
        WHERE r.order_id = ?
        ORDER BY tp.sort_order, r.id
    """, (order_id,))
    
    results = [dict(r) for r in cur.fetchall()]
    
    data = dict(order_info)
    data["results"] = results
    return data

@router.get("/{patient_id}/orders")
def get_patient_orders(patient_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            o.id as order_id, o.sample_id, o.ordered_at, o.status,
            t.id as test_id, t.name as test_name, t.is_tracked, s.name as section_name,
            u.full_name as technician_name
        FROM test_orders o
        JOIN tests t ON o.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        LEFT JOIN users u ON o.ordered_by_user_id = u.id
        WHERE o.patient_id = ?
        ORDER BY o.id DESC
    """, (patient_id,))
    
    orders = [dict(r) for r in cur.fetchall()]
    
    for o in orders:
        cur.execute("""
            SELECT r.id, r.parameter_id, tp.parameter_name, tp.unit, tp.ref_range, r.result_value, r.is_positive
            FROM test_results r
            LEFT JOIN test_parameters tp ON r.parameter_id = tp.id
            WHERE r.order_id = ?
            ORDER BY tp.sort_order, r.id
        """, (o["order_id"],))
        o["results"] = [dict(r) for r in cur.fetchall()]
        
    return orders

