import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from ..schemas import (
    TestCreate, TestResponse, WardCreate, WardUpdate, WardResponse, 
    ClinicianCreate, ClinicianUpdate, ClinicianResponse,
    ReferenceRangeCreate, ReferenceRangeUpdate, ReferenceRangeResponse
)
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
    cur.execute("SELECT id, test_id, parameter_name, unit, secondary_unit, ref_range, sort_order, options FROM test_parameters WHERE test_id = ? ORDER BY sort_order, id", (test_id,))
    return [dict(r) for r in cur.fetchall()]

@router.get("/tests/{test_id}/children")
def get_test_children(test_id: int, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Return all active child sub-parameters of a panel test, ordered by sort_order."""
    cur = conn.cursor()
    cur.execute(
        """SELECT id, name, section_id, is_tracked, parent_rollup_id, sort_order,
                  result_type, default_unit, secondary_unit, options
           FROM tests
           WHERE parent_rollup_id = ? AND is_active = 1
           ORDER BY sort_order, id""",
        (test_id,)
    )
    return [dict(r) for r in cur.fetchall()]


@router.post("/tests")
def create_test(req: TestCreate, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id FROM sections WHERE id = ?", (req.section_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=400, detail="Invalid section ID")
    
    if req.is_tracked is None:
        effective_tracked = 1 if req.result_type in ("qualitative", "semi_quantitative", "options", "panel") else 0
    else:
        effective_tracked = 1 if req.is_tracked else 0

    cur.execute(
        "INSERT INTO tests (name, section_id, is_tracked, sort_order, result_type, default_unit, options, parent_rollup_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (req.name, req.section_id, effective_tracked, req.sort_order, req.result_type, req.default_unit, req.options, req.parent_rollup_id)
    )
    tid = cur.lastrowid
    conn.commit()
    
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "create_test", f"Created test '{req.name}'"))
    conn.commit()
    
    return {"id": tid, "name": req.name, "section_id": req.section_id, "is_tracked": bool(effective_tracked), "result_type": req.result_type, "default_unit": req.default_unit, "options": req.options, "parent_rollup_id": req.parent_rollup_id}
    

@router.put("/tests/{test_id}", response_model=TestResponse)
def update_test(test_id: int, req: TestCreate, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT id FROM tests WHERE id = ?", (test_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Test not found")
        
    if req.is_tracked is None:
        effective_tracked = 1 if req.result_type in ("qualitative", "semi_quantitative", "options", "panel") else 0
    else:
        effective_tracked = 1 if req.is_tracked else 0

    cur.execute("""
        UPDATE tests
        SET name = ?, section_id = ?, is_tracked = ?, result_type = ?, default_unit = ?, options = ?, parent_rollup_id = ?
        WHERE id = ?
    """, (req.name, req.section_id, effective_tracked, req.result_type, req.default_unit, req.options, req.parent_rollup_id, test_id))
    
    conn.commit()
    return TestResponse(
        id=test_id, name=req.name, section_id=req.section_id, 
        is_tracked=bool(effective_tracked), sort_order=req.sort_order, is_active=True,
        result_type=req.result_type, default_unit=req.default_unit, options=req.options,
        parent_rollup_id=req.parent_rollup_id
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


# Reference Ranges Configuration
@router.get("/reference-ranges", response_model=List[ReferenceRangeResponse])
def get_reference_ranges(conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, test_id, parameter_name, age_min, age_max, sex, normal_min, normal_max, critical_min, critical_max, sanity_min, sanity_max, plausible_min, plausible_max, unit
        FROM reference_ranges
        ORDER BY parameter_name ASC, age_min ASC, id ASC
    """)
    return [dict(r) for r in cur.fetchall()]


