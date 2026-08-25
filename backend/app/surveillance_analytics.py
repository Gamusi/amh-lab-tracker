import sqlite3
import datetime
from typing import Optional, Dict, Any, List
from .operations_analytics import calculate_date_range, format_reporting_period

def is_order_surveillance_incident(test_name: str, results: list) -> bool:
    """
    Determines if a completed test order represents a positive / incident case for surveillance.
    - For quantitative Hematology (CBC): ONLY Critical Anemia (Hb < 8.0 g/dL) or panic/critical flags count.
    - For infectious diseases & qualitative assays (Malaria, HIV, BAT, HBsAg, VDRL, Sickling, Widal): positive/reactive counts.
    - For Urinalysis / Stool: positive/abnormal parameters count.
    """
    t_name_lower = (test_name or "").lower()
    
    if "cbc" in t_name_lower or "blood count" in t_name_lower:
        for res in results:
            flag = (res["clinical_flag"] or "").strip().lower()
            p_name = (res["parameter_name"] or "").lower()
            val_str = str(res["result_value"] or "").strip()
            
            if flag in ["l*", "h*", "critical", "panic", "critical low", "critical high"]:
                return True
            
            if "hb" in p_name or "hemoglobin" in p_name:
                try:
                    hb_val = float(val_str.split()[0])
                    if hb_val < 8.0:
                        return True
                except (ValueError, TypeError):
                    pass
        return False

    for res in results:
        if res["is_positive"] == 1:
            return True
        val = (res["result_value"] or "").strip().lower()
        if val in ["positive", "abnormal", "reactive", "detected"] or val.startswith("positive") or val.startswith("reactive"):
            return True
        flag = (res["clinical_flag"] or "").strip().lower()
        if flag in ["panic", "critical", "abnormal", "high", "h*", "l*"]:
            return True
            
    return False

