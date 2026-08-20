import datetime, sqlite3, logging
from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from ..database import get_db
from ..auth import get_current_user
from ..schemas import VisitCreate, TestResultCreate, ParameterResultItem, AddOrdersRequest
from ..evaluator import evaluate_result

logger = logging.getLogger("amh_clients")

router = APIRouter(tags=["Clients, Visits & Clinicians"])

class VisitEdit(BaseModel):
    age_years: float
    sex: str
    ward_of_origin: str

class ClientCreate(BaseModel):
    client_number: Optional[str] = None
    full_name: str
    age_string: str
    age_category: str
    sex: str # Male / Female
    phone: Optional[str] = None

class TestOrderCreate(BaseModel):
    client_id: Optional[int] = None
    visit_id: Optional[int] = None
    test_id: int
    sample_id: Optional[str] = None
    sample_type: Optional[str] = "Venous Blood"
    ref_doctor_ward: Optional[str] = "OPD"
    order_category: Optional[str] = "in-house"

@router.get("/api/clinicians")
def list_clinicians(conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' requested clinicians list")
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM clinicians WHERE is_active = 1 ORDER BY name ASC")
    clinicians = [dict(r) for r in cur.fetchall()]
    return clinicians

@router.get("/api/clients")
def list_clients(query: Optional[str] = None, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' requested clients list (query='{query or ''}')")
    cur = conn.cursor()
    if query:
        q = f"%{query}%"
        cur.execute("SELECT * FROM clients WHERE full_name LIKE ? OR client_number LIKE ? OR phone LIKE ? ORDER BY id DESC LIMIT 50", (q, q, q))
    else:
        cur.execute("SELECT * FROM clients ORDER BY id DESC LIMIT 50")
    results = [dict(r) for r in cur.fetchall()]
    logger.info(f"Returned {len(results)} clients")
    return results

import re

def parse_age_string(s: str) -> float:
    if not s: return 0.0
    s = s.lower().strip()
    if "/365" in s:
        try: return float(s.replace("/365", "").strip()) / 365.0
        except ValueError: pass
    if "/12" in s:
        parts = s.split()
        if len(parts) == 2:
            try: return float(parts[0]) + (float(parts[1].replace("/12", "")) / 12.0)
            except ValueError: pass
        else:
            try: return float(s.replace("/12", "").strip()) / 12.0
            except ValueError: pass
    if s.endswith("d"):
        try: return float(s.replace("d", "").strip()) / 365.0
        except ValueError: pass
    if s.endswith("m"):
        try: return float(s.replace("m", "").strip()) / 12.0
        except ValueError: pass
    m = re.match(r"(\d+)y\s+(\d+)m", s)
    if m:
        return float(m.group(1)) + (float(m.group(2)) / 12.0)
    try: return float(s.replace("y", "").strip())
    except ValueError: return 0.0

@router.post("/api/clients")
def create_client(req: ClientCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' is creating client: '{req.full_name}'")
    cur = conn.cursor()
    
    parsed_age = parse_age_string(req.age_string)

    today = datetime.date.today()
    yy_str = today.strftime("%y")
    seq_name = f"client_number_{yy_str}"
    cur.execute("INSERT OR IGNORE INTO sequence_tracker (seq_name, last_value) VALUES (?, 0)", (seq_name,))
    cur.execute("UPDATE sequence_tracker SET last_value = last_value + 1 WHERE seq_name = ?", (seq_name,))
    cur.execute("SELECT last_value FROM sequence_tracker WHERE seq_name = ?", (seq_name,))
    seq_row = cur.fetchone()
    seq_val = seq_row["last_value"] if seq_row else 1
    generated_client_number = f"AMH-C{yy_str}-{seq_val:04d}"
    
    cur.execute("""
        INSERT INTO clients (client_number, full_name, age_years, age_category, sex, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (generated_client_number, req.full_name, parsed_age, req.age_category, req.sex, req.phone))
    
    pid = cur.lastrowid
    conn.commit()
    logger.info(f"Client created successfully: ID {pid}, Client Number {generated_client_number}")
    return {"status": "created", "client_id": pid, "client_number": generated_client_number}

@router.post("/api/visits")
def create_visit(req: VisitCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' is creating visit for client ID {req.client_id} with {len(req.test_ids)} tests")
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM clients WHERE id = ?", (req.client_id,))
    if not cur.fetchone():
        logger.warning(f"Visit creation failed: client ID {req.client_id} not found")
        raise HTTPException(status_code=404, detail="Client not found")
        
    if req.clinician_id:
        cur.execute("SELECT id FROM clinicians WHERE id = ?", (req.clinician_id,))
        if not cur.fetchone():
            logger.warning(f"Visit creation failed: clinician ID {req.clinician_id} not found")
            raise HTTPException(status_code=400, detail="Clinician not found")
            
    if not req.test_ids:
        raise HTTPException(status_code=400, detail="At least one test ID must be provided")
        
    for tid in req.test_ids:
        cur.execute("SELECT id FROM tests WHERE id = ?", (tid,))
        if not cur.fetchone():
            logger.warning(f"Visit creation failed: test ID {tid} not found")
            raise HTTPException(status_code=404, detail=f"Test ID {tid} not found")
            
    cur.execute("""
        INSERT INTO visits (client_id, clinician_id, ward_of_origin)
        VALUES (?, ?, ?)
    """, (req.client_id, req.clinician_id, req.ward_of_origin))
    visit_id = cur.lastrowid
    
    for tid in req.test_ids:
        cur.execute("""
            INSERT INTO test_orders (visit_id, test_id, sample_id, ordered_by_user_id, status, order_category)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (visit_id, tid, req.sample_id, current_user["id"], req.order_category))
        
    conn.commit()
    logger.info(f"Visit created successfully: visit_id={visit_id}")
    return {"status": "created", "visit_id": visit_id}

@router.put("/api/visits/{visit_id}")
def update_visit(visit_id: int, req: VisitEdit, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' is updating visit ID {visit_id}")
    cur = conn.cursor()
    
    cur.execute("SELECT client_id FROM visits WHERE id = ?", (visit_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Visit not found")
        
    client_id = row["client_id"]
    
    # Update visit
    cur.execute("UPDATE visits SET ward_of_origin = ? WHERE id = ?", (req.ward_of_origin, visit_id))
    
    # Update client age and sex
    cur.execute("UPDATE clients SET age_years = ?, sex = ? WHERE id = ?", (req.age_years, req.sex, client_id))
    
    conn.commit()
    return {"status": "updated", "visit_id": visit_id}

@router.post("/api/visits/{visit_id}/orders")
def add_orders_to_visit(visit_id: int, req: AddOrdersRequest, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' is adding {len(req.test_ids)} orders to visit ID {visit_id}")
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM visits WHERE id = ?", (visit_id,))
    if not cur.fetchone():
        logger.warning(f"Add orders failed: visit ID {visit_id} not found")
        raise HTTPException(status_code=404, detail="Visit not found")
        
    if not req.test_ids:
        raise HTTPException(status_code=400, detail="At least one test ID must be provided")
        
    for tid in req.test_ids:
        cur.execute("SELECT id FROM tests WHERE id = ?", (tid,))
        if not cur.fetchone():
            logger.warning(f"Add orders failed: test ID {tid} not found")
            raise HTTPException(status_code=404, detail=f"Test ID {tid} not found")
            
        # Enforce Single Order Logic
        cur.execute("""
            SELECT o.id, tr.result_value 
            FROM test_orders o
            LEFT JOIN test_results tr ON o.id = tr.order_id
            WHERE o.visit_id = ? AND o.test_id = ?
        """, (visit_id, tid))
        previous_orders = cur.fetchall()
        if previous_orders:
            can_order = True
            for r in previous_orders:
                if r["result_value"] != "Invalid":
                    can_order = False
                    break
            if not can_order:
                raise HTTPException(status_code=400, detail=f"Test ID {tid} already ordered for this visit and is not Invalid.")
            
    added_order_ids = []
    order_cat = req.order_category if hasattr(req, 'order_category') and req.order_category else 'in-house'
    for tid in req.test_ids:
        cur.execute("""
            INSERT INTO test_orders (visit_id, test_id, sample_id, ordered_by_user_id, status, order_category)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (visit_id, tid, req.sample_id, current_user["id"], order_cat))
        added_order_ids.append(cur.lastrowid)
        
    conn.commit()
    logger.info(f"Successfully added orders {added_order_ids} to visit {visit_id}")
    return {"status": "orders_added", "visit_id": visit_id, "order_ids": added_order_ids}

@router.delete("/api/orders/{order_id}")
def delete_order(order_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' is deleting order ID {order_id}")
    cur = conn.cursor()
    cur.execute("SELECT status FROM test_orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending orders can be removed")
    
    cur.execute("DELETE FROM test_orders WHERE id = ?", (order_id,))
    conn.commit()
    logger.info(f"Successfully deleted order {order_id}")
    return {"status": "deleted", "order_id": order_id}

@router.post("/api/clients/orders")
@router.post("/api/orders")
def create_order(req: TestOrderCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' is creating test order: client_id={req.client_id}, visit_id={req.visit_id}, test_id={req.test_id}")
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM tests WHERE id = ?", (req.test_id,))
    if not cur.fetchone():
        logger.warning(f"Order creation failed: test ID {req.test_id} not found")
        raise HTTPException(status_code=404, detail="Test not found")

    visit_id = req.visit_id
    if not visit_id:
        if not req.client_id:
            raise HTTPException(status_code=400, detail="Either visit_id or client_id must be provided")
        cur.execute("SELECT id FROM clients WHERE id = ?", (req.client_id,))
        if not cur.fetchone():
            logger.warning(f"Order creation failed: client ID {req.client_id} not found")
            raise HTTPException(status_code=404, detail="Client not found")
        cur.execute("""
            INSERT INTO visits (client_id, ward_of_origin)
            VALUES (?, ?)
        """, (req.client_id, req.ref_doctor_ward))
        visit_id = cur.lastrowid
    else:
        # Enforce Single Order Logic
        cur.execute("""
            SELECT o.id, tr.result_value 
            FROM test_orders o
            LEFT JOIN test_results tr ON o.id = tr.order_id
            WHERE o.visit_id = ? AND o.test_id = ?
        """, (visit_id, req.test_id))
        previous_orders = cur.fetchall()
        if previous_orders:
            can_order = True
            for r in previous_orders:
                if r["result_value"] != "Invalid":
                    can_order = False
                    break
            if not can_order:
                raise HTTPException(status_code=400, detail=f"Test ID {req.test_id} already ordered for this visit and is not Invalid.")

    order_cat = req.order_category if hasattr(req, 'order_category') and req.order_category else 'in-house'
    cur.execute("""
        INSERT INTO test_orders (visit_id, test_id, sample_id, ordered_by_user_id, status, order_category)
        VALUES (?, ?, ?, ?, 'pending', ?)
    """, (visit_id, req.test_id, req.sample_id, current_user["id"], order_cat))
    
    oid = cur.lastrowid
    conn.commit()
    logger.info(f"Order created successfully: order_id={oid}")
    return {"status": "ordered", "order_id": oid, "visit_id": visit_id}

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

@router.post("/api/results")
@router.post("/api/clients/results")
def enter_result(req: TestResultCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info(f"User '{current_user['username']}' is entering result for order ID {req.order_id}")
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            o.id as order_id, o.visit_id, o.test_id,
            t.name as test_name, t.is_tracked,
            c.date_of_birth, c.sex
        FROM test_orders o
        JOIN tests t ON o.test_id = t.id
        LEFT JOIN visits v ON o.visit_id = v.id
        LEFT JOIN clients c ON v.client_id = c.id
        WHERE o.id = ?
    """, (req.order_id,))
    order = cur.fetchone()
    if not order:
        logger.warning(f"Result entry failed: order ID {req.order_id} not found")
        raise HTTPException(status_code=404, detail="Order not found")

    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")

    dob_str = order["date_of_birth"]
    dob = None
    if dob_str:
        try:
            dob = datetime.datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
        except ValueError:
            dob = None
    sex = order["sex"] or ""
    test_name = order["test_name"] or ""

    overall_positive = False

    # Insert main result or parameter results with verified_at and verified_by_user_id
    if req.parameter_results:
        for pr in req.parameter_results:
            cur.execute("SELECT parameter_name FROM test_parameters WHERE id = ?", (pr.parameter_id,))
            param_row = cur.fetchone()
            param_name = param_row["parameter_name"] if param_row else ""

            eval_dict = evaluate_result(param_name, pr.result_value, dob, sex, today)
            pr_is_positive = eval_dict.get("is_abnormal", False)

            if pr.result_value:
                pr_val_lower = pr.result_value.strip().lower()
                if pr_val_lower in ["positive", "abnormal", "reactive"] or pr_val_lower.startswith("positive") or pr_val_lower.startswith("reactive"):
                    pr_is_positive = True

            if pr_is_positive:
                overall_positive = True

            cur.execute("SELECT id FROM test_results WHERE order_id = ? AND parameter_id = ?", (req.order_id, pr.parameter_id))
            res_row = cur.fetchone()
            if res_row:
                cur.execute("""
                    UPDATE test_results
                    SET result_value = ?, is_positive = ?, entered_by_user_id = COALESCE(entered_by_user_id, ?), entered_at = COALESCE(entered_at, ?), verified_by_user_id = ?, verified_at = ?
                    WHERE id = ?
                """, (pr.result_value, pr_is_positive, current_user["id"], now_str, current_user["id"], now_str, res_row["id"]))
            else:
                cur.execute("""
                    INSERT INTO test_results (order_id, parameter_id, result_value, is_positive, entered_by_user_id, entered_at, verified_by_user_id, verified_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (req.order_id, pr.parameter_id, pr.result_value, pr_is_positive, current_user["id"], now_str, current_user["id"], now_str))
    else:
        eval_dict = evaluate_result(test_name, req.result_value, dob, sex, today)
        is_positive = eval_dict.get("is_abnormal", False)

        if req.result_value:
            val_lower = req.result_value.strip().lower()
            if val_lower in ["positive", "abnormal", "reactive"] or val_lower.startswith("positive") or val_lower.startswith("reactive"):
                is_positive = True

        overall_positive = is_positive

        cur.execute("SELECT id FROM test_results WHERE order_id = ? AND parameter_id IS NULL", (req.order_id,))
        res_row = cur.fetchone()
        if res_row:
            cur.execute("""
                UPDATE test_results
                SET result_value = ?, is_positive = ?, entered_by_user_id = COALESCE(entered_by_user_id, ?), entered_at = COALESCE(entered_at, ?), verified_by_user_id = ?, verified_at = ?
                WHERE id = ?
            """, (req.result_value, is_positive, current_user["id"], now_str, current_user["id"], now_str, res_row["id"]))
        else:
            cur.execute("""
                INSERT INTO test_results (order_id, parameter_id, result_value, is_positive, entered_by_user_id, entered_at, verified_by_user_id, verified_at)
                VALUES (?, NULL, ?, ?, ?, ?, ?, ?)
            """, (req.order_id, req.result_value, is_positive, current_user["id"], now_str, current_user["id"], now_str))

    cur.execute("UPDATE test_orders SET status = 'completed' WHERE id = ?", (req.order_id,))

    # Auto-increment DailyEntry counts (with HIV algorithm rollup support)
    increment_daily_entry(cur, today_str, order["test_id"], overall_positive, current_user["id"])

    # Sequential Lab Number Assignment on the parent visit
    assigned_lab_number = None
    visit_id = order["visit_id"]
    if visit_id:
        cur.execute("SELECT id, lab_number FROM visits WHERE id = ?", (visit_id,))
        v_row = cur.fetchone()
        if v_row:
            if not v_row["lab_number"]:
                today = datetime.date.today()
                yy_str = today.strftime("%y")
                m_str = str(today.month)  # Non-zero-padded month (e.g. 8 not 08)
                ym_key = f"{yy_str}_{m_str}"
                seq_name = f"lab_number_{ym_key}"
                cur.execute("INSERT OR IGNORE INTO sequence_tracker (seq_name, last_value) VALUES (?, 0)", (seq_name,))
                cur.execute("UPDATE sequence_tracker SET last_value = last_value + 1 WHERE seq_name = ?", (seq_name,))
                cur.execute("SELECT last_value FROM sequence_tracker WHERE seq_name = ?", (seq_name,))
                seq_row = cur.fetchone()
                seq_val = seq_row["last_value"] if seq_row else 1
                assigned_lab_number = f"AMH-{yy_str}-{m_str}-{seq_val:03d}"
                cur.execute("UPDATE visits SET lab_number = ? WHERE id = ?", (assigned_lab_number, visit_id))
            else:
                assigned_lab_number = v_row["lab_number"]

    conn.commit()
    logger.info(f"Result saved successfully for order ID {req.order_id}, lab_number={assigned_lab_number}")
    return {"status": "result_saved", "order_id": req.order_id, "auto_incremented_daily_log": True, "lab_number": assigned_lab_number}


@router.get("/api/clients/report/{order_id}")
@router.get("/api/report/{order_id}")
def get_printable_client_report(order_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            o.id as order_id, o.sample_id, o.ordered_at, o.status,
            p.client_number, p.full_name as client_name, p.date_of_birth, p.sex, p.phone,
            v.id as visit_id, v.ward_of_origin, v.lab_number,
            c.name as clinician_name,
            t.name as test_name, t.is_tracked, s.name as section_name,
            u.full_name as technician_name
        FROM test_orders o
        JOIN visits v ON o.visit_id = v.id
        JOIN clients p ON v.client_id = p.id
        LEFT JOIN clinicians c ON v.clinician_id = c.id
        JOIN tests t ON o.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        LEFT JOIN users u ON o.ordered_by_user_id = u.id
        WHERE o.id = ?
    """, (order_id,))
    
    order_info = cur.fetchone()
    if not order_info:
        raise HTTPException(status_code=404, detail="Client report order not found")

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

@router.get("/api/clients/{client_id}/orders")
def get_client_orders(client_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            o.id as order_id, o.sample_id, o.ordered_at, o.status,
            o.visit_id, v.ward_of_origin, v.lab_number,
            t.id as test_id, t.name as test_name, t.is_tracked, s.name as section_name,
            u.full_name as technician_name
        FROM test_orders o
        JOIN visits v ON o.visit_id = v.id
        JOIN tests t ON o.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        LEFT JOIN users u ON o.ordered_by_user_id = u.id
        WHERE v.client_id = ?
        ORDER BY o.id DESC
    """, (client_id,))
    
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

@router.get("/api/clients/{client_id}/visits")
def get_client_visits(client_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            v.id as visit_id, v.ward_of_origin, v.lab_number, v.created_at,
            cl.name as clinician_name
        FROM visits v
        LEFT JOIN clinicians cl ON v.clinician_id = cl.id
        WHERE v.client_id = ?
        ORDER BY v.id DESC
    """, (client_id,))
    return [dict(r) for r in cur.fetchall()]


@router.get("/api/visits/{visit_id}")
def get_visit_details(visit_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            v.id as visit_id, v.ward_of_origin, v.lab_number, v.created_at,
            c.id as client_id, c.client_number, c.full_name, c.date_of_birth, c.age_years, c.sex, c.phone,
            cl.id as clinician_id, cl.name as clinician_name
        FROM visits v
        JOIN clients c ON v.client_id = c.id
        LEFT JOIN clinicians cl ON v.clinician_id = cl.id
        WHERE v.id = ?
    """, (visit_id,))
    visit_row = cur.fetchone()
    if not visit_row:
        raise HTTPException(status_code=404, detail="Visit not found")

    cur.execute("""
        SELECT 
            o.id as order_id, o.sample_id, o.ordered_at, o.status,
            t.id as test_id, t.name as test_name, t.is_tracked, s.name as section_name,
            u.full_name as ordered_by_name
        FROM test_orders o
        JOIN tests t ON o.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        LEFT JOIN users u ON o.ordered_by_user_id = u.id
        WHERE o.visit_id = ?
        ORDER BY o.id ASC
    """, (visit_id,))
    orders = [dict(r) for r in cur.fetchall()]

    for o in orders:
        cur.execute("""
            SELECT r.id, r.parameter_id, tp.parameter_name, tp.unit, tp.ref_range, r.result_value, r.is_positive,
                   r.entered_at, r.verified_at, u1.full_name as entered_by_name, u2.full_name as verified_by_name
            FROM test_results r
            LEFT JOIN test_parameters tp ON r.parameter_id = tp.id
            LEFT JOIN users u1 ON r.entered_by_user_id = u1.id
            LEFT JOIN users u2 ON r.verified_by_user_id = u2.id
            WHERE r.order_id = ?
            ORDER BY tp.sort_order, r.id
        """, (o["order_id"],))
        o["results"] = [dict(r) for r in cur.fetchall()]

    data = dict(visit_row)
    data["orders"] = orders
    return data

@router.delete("/api/visits/{visit_id}")
def delete_visit(visit_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete visits")
        
    logger.info(f"Admin '{current_user['username']}' is deleting visit ID {visit_id}")
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM visits WHERE id = ?", (visit_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Visit not found")
        
    # Find all test orders for this visit
    cur.execute("SELECT id FROM test_orders WHERE visit_id = ?", (visit_id,))
    orders = cur.fetchall()
    
    # Delete test results for these orders
    for o in orders:
        cur.execute("DELETE FROM test_results WHERE order_id = ?", (o["id"],))
        
    # Delete test orders
    cur.execute("DELETE FROM test_orders WHERE visit_id = ?", (visit_id,))
    
    # Delete visit
    cur.execute("DELETE FROM visits WHERE id = ?", (visit_id,))
    
    conn.commit()
    return {"status": "deleted"}
