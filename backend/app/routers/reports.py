import datetime, sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..auth import get_current_user
from ..pdf_generator import generate_pdf, generate_blood_bag_label
from .. import evaluator
from .. import biochem_validator
from .. import operations_analytics
from .. import operations_pdf
from .. import surveillance_analytics
from .. import surveillance_pdf

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

    cur.execute("SELECT facility_name FROM facility_settings WHERE id = 1")
    fac_row = cur.fetchone()
    facility_name = fac_row["facility_name"] if fac_row and fac_row["facility_name"] else "Clinical Diagnostic Laboratory"

    return {
        "facility": facility_name,
        "moh_form": "HMIS 105 Section 6 — Laboratory Surveillance",
        "month": ref_date.strftime("%B %Y"),
        "start_date": s_str,
        "end_date": e_str,
        "surveillance_items": surveillance_items
    }

@router.get("/operations")
def get_operations_report(
    period_type: str = Query("Month"),
    reference_date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return operations_analytics.calculate_operations_metrics(
        conn=conn,
        period_type=period_type,
        reference_date=reference_date,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/operations/pdf")
def get_operations_report_pdf(
    period_type: str = Query("Month"),
    reference_date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    data = operations_analytics.calculate_operations_metrics(
        conn=conn,
        period_type=period_type,
        reference_date=reference_date,
        start_date=start_date,
        end_date=end_date
    )
    pdf_bytes = operations_pdf.generate_operations_pdf(data=data, current_user=current_user)
    
    p_info = data.get("period", {})
    s_date = p_info.get("start_date", "start")
    e_date = p_info.get("end_date", "end")
    filename = f"AMH_Operations_Report_{period_type}_{s_date}_{e_date}.pdf"
    
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/surveillance")
def get_surveillance_report(
    period_type: str = Query("Month"),
    reference_date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return surveillance_analytics.calculate_surveillance_metrics(
        conn=conn,
        period_type=period_type,
        reference_date=reference_date,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/surveillance/pdf")
def get_surveillance_report_pdf(
    period_type: str = Query("Month"),
    reference_date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    data = surveillance_analytics.calculate_surveillance_metrics(
        conn=conn,
        period_type=period_type,
        reference_date=reference_date,
        start_date=start_date,
        end_date=end_date
    )
    pdf_bytes = surveillance_pdf.generate_surveillance_pdf(data=data, current_user=current_user)
    
    p_info = data.get("period", {})
    s_date = p_info.get("start_date", "start")
    e_date = p_info.get("end_date", "end")
    filename = f"AMH_Surveillance_Report_{period_type}_{s_date}_{e_date}.pdf"
    
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

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

def _compute_flag(val_str, ref_str=None):
    if not val_str: return ""
    try:
        val = float(str(val_str).strip().split()[0])
        if ref_str:
            ref = ref_str.replace(" ", "")
            if '-' in ref:
                min_v, max_v = map(float, ref.split('-'))
                if val < min_v: return 'L'
                if val > max_v: return 'H'
            elif '>=' in ref:
                if val < float(ref.replace('>=', '')): return 'L'
            elif '<=' in ref:
                if val > float(ref.replace('<=', '')): return 'H'
            elif '>' in ref:
                if val <= float(ref.replace('>', '')): return 'L'
            elif '<' in ref:
                if val >= float(ref.replace('<', '')): return 'H'
    except Exception:
        pass
        
    if evaluator.is_qualitative_abnormal(val_str, ref_str):
        return "\u26A0"
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
            v.specimen_type_id,
            st.name AS specimen_name,
            c.id AS client_id,
            c.client_number,
            c.full_name,
            c.date_of_birth,
            c.age_years,
            c.age_category,
            c.sex,
            c.phone,
            cl.name AS clinician_name
        FROM visits v
        JOIN clients c ON v.client_id = c.id
        LEFT JOIN clinicians cl ON v.clinician_id = cl.id
        LEFT JOIN specimen_types st ON v.specimen_type_id = st.id
        WHERE v.id = ?
    """, (visit_id,))
    visit_row = cur.fetchone()
    if not visit_row:
        raise HTTPException(status_code=404, detail="Visit not found")
        
    dob_str = visit_row["date_of_birth"]
    dob = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None
    sex = visit_row["sex"] or "U"
    
    cur.execute("""
        SELECT COUNT(*) as unverified_count
        FROM test_orders to_ord
        LEFT JOIN test_results tr ON tr.order_id = to_ord.id
        WHERE to_ord.visit_id = ? AND (to_ord.status = 'entered' OR (to_ord.status = 'completed' AND tr.result_value IS NOT NULL AND tr.verified_by_user_id IS NULL))
    """, (visit_id,))
    unv_row = cur.fetchone()
    if unv_row and unv_row["unverified_count"] > 0:
        if current_user.get("role") not in ["admin", "superadmin"]:
            raise HTTPException(status_code=403, detail="Results must be verified by an Administrator before printing.")

    cur.execute("""
        SELECT 
            to_ord.id AS order_id,
            t.id AS test_id,
            t.name AS test_name, 
            t.parent_rollup_id,
            tr.result_value, 
            tr.result_unit,
            tr.clinical_flag,
            t.ref_range,
            t.default_unit,
            s.name AS section_name, 
            to_ord.ordered_at, 
            to_ord.sample_id,
            COALESCE(tr.entered_at, tr_p.entered_at) AS entered_at,
            COALESCE(u_enter.full_name, u_enter_p.full_name) AS entered_by_name,
            u_ord.full_name AS ordered_by_name,
            COALESCE(u_ver.full_name, u_ver_p.full_name) AS verified_by_name
        FROM test_orders to_ord
        LEFT JOIN test_results tr ON tr.order_id = to_ord.id AND tr.parameter_id IS NULL
        LEFT JOIN test_results tr_p ON tr_p.order_id = to_ord.id AND tr_p.parameter_id IS NOT NULL
        JOIN tests t ON to_ord.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        LEFT JOIN users u_enter ON tr.entered_by_user_id = u_enter.id
        LEFT JOIN users u_enter_p ON tr_p.entered_by_user_id = u_enter_p.id
        LEFT JOIN users u_ord ON to_ord.ordered_by_user_id = u_ord.id
        LEFT JOIN users u_ver ON tr.verified_by_user_id = u_ver.id
        LEFT JOIN users u_ver_p ON tr_p.verified_by_user_id = u_ver_p.id
        WHERE to_ord.visit_id = ? AND to_ord.status IN ('completed', 'entered')
        GROUP BY to_ord.id
        ORDER BY s.sort_order, t.sort_order, to_ord.id
    """, (visit_id,))
    
    rows = cur.fetchall()
    
    if not rows:
        raise HTTPException(status_code=400, detail="No completed test results found for this visit. Enter results before printing.")
    
    dob_obj = dob
    age_int = None
    if dob_obj:
        try:
            age_int = evaluator.calculate_age(dob_obj, datetime.date.today())
        except Exception:
            pass
    if age_int is None and visit_row["age_years"] is not None:
        age_int = int(visit_row["age_years"])

    # Query any test_results linked to test_parameters for this visit
    cur.execute("""
        SELECT 
            tr.order_id,
            tp.parameter_name, 
            tr.result_value, 
            tr.result_unit, 
            tr.clinical_flag,
            tp.unit AS default_unit, 
            tp.ref_range, 
            tr.is_positive,
            tr.entered_at,
            u_enter.full_name AS entered_by_name,
            u_ver.full_name AS verified_by_name
        FROM test_results tr
        JOIN test_parameters tp ON tr.parameter_id = tp.id
        JOIN test_orders to_ord ON tr.order_id = to_ord.id
        LEFT JOIN users u_enter ON tr.entered_by_user_id = u_enter.id
        LEFT JOIN users u_ver ON tr.verified_by_user_id = u_ver.id
        WHERE to_ord.visit_id = ? AND tr.parameter_id IS NOT NULL
        ORDER BY tp.sort_order, tp.id
    """, (visit_id,))
    param_rows = cur.fetchall()
    params_by_order = {}
    ordered_date = None
    technician_name = None
    verified_by = None
    analyzer_sample_id = None
    analyzer_timestamp = None

    for pr in param_rows:
        oid = pr["order_id"]
        if oid not in params_by_order:
            params_by_order[oid] = []
        
        if not technician_name and pr["entered_by_name"]:
            technician_name = pr["entered_by_name"]
        if not verified_by and pr["verified_by_name"]:
            verified_by = pr["verified_by_name"]
        if not analyzer_timestamp and pr["entered_at"]:
            analyzer_timestamp = pr["entered_at"]
        
        p_name = pr["parameter_name"]
        p_val = pr["result_value"]
        p_unit = pr["result_unit"] or pr["default_unit"] or ""
        p_ref = pr["ref_range"]
        p_flag = pr["clinical_flag"]

        if not p_ref:
            rule = biochem_validator._find_matching_rule(db, p_name, age=age_int, sex=sex, unit=p_unit)
            if rule:
                n_min = rule.get("normal_min")
                n_max = rule.get("normal_max")
                if n_min is not None and n_max is not None:
                    p_ref = f"{n_min} - {n_max}"
                elif n_min is not None:
                    p_ref = f">= {n_min}"
                elif n_max is not None:
                    p_ref = f"< {n_max}"
            else:
                eval_res = evaluator.evaluate_result(p_name, p_val, dob=dob_obj, sex=sex, entry_date=datetime.date.today(), db=db, unit=p_unit)
                if eval_res and eval_res.get("reference"):
                    p_ref = eval_res.get("reference")

        if not p_flag:
            eval_res = evaluator.evaluate_result(p_name, p_val, dob=dob_obj, sex=sex, entry_date=datetime.date.today(), db=db, unit=p_unit)
            if eval_res and eval_res.get("flag"):
                p_flag = eval_res.get("flag")
            else:
                p_flag = _compute_flag(p_val, p_ref)

        params_by_order[oid].append({
            "name": p_name,
            "result": p_val,
            "unit": p_unit,
            "reference_range": p_ref or "",
            "flag": p_flag or ""
        })

    cur.execute("""
        SELECT 
            dc.*,
            u_enter.full_name AS entered_by_name,
            u_ver.full_name AS verified_by_name
        FROM donor_crossmatches dc
        JOIN test_orders to_ord ON dc.order_id = to_ord.id
        LEFT JOIN users u_enter ON dc.entered_by_user_id = u_enter.id
        LEFT JOIN users u_ver ON dc.verified_by_user_id = u_ver.id
        WHERE to_ord.visit_id = ?
        ORDER BY dc.id ASC
    """, (visit_id,))
    crossmatch_rows = cur.fetchall()
    crossmatches_by_order = {}
    for cm in crossmatch_rows:
        oid = cm["order_id"]
        if oid not in crossmatches_by_order:
            crossmatches_by_order[oid] = []
        crossmatches_by_order[oid].append(dict(cm))

    # Fetch culture_orders for this visit
    cur.execute("""
        SELECT co.*, to_ord.id AS ord_id
        FROM culture_orders co
        JOIN test_orders to_ord ON co.order_id = to_ord.id
        WHERE to_ord.visit_id = ?
    """, (visit_id,))
    co_rows = cur.fetchall()
    culture_by_order = {}
    for co in co_rows:
        oid = co["ord_id"]
        co_id = co["id"]
        # Fetch isolates
        cur.execute("""
            SELECT id, isolate_number, organism_name, colony_morphology, is_pathogen, is_contaminant
            FROM culture_isolates WHERE culture_order_id = ? ORDER BY isolate_number ASC
        """, (co_id,))
        iso_rows = cur.fetchall()
        isolates_list = []
        alerts_list = []
        for iso in iso_rows:
            iso_id = iso["id"]
            cur.execute("""
                SELECT antimicrobial_class, agent_name, measurement_type, measurement_value,
                       raw_sir, overridden_sir, override_reason, clinical_note
                FROM culture_ast_results WHERE isolate_id = ? ORDER BY antimicrobial_class ASC, agent_name ASC
            """, (iso_id,))
            ast_rows = [dict(r) for r in cur.fetchall()]
            isolates_list.append({
                "organism_name": iso["organism_name"],
                "colony_morphology": iso["colony_morphology"],
                "is_pathogen": bool(iso["is_pathogen"]),
                "is_contaminant": bool(iso["is_contaminant"]),
                "ast_results": ast_rows
            })
            from ..culture_engine import apply_phenotypic_safety_overrides
            _, iso_alerts = apply_phenotypic_safety_overrides(iso["organism_name"], ast_rows)
            alerts_list.extend(iso_alerts)

        culture_by_order[oid] = {
            "phase": co["phase"],
            "preliminary_micro": co["preliminary_micro"],
            "colony_count_cfu": co["colony_count_cfu"],
            "growth_category": co["growth_category"],
            "incubation_hours": co["incubation_hours"],
            "media_used": co["media_used"],
            "clinical_notes": co["clinical_notes"],
            "isolates": isolates_list,
            "alerts": list(dict.fromkeys(alerts_list))
        }

    results_by_section = {}
    ordered_date = None
    technician_name = None
    verified_by = None
    analyzer_sample_id = None
    analyzer_timestamp = None
    
    for row in rows:
        order_id = row["order_id"]
        test_name = row["test_name"]
        result_value = row["result_value"]
        section_name = row["section_name"]
        order_params = params_by_order.get(order_id, [])
        order_crossmatches = crossmatches_by_order.get(order_id, [])

        if not result_value and not order_params and not order_crossmatches:
            continue
            
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
            
        t_unit = row["result_unit"] or row["default_unit"] or ""
        t_ref = row["ref_range"]
        t_flag = row["clinical_flag"]

        if not order_params:
            if not t_ref:
                rule = biochem_validator._find_matching_rule(db, test_name, age=age_int, sex=sex, unit=t_unit)
                if rule:
                    n_min = rule.get("normal_min")
                    n_max = rule.get("normal_max")
                    if n_min is not None and n_max is not None:
                        t_ref = f"{n_min} - {n_max}"
                    elif n_min is not None:
                        t_ref = f">= {n_min}"
                    elif n_max is not None:
                        t_ref = f"< {n_max}"
                else:
                    eval_res = evaluator.evaluate_result(test_name, result_value, dob=dob_obj, sex=sex, entry_date=datetime.date.today(), db=db, unit=t_unit)
                    if eval_res and eval_res.get("reference"):
                        t_ref = eval_res.get("reference")

            if not t_flag:
                eval_res = evaluator.evaluate_result(test_name, result_value, dob=dob_obj, sex=sex, entry_date=datetime.date.today(), db=db, unit=t_unit)
                if eval_res and eval_res.get("flag"):
                    t_flag = eval_res.get("flag")
                else:
                    t_flag = _compute_flag(result_value, t_ref)

        test_data = {
            "test_name": test_name,
            "result": result_value if not order_params else "Completed",
            "unit": t_unit,
            "reference": t_ref or "",
            "reference_range": t_ref or "",
            "flag": t_flag or "",
            "sample_id": row["sample_id"] or "",
            "timestamp": row["entered_at"] or "",
            "parameters": order_params,
            "crossmatches": order_crossmatches
        }

        if order_id in culture_by_order:
            test_data.update(culture_by_order[order_id])
        
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
        age_str = f"{age_val}y" if age_val > 0 else "<1y"
    elif visit_row["age_years"] is not None:
        ay = visit_row["age_years"]
        if ay < 0.08: # ~29 days
            days = round(ay * 365.25)
            age_str = f"{days}d"
        elif ay < 1.0:
            months = round(ay * 12)
            age_str = f"{months}m"
        elif ay < 3.0:
            yrs = int(ay)
            rem_m = round((ay - yrs) * 12)
            age_str = f"{yrs}y {rem_m}m" if rem_m > 0 else f"{yrs}y"
        else:
            age_str = f"{int(ay)}y" if ay.is_integer() else f"{ay:g}y"
        
    # Query all distinct specimens used across orders in this visit
    cur.execute("""
        SELECT DISTINCT st.name
        FROM test_orders to_ord
        JOIN specimen_types st ON to_ord.specimen_type_id = st.id
        WHERE to_ord.visit_id = ?
        ORDER BY st.sort_order, st.id
    """, (visit_id,))
    v_specs = cur.fetchall()
    raw_spec_names = [r["name"] for r in v_specs if r["name"]]
    if not raw_spec_names and visit_row["specimen_name"]:
        raw_spec_names = [visit_row["specimen_name"]]

    from ..specimen_validator import get_specimen_report_alias
    short_names = []
    for sn in raw_spec_names:
        alias = get_specimen_report_alias(sn)
        if alias and alias not in short_names:
            short_names.append(alias)

    specimen_display = ", ".join(short_names) if short_names else "Blood"

    clinician_name = visit_row["clinician_name"] or "SELF REQUEST"

    order_data = {
        "client_number": visit_row["client_number"] or "",
        "full_name": visit_row["full_name"] or "",
        "age": age_str,
        "sex": sex,
        "lab_number": visit_row["lab_number"] or "",
        "ward_of_origin": visit_row["ward_of_origin"] or "",
        "specimen": specimen_display,
        "requested_by": clinician_name,
        "ordered_by": clinician_name,
        "ordered_date": ordered_date or (visit_row["visit_created_at"][:10] if visit_row["visit_created_at"] else ""),
        "technician_name": technician_name or "",
        "verified_by": verified_by or "",
        "analyzer_sample_id": analyzer_sample_id or "",
        "analyzer_timestamp": analyzer_timestamp or ""
    }

    
    pdf_bytes = generate_pdf(order_data, results_data)
    lab_num = visit_row["lab_number"] or f"AMH_Visit_{visit_id}"
    safe_filename = "".join(c for c in lab_num if c.isalnum() or c in ("-", "_", ".")) + ".pdf"

    headers = {
        "Content-Disposition": f'inline; filename="{safe_filename}"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/client/{client_id}/pdf")
def get_client_report_pdf(client_id: int, db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cur = db.cursor()
    cur.execute("SELECT id FROM visits WHERE client_id = ? ORDER BY id DESC LIMIT 1", (client_id,))
    v_row = cur.fetchone()
    if not v_row:
        raise HTTPException(status_code=404, detail="Client or visit not found")
    return get_visit_report_pdf(visit_id=v_row["id"], db=db, current_user=current_user)

@router.get("/crossmatch/{crossmatch_id}/bag-label")
def get_crossmatch_bag_label(
    crossmatch_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    cur = db.cursor()
    cur.execute("""
        SELECT 
            dc.*,
            c.full_name as client_name, c.client_number,
            v.lab_number, v.ward_of_origin as ward,
            u_enter.full_name as technician_name,
            u_ver.full_name as verified_by_name
        FROM donor_crossmatches dc
        JOIN test_orders o ON dc.order_id = o.id
        JOIN visits v ON o.visit_id = v.id
        JOIN clients c ON v.client_id = c.id
        LEFT JOIN users u_enter ON dc.entered_by_user_id = u_enter.id
        LEFT JOIN users u_ver ON dc.verified_by_user_id = u_ver.id
        WHERE dc.id = ?
    """, (crossmatch_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Crossmatch record not found")

    if row["compatibility_status"] != "COMPATIBLE":
        raise HTTPException(status_code=400, detail="Blood bag release labels can only be generated for COMPATIBLE donor units.")

    cur.execute("""
        SELECT tr.result_value
        FROM test_results tr
        JOIN test_orders o ON tr.order_id = o.id
        JOIN visits v ON o.visit_id = v.id
        JOIN tests t ON o.test_id = t.id
        WHERE v.client_id = (SELECT client_id FROM visits v2 JOIN test_orders o2 ON v2.id = o2.visit_id WHERE o2.id = ?)
        AND LOWER(t.name) LIKE '%blood group%'
        AND tr.result_value IS NOT NULL AND tr.result_value NOT LIKE '%Discrepancy%'
        ORDER BY tr.id DESC LIMIT 1
    """, (row["order_id"],))
    bg_r = cur.fetchone()
    client_bg = bg_r["result_value"] if bg_r else "Documented Group"

    label_data = {
        "client_name": row["client_name"],
        "client_number": row["client_number"],
        "lab_number": row["lab_number"] or row["client_number"],
        "ward": row["ward"] or "OPD",
        "donor_unit_id": row["donor_unit_id"],
        "donor_blood_group": row["donor_blood_group"],
        "client_blood_group": client_bg,
        "product_type": row["product_type"],
        "expiry_date": row["expiry_date"],
        "compatibility_status": row["compatibility_status"],
        "release_status": row["release_status"],
        "technician_name": row["technician_name"] or current_user.get("full_name") or "Lab Technician",
        "verified_by": row["verified_by_name"] or "Supervisor",
        "issued_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    pdf_bytes = generate_blood_bag_label(label_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="blood_bag_label_{row["donor_unit_id"]}.pdf"'
        }
    )


