import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from ..schemas import TestCreate, TestResponse, WardCreate, WardUpdate, WardResponse, ClinicianCreate, ClinicianUpdate, ClinicianResponse
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
    cur.execute("SELECT id, name, section_id, is_tracked, parent_rollup_id, ref_range, panic_value_low, panic_value_high, is_active, sort_order, result_type, default_unit, secondary_unit, options FROM tests WHERE is_active = 1 ORDER BY section_id, sort_order, id")
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
        "INSERT INTO tests (name, section_id, is_tracked, sort_order, result_type, default_unit, options) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (req.name, req.section_id, 1 if req.is_tracked else 0, req.sort_order, req.result_type, req.default_unit, req.options)
    )
    tid = cur.lastrowid
    conn.commit()
    
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "create_test", f"Created test '{req.name}'"))
    conn.commit()
    
    return {"id": tid, "name": req.name, "section_id": req.section_id, "is_tracked": req.is_tracked, "result_type": req.result_type, "default_unit": req.default_unit, "options": req.options}
    

@router.put("/tests/{test_id}", response_model=TestResponse)
def update_test(test_id: int, req: TestCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id FROM tests WHERE id = ?", (test_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Test not found")
        
    cur.execute("""
        UPDATE tests
        SET name = ?, section_id = ?, is_tracked = ?, result_type = ?, default_unit = ?, options = ?
        WHERE id = ?
    """, (req.name, req.section_id, 1 if req.is_tracked else 0, req.result_type, req.default_unit, req.options, test_id))
    
    conn.commit()
    return TestResponse(
        id=test_id, name=req.name, section_id=req.section_id, 
        is_tracked=req.is_tracked, sort_order=req.sort_order, is_active=True,
        result_type=req.result_type, default_unit=req.default_unit, options=req.options
    )

@router.delete("/tests/{test_id}")
def delete_test(test_id: int, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("UPDATE tests SET is_active = 0 WHERE id = ?", (test_id,))
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "delete_test", f"Soft deleted test ID {test_id}"))
    conn.commit()
    return {"status": "deleted"}

@router.get("/wards", response_model=List[WardResponse])
def get_wards(active_only: Optional[bool] = None, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    if active_only is True:
        cur.execute("SELECT id, name, is_active FROM wards WHERE is_active = 1 ORDER BY name ASC")
    elif active_only is False:
        cur.execute("SELECT id, name, is_active FROM wards WHERE is_active = 0 ORDER BY name ASC")
    else:
        cur.execute("SELECT id, name, is_active FROM wards ORDER BY name ASC")
    return [dict(r) for r in cur.fetchall()]

@router.post("/wards", response_model=WardResponse)
def create_ward(req: WardCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    name = req.name.strip() if req.name else ""
    if not name:
        raise HTTPException(status_code=400, detail="Ward name cannot be empty")
    cur = conn.cursor()
    cur.execute("SELECT id FROM wards WHERE LOWER(name) = LOWER(?)", (name,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Ward already exists")
    cur.execute("INSERT INTO wards (name, is_active) VALUES (?, 1)", (name,))
    wid = cur.lastrowid
    conn.commit()
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if user_id:
        conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user_id, "create_ward", f"Created ward '{name}'"))
        conn.commit()
    return WardResponse(id=wid, name=name, is_active=True)

@router.put("/wards/{ward_id}", response_model=WardResponse)
def update_ward(ward_id: int, req: WardUpdate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, name, is_active FROM wards WHERE id = ?", (ward_id,))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Ward not found")
    
    new_name = req.name.strip() if req.name is not None else existing["name"]
    if req.name is not None and not new_name:
        raise HTTPException(status_code=400, detail="Ward name cannot be empty")
        
    if req.name is not None and new_name.lower() != existing["name"].lower():
        cur.execute("SELECT id FROM wards WHERE LOWER(name) = LOWER(?) AND id != ?", (new_name, ward_id))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Ward with this name already exists")
            
    new_is_active = req.is_active if req.is_active is not None else bool(existing["is_active"])
    
    cur.execute("UPDATE wards SET name = ?, is_active = ? WHERE id = ?", (new_name, 1 if new_is_active else 0, ward_id))
    conn.commit()
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if user_id:
        conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user_id, "update_ward", f"Updated ward ID {ward_id} ({new_name})"))
        conn.commit()
    return WardResponse(id=ward_id, name=new_name, is_active=new_is_active)