def calculate_surveillance_metrics(
    conn: sqlite3.Connection,
    period_type: str = "Month",
    reference_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates deterministic AMH Laboratory Epidemiological Surveillance & Disease Incidence metrics.
    Focuses strictly on assays and clinical panels configured with is_tracked = 1.
    """
    if not reference_date:
        ref_date = datetime.date.today()
    else:
        try:
            ref_date = datetime.datetime.strptime(reference_date, "%Y-%m-%d").date()
        except ValueError:
            ref_date = datetime.date.today()

    if not start_date or not end_date:
        s_date, e_date = calculate_date_range(period_type, ref_date)
        s_str = s_date.strftime("%Y-%m-%d")
        e_str = e_date.strftime("%Y-%m-%d")
    else:
        s_str = start_date
        e_str = end_date

    formatted_period = format_reporting_period(period_type, ref_date)

    cur = conn.cursor()

    # Query all active tracked tests (is_tracked = 1)
    cur.execute("""
        SELECT 
            s.id AS section_id,
            s.name AS section_name,
            t.id AS test_id,
            t.name AS test_name,
            t.parent_rollup_id
        FROM tests t
        JOIN sections s ON t.section_id = s.id
        WHERE t.is_active = 1 AND t.is_tracked = 1
        ORDER BY s.sort_order, s.id, t.name
    """)
    tracked_catalog = cur.fetchall()

    # Tracked parent/orderable tests
    orderable_tracked_map = {}
    for t in tracked_catalog:
        if t["parent_rollup_id"] is None:
            orderable_tracked_map[t["test_id"]] = {
                "test_id": t["test_id"],
                "test_name": t["test_name"],
                "section_id": t["section_id"],
                "section_name": t["section_name"],
                "evaluated": 0,
                "positive": 0,
                "negative": 0,
                "incidence_rate": 0.0
            }

    # Query completed orders for tracked tests within the period
    cur.execute("""
        SELECT 
            to_ord.id AS order_id,
            to_ord.visit_id,
            to_ord.test_id,
            to_ord.ordered_at,
            t.name AS test_name,
            t.parent_rollup_id,
            s.id AS section_id,
            s.name AS section_name,
            v.ward_of_origin
        FROM test_orders to_ord
        JOIN tests t ON to_ord.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        JOIN visits v ON to_ord.visit_id = v.id
        WHERE to_ord.status = 'completed'
          AND v.is_deleted = 0
          AND t.is_tracked = 1
          AND t.parent_rollup_id IS NULL
          AND DATE(to_ord.ordered_at) >= ?
          AND DATE(to_ord.ordered_at) <= ?
        ORDER BY to_ord.ordered_at
    """, (s_str, e_str))
    order_rows = cur.fetchall()

    # Section accumulators
    cur.execute("SELECT id, name FROM sections ORDER BY sort_order, id")
    all_sections = cur.fetchall()
    section_stats: Dict[int, Dict[str, Any]] = {
        sec["id"]: {
            "section_id": sec["id"],
            "section_name": sec["name"],
            "evaluated_count": 0,
            "incident_count": 0,
            "incidence_rate_percent": 0.0
        }
        for sec in all_sections
    }

    # Ward of origin accumulators: {ward: {"evaluated": int, "positive": int}}
    ward_stats: Dict[str, Dict[str, int]] = {}

    total_evaluated = 0
    total_incident_cases = 0

    for row in order_rows:
        oid = row["order_id"]
        tid = row["test_id"]
        sec_id = row["section_id"]
        w_origin = row["ward_of_origin"] or "Outpatient / GOPD"

        if w_origin not in ward_stats:
            ward_stats[w_origin] = {"evaluated": 0, "positive": 0}
        ward_stats[w_origin]["evaluated"] += 1

        total_evaluated += 1
        if sec_id in section_stats:
            section_stats[sec_id]["evaluated_count"] += 1

        if tid in orderable_tracked_map:
            orderable_tracked_map[tid]["evaluated"] += 1

        # Check if the order had any positive/abnormal result
        cur.execute("""
            SELECT tr.is_positive, tr.clinical_flag, tr.result_value, tp.parameter_name
            FROM test_results tr
            LEFT JOIN test_parameters tp ON tr.parameter_id = tp.id
            WHERE tr.order_id = ?
        """, (oid,))
        results = cur.fetchall()

        is_order_incident = is_order_surveillance_incident(row["test_name"], results)

        if is_order_incident:
            total_incident_cases += 1
            if sec_id in section_stats:
                section_stats[sec_id]["incident_count"] += 1
            if tid in orderable_tracked_map:
                orderable_tracked_map[tid]["positive"] += 1
            ward_stats[w_origin]["positive"] += 1

    # Calculate rates for each test
    surveillance_ledger = []
    for tid, item in orderable_tracked_map.items():
        ev = item["evaluated"]
        pos = item["positive"]
        item["negative"] = max(0, ev - pos)
        item["incidence_rate"] = round((pos / ev) * 100.0, 1) if ev > 0 else 0.0
        surveillance_ledger.append(item)

    # Sort ledger by section then test name
    surveillance_ledger.sort(key=lambda x: (x["section_name"], x["test_name"]))

    # Calculate rates for sections
    sections_breakdown = []
    for s_id, s_info in section_stats.items():
        ev = s_info["evaluated_count"]
        pos = s_info["incident_count"]
        rate = round((pos / ev) * 100.0, 1) if ev > 0 else 0.0
        s_info["incidence_rate_percent"] = rate
        sections_breakdown.append(s_info)

    # Calculate overall incidence rate
    overall_incidence_rate = round((total_incident_cases / total_evaluated) * 100.0, 1) if total_evaluated > 0 else 0.0

    # Ward breakdown list
    wards_breakdown = []
    for w_name, w_info in sorted(ward_stats.items(), key=lambda x: x[1]["positive"], reverse=True):
        ev = w_info["evaluated"]
        pos = w_info["positive"]
        rate = round((pos / ev) * 100.0, 1) if ev > 0 else 0.0
        wards_breakdown.append({
            "ward": w_name,
            "evaluated": ev,
            "positive_cases": pos,
            "incidence_rate": rate
        })

    # Financial Year monthly trends calculation (from July of active FY to ref_date)
    ref_y, ref_m = ref_date.year, ref_date.month
    fy_start_year = ref_y if ref_m >= 7 else ref_y - 1

    trend_months = []
    curr_y, curr_m = fy_start_year, 7
    while True:
        m_str = f"{curr_y}-{curr_m:02d}"
        trend_months.append((curr_y, curr_m, m_str))
        if curr_y == ref_y and curr_m == ref_m:
            break
        curr_m += 1
        if curr_m > 12:
            curr_m = 1
            curr_y += 1

    if len(trend_months) < 2:
        prev_m = 12 if curr_m == 1 else curr_m - 1
        prev_y = curr_y - 1 if curr_m == 1 else curr_y
        trend_months.insert(0, (prev_y, prev_m, f"{prev_y}-{prev_m:02d}"))

    # Track top tracked conditions for the trends chart
    tracked_trend_names = [t["test_name"] for t in surveillance_ledger[:6]] if surveillance_ledger else []

    monthly_trends = []
    for ty, tm, tmonth_str in trend_months:
        m_start = f"{tmonth_str}-01"
        if tm == 12:
            m_end = f"{ty}-12-31"
        else:
            m_end = (datetime.date(ty, tm + 1, 1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        cur.execute("""
            SELECT 
                to_ord.id AS order_id,
                t.name AS test_name
            FROM test_orders to_ord
            JOIN tests t ON to_ord.test_id = t.id
            WHERE to_ord.status = 'completed'
              AND t.is_tracked = 1
              AND t.parent_rollup_id IS NULL
              AND DATE(to_ord.ordered_at) >= ? AND DATE(to_ord.ordered_at) <= ?
        """, (m_start, m_end))
        m_orders = cur.fetchall()

        month_label = datetime.date(ty, tm, 1).strftime("%b %Y")
        month_entry = {"month_key": tmonth_str, "month_label": month_label, "total_positives": 0}
        
        for tn in tracked_trend_names:
            month_entry[tn] = 0

        for ord_row in m_orders:
            o_id = ord_row["order_id"]
            t_name = ord_row["test_name"]
            cur.execute("""
                SELECT tr.is_positive, tr.clinical_flag, tr.result_value, tp.parameter_name
                FROM test_results tr
                LEFT JOIN test_parameters tp ON tr.parameter_id = tp.id
                WHERE tr.order_id = ?
            """, (o_id,))
            ord_res = cur.fetchall()

            if is_order_surveillance_incident(t_name, ord_res):
                month_entry["total_positives"] += 1
                if t_name in month_entry:
                    month_entry[t_name] += 1
            
        monthly_trends.append(month_entry)

    return {
        "period": {
            "period_type": period_type,
            "formatted_period": formatted_period,
            "reference_date": ref_date.strftime("%Y-%m-%d"),
            "start_date": s_str,
            "end_date": e_str
        },
        "summary": {
            "total_evaluated": total_evaluated,
            "total_incident_cases": total_incident_cases,
            "overall_incidence_rate": overall_incidence_rate,
            "tracked_menu_count": len(orderable_tracked_map)
        },
        "sections_breakdown": sections_breakdown,
        "surveillance_ledger": surveillance_ledger,
        "wards_breakdown": wards_breakdown,
        "monthly_trends": {
            "conditions": tracked_trend_names,
            "trends": monthly_trends
        }
    }
