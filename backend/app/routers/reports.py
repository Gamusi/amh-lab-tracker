import datetime, sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any
from ..database import get_db
from ..auth import get_current_user
from ..pdf_generator import generate_pdf
from .. import evaluator

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

def _compute_flag(val_str, ref_str):
    if not val_str or not ref_str: return ""
    try:
        val = float(val_str)
        ref = ref_str.replace(" ", "")
        if '-' in ref:
            min_v, max_v = map(float, ref.split('-'))
            if val < min_v: return 'Low'
            if val > max_v: return 'High'
        elif '>=' in ref:
            if val < float(ref.replace('>=', '')): return 'Low'
        elif '<=' in ref:
            if val > float(ref.replace('<=', '')): return 'High'
        elif '>' in ref:
            if val <= float(ref.replace('>', '')): return 'Low'
        elif '<' in ref:
            if val >= float(ref.replace('<', '')): return 'High'
    except Exception:
        if isinstance(val_str, str) and isinstance(ref_str, str):
            if val_str.strip().lower() != ref_str.strip().lower() and "negative" in ref_str.lower():
                return "Abnormal"
    return ""

@router.get("/visit/{visit_id}/pdf")
def get_visit_report_pdf(visit_id: int, db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = db.cursor()
    cur.execute("""
        SELECT 
            v.id AS visit_id,
            v.ward_of_origin,
            v.lab_number,
            v.created_at AS visit_created_at,
            c.id AS client_id,
            c.client_number,
            c.full_name,
            c.date_of_birth,
            c.sex,
            c.phone,
            cl.name AS clinician_name
        FROM visits v
        JOIN clients c ON v.client_id = c.id
        LEFT JOIN clinicians cl ON v.clinician_id = cl.id
        WHERE v.id = ?
    """, (visit_id,))
    visit_row = cur.fetchone()
    if not visit_row:
        raise HTTPException(status_code=404, detail="Visit not found")
        
    dob_str = visit_row["date_of_birth"]
    dob = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None
    sex = visit_row["sex"] or "U"
    
    cur.execute("""
        SELECT 
            to_ord.id AS order_id,
            t.id AS test_id,
            t.name AS test_name, 
            t.parent_rollup_id,
            tr.result_value, 
            t.ref_range,
            t.default_unit,
            s.name AS section_name, 
            to_ord.ordered_at, 
            to_ord.sample_id,
            tr.entered_at,
            u_enter.full_name AS entered_by_name,
            u_ord.full_name AS ordered_by_name,
            u_ver.full_name AS verified_by_name
        FROM test_orders to_ord
        LEFT JOIN test_results tr ON tr.order_id = to_ord.id
        JOIN tests t ON to_ord.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        LEFT JOIN users u_enter ON tr.entered_by_user_id = u_enter.id
        LEFT JOIN users u_ord ON to_ord.ordered_by_user_id = u_ord.id
        LEFT JOIN users u_ver ON tr.verified_by_user_id = u_ver.id
        WHERE to_ord.visit_id = ? AND to_ord.status = 'completed' AND tr.result_value IS NOT NULL
        ORDER BY s.sort_order, t.sort_order, tr.id
    """, (visit_id,))
    
    rows = cur.fetchall()
    
    if not rows:
        raise HTTPException(status_code=400, detail="No completed test results found for this visit. Enter results before printing.")
    
    # Query any test_results linked to test_parameters for this visit
    cur.execute("""
        SELECT 
            tr.order_id,
            tp.parameter_name, 
            tr.result_value, 
            tr.result_unit, 
            tp.unit AS default_unit, 
            tp.ref_range, 
            tr.is_positive
        FROM test_results tr
        JOIN test_parameters tp ON tr.parameter_id = tp.id
        JOIN test_orders to_ord ON tr.order_id = to_ord.id
        WHERE to_ord.visit_id = ?
        ORDER BY tp.sort_order, tp.id
    """, (visit_id,))
    param_rows = cur.fetchall()
    params_by_order = {}
    for pr in param_rows:
        oid = pr["order_id"]
        if oid not in params_by_order:
            params_by_order[oid] = []
        params_by_order[oid].append({
            "name": pr["parameter_name"],
            "result": pr["result_value"],
            "unit": pr["result_unit"] or pr["default_unit"] or "",
            "reference_range": pr["ref_range"] or "",
            "flag": _compute_flag(pr["result_value"], pr["ref_range"])
        })

    results_by_section = {}
    ordered_date = None
    technician_name = None
    verified_by = None
    analyzer_sample_id = None
    analyzer_timestamp = None
    
    for row in rows:
        test_name = row["test_name"]
        result_value = row["result_value"]
        section_name = row["section_name"]
        order_id = row["order_id"]
            
        if not ordered_date and row["ordered_at"]:
            ordered_date = row["ordered_at"][:10]
        if not technician_name:
            technician_name = row["entered_by_name"] or row["ordered_by_name"]
        if not verified_by and row["verified_by_name"]:
            verified_by = row["verified_by_name"]
        if not analyzer_sample_id and row["sample_id"]:
            analyzer_sample_id = row["sample_id"]
        if not analyzer_timestamp and row["entered_at"]:
            analyzer_timestamp = row["entered_at"]
            
        test_data = {
            "test_name": test_name,
            "result": result_value,
            "unit": row["default_unit"] or "",
            "reference": row["ref_range"] or "",
            "reference_range": row["ref_range"] or "",
            "flag": _compute_flag(result_value, row["ref_range"]),
            "sample_id": row["sample_id"] or "",
            "timestamp": row["entered_at"] or "",
            "parameters": params_by_order.get(order_id, [])
        }
        
        if section_name not in results_by_section:
            results_by_section[section_name] = []
        results_by_section[section_name].append(test_data)

        
    results_data = []
    for sec_name, tests in results_by_section.items():
        results_data.append({
            "department": sec_name,
            "tests": tests
        })
        
    age_str = ""
    if dob:
        age_val = evaluator.calculate_age(dob, datetime.date.today())
        age_str = str(age_val)
        
    clinician_name = visit_row["clinician_name"] or "SELF REQUEST"

    order_data = {
        "client_number": visit_row["client_number"] or "",
        "full_name": visit_row["full_name"] or "",
        "age": age_str,
        "sex": sex,
        "lab_number": visit_row["lab_number"] or "",
        "ward_of_origin": visit_row["ward_of_origin"] or "",
        "requested_by": clinician_name,
        "ordered_by": clinician_name,
        "ordered_date": ordered_date or (visit_row["visit_created_at"][:10] if visit_row["visit_created_at"] else ""),
        "technician_name": technician_name or "",
        "verified_by": verified_by or "",
        "analyzer_sample_id": analyzer_sample_id or "",
        "analyzer_timestamp": analyzer_timestamp or ""
    }

    
    pdf_bytes = generate_pdf(order_data, results_data)
    return Response(content=pdf_bytes, media_type="application/pdf")

@router.get("/client/{client_id}/pdf")
def get_client_report_pdf(client_id: int, db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = db.cursor()
    cur.execute("SELECT id FROM visits WHERE client_id = ? ORDER BY id DESC LIMIT 1", (client_id,))
    v_row = cur.fetchone()
    if not v_row:
        raise HTTPException(status_code=404, detail="Client or visit not found")
    return get_visit_report_pdf(visit_id=v_row["id"], db=db, current_user=current_user)

