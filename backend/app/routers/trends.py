import sqlite3
from fastapi import APIRouter, Depends, Query
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/trends", tags=["Trends"])

@router.get("")
def get_trends(
    from_year: int = Query(2026),
    to_year: int = Query(2027),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM sections ORDER BY sort_order, id")
    sections = cur.fetchall()

    months_list = []
    for y in range(from_year, to_year + 1):
        for m in range(1, 13):
            months_list.append((y, m, f"{y}-{m:02d}"))

    trend_rows = []

    for y, m, month_str in months_list:
        start_d = f"{month_str}-01"
        if m == 12: end_d = f"{y}-12-31"
        else: end_d = f"{y}-{m+1:02d}-01"

        row_data = {"month": month_str, "year": y, "month_num": m}
        
        cur.execute("""
            SELECT t.section_id, SUM(e.done) as total_done
            FROM daily_entries e
            JOIN tests t ON e.test_id = t.id
            WHERE e.entry_date >= ? AND e.entry_date < ?
            GROUP BY t.section_id
        """, (start_d, end_d))
        
        results = cur.fetchall()
        sums_by_sec = {r["section_id"]: (r["total_done"] or 0) for r in results}

        total_month = 0
        for s in sections:
            val = sums_by_sec.get(s["id"], 0)
            row_data[s["name"]] = val
            total_month += val
        
        row_data["Total"] = total_month
        trend_rows.append(row_data)

    return {
        "from_year": from_year,
        "to_year": to_year,
        "sections": [s["name"] for s in sections],
        "trends": trend_rows
    }
