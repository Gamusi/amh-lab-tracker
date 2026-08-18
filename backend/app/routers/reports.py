import datetime, sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any
from ..database import get_db
from ..auth import get_current_user
from ..pdf_generator import generate_pdf

router = APIRouter(prefix="/api/reports", tags=["Reports"])

def calculate_date_range(period_type: str, ref_date: datetime.date):
    if period_type == "Day":
        return ref_date, ref_date
    elif period_type == "Week":
        start = ref_date - datetime.timedelta(days=ref_date.weekday())
        end = start + datetime.timedelta(days=6)
        return start, end
    elif period_type == "Month":
        start = ref_date.replace(day=1)
        if start.month == 12:
            end = datetime.date(start.year, 12, 31)
        else:
            end = datetime.date(start.year, start.month + 1, 1) - datetime.timedelta(days=1)
        return start, end
    elif period_type == "Quarter":
        m, y = ref_date.month, ref_date.year
        if m in [7, 8, 9]: return datetime.date(y, 7, 1), datetime.date(y, 9, 30)
        elif m in [10, 11, 12]: return datetime.date(y, 10, 1), datetime.date(y, 12, 31)
        elif m in [1, 2, 3]: return datetime.date(y, 1, 1), datetime.date(y, 3, 31)
        else: return datetime.date(y, 4, 1), datetime.date(y, 6, 30)
    elif period_type == "Half-Year":
        m, y = ref_date.month, ref_date.year
        if m >= 7: return datetime.date(y, 7, 1), datetime.date(y, 12, 31)
        else: return datetime.date(y, 1, 1), datetime.date(y, 6, 30)
    elif period_type == "Financial Year":
        m, y = ref_date.month, ref_date.year
        if m >= 7: return datetime.date(y, 7, 1), datetime.date(y + 1, 6, 30)
        else: return datetime.date(y - 1, 7, 1), datetime.date(y, 6, 30)
    else:
        return datetime.date(ref_date.year, 1, 1), datetime.date(ref_date.year, 12, 31)

@router.get("")
def get_report(
    period_type: str = Query("Month"),
    reference_date: str = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not reference_date:
        ref_date = datetime.date.today()
    else:
        try:
            ref_date = datetime.datetime.strptime(reference_date, "%Y-%m-%d").date()
        except ValueError:
            ref_date = datetime.date.today()

    start_date, end_date = calculate_date_range(period_type, ref_date)
    s_str = start_date.strftime("%Y-%m-%d")
    e_str = end_date.strftime("%Y-%m-%d")

    cur = conn.cursor()
    cur.execute("SELECT id, name FROM sections ORDER BY sort_order, id")
    sections = cur.fetchall()

    report_sections = []
    total_done_grand = 0
    total_pos_grand = 0

    for sec in sections:
        cur.execute("SELECT id, name, is_tracked FROM tests WHERE section_id = ? AND is_active = 1 ORDER BY sort_order, id", (sec["id"],))
        tests = cur.fetchall()
        
        sec_done = 0
        sec_pos = 0
        test_rows = []

        for t in tests:
            cur.execute("""
                SELECT SUM(done) as sum_done, SUM(positive) as sum_pos
                FROM daily_entries
                WHERE test_id = ? AND entry_date >= ? AND entry_date <= ?
            """, (t["id"], s_str, e_str))
            
            row_sum = cur.fetchone()
            done_sum = row_sum["sum_done"] if row_sum and row_sum["sum_done"] else 0
            pos_sum = row_sum["sum_pos"] if row_sum and row_sum["sum_pos"] and t["is_tracked"] else None

            sec_done += done_sum
            if pos_sum is not None:
                sec_pos += pos_sum

            positivity_rate = None
            if t["is_tracked"] and done_sum > 0 and pos_sum is not None:
                positivity_rate = round((pos_sum / done_sum) * 100, 1)

            test_rows.append({
                "test_id": t["id"],
                "test_name": t["name"],
                "is_tracked": bool(t["is_tracked"]),
                "done": done_sum,
                "positive": pos_sum,
                "positivity_rate": positivity_rate
            })

        total_done_grand += sec_done
        total_pos_grand += sec_pos

        report_sections.append({
            "section_id": sec["id"],
            "section_name": sec["name"],
            "section_total_done": sec_done,
            "section_total_positive": sec_pos,
            "tests": test_rows
        })

    return {
        "period_type": period_type,
        "reference_date": ref_date.strftime("%Y-%m-%d"),
        "start_date": s_str,
        "end_date": e_str,
        "grand_total_done": total_done_grand,
        "grand_total_positive": total_pos_grand,
        "sections": report_sections
    }

@router.get("/hmis105")
def get_hmis105_report(
    reference_date: str = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not reference_date:
        ref_date = datetime.date.today()
    else:
        try:
            ref_date = datetime.datetime.strptime(reference_date, "%Y-%m-%d").date()
        except ValueError:
            ref_date = datetime.date.today()

    start_date = ref_date.replace(day=1)
    if start_date.month == 12:
        end_date = datetime.date(start_date.year, 12, 31)
    else:
        end_date = datetime.date(start_date.year, start_date.month + 1, 1) - datetime.timedelta(days=1)

    s_str = start_date.strftime("%Y-%m-%d")
    e_str = end_date.strftime("%Y-%m-%d")

    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.name, SUM(e.done) as total_done, SUM(e.positive) as total_pos
        FROM tests t
        LEFT JOIN daily_entries e ON e.test_id = t.id AND e.entry_date >= ? AND e.entry_date <= ?
        WHERE t.is_tracked = 1 AND t.is_active = 1
        GROUP BY t.id, t.name
        ORDER BY t.sort_order, t.id
    """, (s_str, e_str))

    surveillance_items = []
    for r in cur.fetchall():
        done = r["total_done"] or 0
        pos = r["total_pos"] or 0
        rate = round((pos / done) * 100, 1) if done > 0 else 0.0
        surveillance_items.append({
            "disease_test": r["name"],
            "tests_done": done,
            "positive_cases": pos,
            "positivity_rate": rate
        })

    return {
        "facility": "Ahmadiyya Muslim Hospital, Mbale",
        "moh_form": "HMIS 105 Section 6 — Laboratory Surveillance",
        "month": ref_date.strftime("%B %Y"),
        "start_date": s_str,
        "end_date": e_str,
        "surveillance_items": surveillance_items
    }

class ReportRequest(BaseModel):
    order_data: Dict[str, Any]
    results_data: List[Dict[str, Any]]

@router.post("/generate-pdf")
def create_pdf_report(
    request: ReportRequest,
    current_user: dict = Depends(get_current_user)
):
    pdf_bytes = generate_pdf(request.order_data, request.results_data)
    return Response(content=pdf_bytes, media_type="application/pdf")
