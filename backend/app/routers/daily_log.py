import datetime, sqlite3
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from ..database import get_db
from ..schemas import DailyLogSaveRequest
from ..auth import get_current_user

router = APIRouter(prefix="/api/daily-log", tags=["Daily Log"])

@router.get("")
def get_daily_log(date_str: str = Query(..., alias="date"), conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        entry_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    cur = conn.cursor()
    cur.execute("SELECT id, name, sort_order FROM sections ORDER BY sort_order, id")
    sections = cur.fetchall()
    
    result_sections = []
    total_done_today = 0
    total_positive_today = 0
    total_rows_today = 0

    for sec in sections:
        cur.execute("SELECT id, name, is_tracked FROM tests WHERE section_id = ? AND is_active = 1 ORDER BY sort_order, id", (sec["id"],))
        tests = cur.fetchall()
        test_items = []
        
        for t in tests:
            cur.execute("SELECT done, positive, entered_by_user_id, updated_at FROM daily_entries WHERE entry_date = ? AND test_id = ?", (date_str, t["id"]))
            entry = cur.fetchone()
            
            done = entry["done"] if entry else 0
            pos = entry["positive"] if entry else None
            
            if done > 0 or (pos is not None and pos > 0):
                total_rows_today += 1
                total_done_today += done
                if pos is not None:
                    total_positive_today += pos

            test_items.append({
                "test_id": t["id"],
                "test_name": t["name"],
                "is_tracked": bool(t["is_tracked"]),
                "done": done,
                "positive": pos if t["is_tracked"] else None,
                "entered_by": entry["entered_by_user_id"] if entry else None,
                "updated_at": entry["updated_at"] if entry else None
            })
        
        result_sections.append({
            "section_id": sec["id"],
            "section_name": sec["name"],
            "tests": test_items
        })

    return {
        "entry_date": date_str,
        "sections": result_sections,
        "today_check": {
            "rows_logged": total_rows_today,
            "total_done": total_done_today,
            "total_positive": total_positive_today
        }
    }

@router.post("")
def save_daily_log(req: DailyLogSaveRequest, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        entry_date = datetime.datetime.strptime(req.entry_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    cur = conn.cursor()
    saved_count = 0
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    for item in req.entries:
        cur.execute("SELECT id, is_tracked FROM tests WHERE id = ?", (item.test_id,))
        test = cur.fetchone()
        if not test:
            continue
        
        done_val = max(0, item.done)
        pos_val = None
        if test["is_tracked"] and item.positive is not None:
            pos_val = max(0, min(done_val, item.positive))

        cur.execute("""
            INSERT INTO daily_entries (entry_date, test_id, done, positive, entered_by_user_id, entered_at, updated_by_user_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entry_date, test_id) DO UPDATE SET
            done = MAX(daily_entries.done, excluded.done),
            positive = CASE 
                WHEN excluded.positive IS NULL THEN daily_entries.positive
                WHEN daily_entries.positive IS NULL THEN excluded.positive
                ELSE MAX(daily_entries.positive, excluded.positive)
            END,
            updated_by_user_id = excluded.entered_by_user_id,
            updated_at = excluded.entered_at
        """, (req.entry_date, test["id"], done_val, pos_val, current_user["id"], now_str, current_user["id"], now_str))
        
        saved_count += 1

    conn.commit()

class VerifyShiftRequest(BaseModel):
    entry_date: str
    paper_register_tally: int
    system_total: int

@router.post("/verify")
def verify_shift_tally(req: VerifyShiftRequest, conn: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = conn.cursor()
    match_status = "MATCH" if req.paper_register_tally == req.system_total else "MISMATCH"
    detail_msg = f"Shift verification for {req.entry_date}: Register Tally={req.paper_register_tally}, System Total={req.system_total} [{match_status}]"
    
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
        (current_user["id"], "verify_shift_tally", detail_msg)
    )
    conn.commit()
    return {"status": "verified", "match": match_status, "detail": detail_msg}
