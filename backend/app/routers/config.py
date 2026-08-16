import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from ..schemas import TestCreate
from ..models import User
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/api/config", tags=["Configuration"])

@router.get("/sections")
def get_sections(conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, name, sort_order FROM sections ORDER BY sort_order, id")
    return [dict(r) for r in cur.fetchall()]

@router.get("/tests")
def get_tests(conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, name, section_id, is_tracked, parent_rollup_id, is_active, sort_order FROM tests WHERE is_active = 1 ORDER BY section_id, sort_order, id")
    return [dict(r) for r in cur.fetchall()]

@router.get("/tests/{test_id}/parameters")
def get_test_parameters(test_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, test_id, parameter_name, unit, ref_range, sort_order FROM test_parameters WHERE test_id = ? ORDER BY sort_order, id", (test_id,))
    return [dict(r) for r in cur.fetchall()]

@router.post("/tests")
def create_test(req: TestCreate, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id FROM sections WHERE id = ?", (req.section_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=400, detail="Invalid section ID")
    
    cur.execute(
        "INSERT INTO tests (name, section_id, is_tracked, sort_order) VALUES (?, ?, ?, ?)",
        (req.name, req.section_id, 1 if req.is_tracked else 0, req.sort_order)
    )
    tid = cur.lastrowid
    conn.commit()
    
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "create_test", f"Created test '{req.name}'"))
    conn.commit()
    
    return {"id": tid, "name": req.name, "section_id": req.section_id, "is_tracked": req.is_tracked}
    
@router.post("/results")
def enter_result(req: TestCreate, current_user: User = Depends(get_current_user)):
    print(current_user.full_name)

@router.delete("/tests/{test_id}")
def delete_test(test_id: int, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("UPDATE tests SET is_active = 0 WHERE id = ?", (test_id,))
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "delete_test", f"Soft deleted test ID {test_id}"))
    conn.commit()
    return {"status": "deleted"}
