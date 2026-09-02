import datetime, sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from ..database import get_db
from ..schemas import DailyLogSaveRequest
from ..auth import get_current_user, require_admin

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
    
    # Query all active tests, combining routine daily entries and historical backlog entries
    cur.execute("""
        SELECT 
            t.id as test_id, t.name as test_name, t.section_id, t.is_tracked, t.sort_order,
            (COALESCE(e.done, 0) + COALESCE(b.done, 0)) as done,
            CASE 
                WHEN e.positive IS NOT NULL OR b.positive IS NOT NULL THEN (COALESCE(e.positive, 0) + COALESCE(b.positive, 0))
                ELSE NULL 
            END as positive,
            COALESCE(b.entered_by_user_id, e.entered_by_user_id) as entered_by_user_id,
            COALESCE(b.updated_at, e.updated_at) as updated_at
        FROM tests t
        LEFT JOIN daily_entries e ON e.test_id = t.id AND e.entry_date = ?
        LEFT JOIN backlog_entries b ON b.test_id = t.id AND b.entry_date = ?
        WHERE t.is_active = 1
        ORDER BY t.section_id, t.sort_order, t.id
    """, (date_str, date_str))
    all_tests = cur.fetchall()

    # Group tests by section_id
    tests_by_section = {}
    for row in all_tests:
        sec_id = row["section_id"]
        if sec_id not in tests_by_section:
            tests_by_section[sec_id] = []
        tests_by_section[sec_id].append(row)

    result_sections = []
    total_done_today = 0
    total_positive_today = 0
    total_rows_today = 0

    for sec in sections:
        sec_id = sec["id"]
        tests = tests_by_section.get(sec_id, [])
        test_items = []
        
        for t in tests:
            done = t["done"] if t["done"] is not None else 0
            pos = t["positive"] if t["positive"] is not None else None
            
            if done > 0 or (pos is not None and pos > 0):
                total_rows_today += 1
                total_done_today += done
                if pos is not None:
                    total_positive_today += pos

            test_items.append({
                "test_id": t["test_id"],
                "test_name": t["test_name"],
                "is_tracked": bool(t["is_tracked"]),
                "done": done,
                "positive": pos if t["is_tracked"] else None,
                "entered_by": t["entered_by_user_id"],
                "updated_at": t["updated_at"]
            })
        
        result_sections.append({
            "section_id": sec["id"],
            "section_name": sec["name"],
            "tests": test_items
        })

    # Fetch order stats for the date
    cur.execute("""
        SELECT status, COUNT(*) as count
        FROM test_orders
        WHERE date(ordered_at) = ?
        GROUP BY status
    """, (date_str,))
    
    order_stats = cur.fetchall()
    total_orders = 0
    pending_orders = 0
    entered_orders = 0
    completed_orders = 0
    
    for stat in order_stats:
        status = stat["status"].lower()
        count = stat["count"]
        total_orders += count
        if status == "pending":
            pending_orders += count
        elif status == "entered":
            entered_orders += count
        elif status == "completed":
            completed_orders += count

    return {
        "entry_date": date_str,
        "sections": result_sections,
        "today_check": {
            "rows_logged": total_rows_today,
            "total_done": total_done_today,
            "total_positive": total_positive_today
        },
        "order_summary": {
            "total": total_orders,
            "pending": pending_orders,
            "entered": entered_orders,
            "completed": completed_orders
        }
    }

@router.post("")
def save_daily_log(req: DailyLogSaveRequest, conn: sqlite3.Connection = Depends(get_db), admin_user: dict = Depends(require_admin)):
    cur = conn.cursor()
    saved_count = 0
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

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
        """, (req.entry_date, test["id"], done_val, pos_val, admin_user["id"], now_str, admin_user["id"], now_str))
        
        saved_count += 1

    conn.commit()
    return {"status": "saved", "rows_saved": saved_count}