@router.delete("/wards/{ward_id}")
def delete_ward(ward_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM wards WHERE id = ?", (ward_id,))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Ward not found")
    cur.execute("UPDATE wards SET is_active = 0 WHERE id = ?", (ward_id,))
    conn.commit()
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if user_id:
        conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user_id, "delete_ward", f"Soft deleted ward ID {ward_id} ({existing['name']})"))
        conn.commit()
    return {"status": "deleted"}

@router.get("/clinicians", response_model=List[ClinicianResponse])
def get_clinicians(active_only: Optional[bool] = None, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    if active_only is True:
        cur.execute("SELECT id, name, is_active, created_at FROM clinicians WHERE is_active = 1 ORDER BY name ASC")
    elif active_only is False:
        cur.execute("SELECT id, name, is_active, created_at FROM clinicians WHERE is_active = 0 ORDER BY name ASC")
    else:
        cur.execute("SELECT id, name, is_active, created_at FROM clinicians ORDER BY name ASC")
    return [dict(r) for r in cur.fetchall()]

@router.post("/clinicians", response_model=ClinicianResponse)
def create_clinician(req: ClinicianCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    name = req.name.strip() if req.name else ""
    if not name:
        raise HTTPException(status_code=400, detail="Clinician name cannot be empty")
    cur = conn.cursor()
    cur.execute("SELECT id FROM clinicians WHERE LOWER(name) = LOWER(?)", (name,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Clinician already exists")
    cur.execute("INSERT INTO clinicians (name, is_active) VALUES (?, 1)", (name,))
    cid = cur.lastrowid
    conn.commit()
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if user_id:
        conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user_id, "create_clinician", f"Created clinician '{name}'"))
        conn.commit()
    return ClinicianResponse(id=cid, name=name, is_active=True)

@router.put("/clinicians/{clinician_id}", response_model=ClinicianResponse)
def update_clinician(clinician_id: int, req: ClinicianUpdate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, name, is_active FROM clinicians WHERE id = ?", (clinician_id,))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Clinician not found")
    
    new_name = req.name.strip() if req.name is not None else existing["name"]
    if req.name is not None and not new_name:
        raise HTTPException(status_code=400, detail="Clinician name cannot be empty")
        
    if req.name is not None and new_name.lower() != existing["name"].lower():
        cur.execute("SELECT id FROM clinicians WHERE LOWER(name) = LOWER(?) AND id != ?", (new_name, clinician_id))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Clinician with this name already exists")
            
    new_is_active = req.is_active if req.is_active is not None else bool(existing["is_active"])
    
    cur.execute("UPDATE clinicians SET name = ?, is_active = ? WHERE id = ?", (new_name, 1 if new_is_active else 0, clinician_id))
    conn.commit()
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if user_id:
        conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user_id, "update_clinician", f"Updated clinician ID {clinician_id} ({new_name})"))
        conn.commit()
    return ClinicianResponse(id=clinician_id, name=new_name, is_active=new_is_active)

@router.delete("/clinicians/{clinician_id}")
def delete_clinician(clinician_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM clinicians WHERE id = ?", (clinician_id,))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Clinician not found")
    cur.execute("UPDATE clinicians SET is_active = 0 WHERE id = ?", (clinician_id,))
    conn.commit()
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if user_id:
        conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user_id, "delete_clinician", f"Soft deleted clinician ID {clinician_id} ({existing['name']})"))
        conn.commit()
    return {"status": "deleted"}