@router.post("/reference-ranges", response_model=ReferenceRangeResponse)
def create_reference_range(req: ReferenceRangeCreate, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    param_name = req.parameter_name.strip()
    if not param_name:
        raise HTTPException(status_code=400, detail="Parameter name cannot be empty")
    
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reference_ranges (test_id, parameter_name, age_min, age_max, sex, normal_min, normal_max, critical_min, critical_max, sanity_min, sanity_max, plausible_min, plausible_max, unit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.test_id, param_name, req.age_min if req.age_min is not None else 0, req.age_max if req.age_max is not None else 999, req.sex, req.normal_min, req.normal_max, req.critical_min, req.critical_max, req.sanity_min, req.sanity_max, req.plausible_min, req.plausible_max, req.unit))
    rid = cur.lastrowid
    conn.commit()

    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "create_reference_range", f"Created reference range rule ID {rid} for '{param_name}'"))
    conn.commit()

    return ReferenceRangeResponse(
        id=rid, test_id=req.test_id, parameter_name=param_name,
        age_min=req.age_min if req.age_min is not None else 0,
        age_max=req.age_max if req.age_max is not None else 999,
        sex=req.sex, normal_min=req.normal_min, normal_max=req.normal_max,
        critical_min=req.critical_min, critical_max=req.critical_max,
        sanity_min=req.sanity_min, sanity_max=req.sanity_max,
        plausible_min=req.plausible_min, plausible_max=req.plausible_max,
        unit=req.unit
    )


@router.put("/reference-ranges/{range_id}", response_model=ReferenceRangeResponse)
def update_reference_range(range_id: int, req: ReferenceRangeUpdate, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id, test_id, parameter_name, age_min, age_max, sex, normal_min, normal_max, critical_min, critical_max, sanity_min, sanity_max, plausible_min, plausible_max, unit FROM reference_ranges WHERE id = ?", (range_id,))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Reference range not found")

    new_test_id = req.test_id if req.test_id is not None else existing["test_id"]
    new_param = req.parameter_name.strip() if req.parameter_name is not None else existing["parameter_name"]
    new_age_min = req.age_min if req.age_min is not None else existing["age_min"]
    new_age_max = req.age_max if req.age_max is not None else existing["age_max"]
    new_sex = req.sex if req.sex is not None else existing["sex"]
    new_norm_min = req.normal_min if req.normal_min is not None else existing["normal_min"]
    new_norm_max = req.normal_max if req.normal_max is not None else existing["normal_max"]
    new_crit_min = req.critical_min if req.critical_min is not None else existing["critical_min"]
    new_crit_max = req.critical_max if req.critical_max is not None else existing["critical_max"]
    new_sanity_min = req.sanity_min if req.sanity_min is not None else existing["sanity_min"]
    new_sanity_max = req.sanity_max if req.sanity_max is not None else existing["sanity_max"]
    new_plausible_min = req.plausible_min if req.plausible_min is not None else existing["plausible_min"]
    new_plausible_max = req.plausible_max if req.plausible_max is not None else existing["plausible_max"]
    new_unit = req.unit if req.unit is not None else existing["unit"]

    cur.execute("""
        UPDATE reference_ranges
        SET test_id = ?, parameter_name = ?, age_min = ?, age_max = ?, sex = ?, normal_min = ?, normal_max = ?, critical_min = ?, critical_max = ?, sanity_min = ?, sanity_max = ?, plausible_min = ?, plausible_max = ?, unit = ?
        WHERE id = ?
    """, (new_test_id, new_param, new_age_min, new_age_max, new_sex, new_norm_min, new_norm_max, new_crit_min, new_crit_max, new_sanity_min, new_sanity_max, new_plausible_min, new_plausible_max, new_unit, range_id))
    conn.commit()

    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "update_reference_range", f"Updated reference range rule ID {range_id} for '{new_param}'"))
    conn.commit()

    return ReferenceRangeResponse(
        id=range_id, test_id=new_test_id, parameter_name=new_param,
        age_min=new_age_min, age_max=new_age_max, sex=new_sex,
        normal_min=new_norm_min, normal_max=new_norm_max,
        critical_min=new_crit_min, critical_max=new_crit_max,
        sanity_min=new_sanity_min, sanity_max=new_sanity_max,
        plausible_min=new_plausible_min, plausible_max=new_plausible_max,
        unit=new_unit
    )


@router.delete("/reference-ranges/{range_id}")
def delete_reference_range(range_id: int, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id, parameter_name FROM reference_ranges WHERE id = ?", (range_id,))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Reference range not found")

    cur.execute("DELETE FROM reference_ranges WHERE id = ?", (range_id,))
    conn.commit()

    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "delete_reference_range", f"Deleted reference range rule ID {range_id} ('{existing['parameter_name']}')"))
    conn.commit()
    return {"status": "deleted"}


