import sqlite3
import datetime
from typing import Optional, Dict, Any

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

def format_reporting_period(period_type: str, ref_date: datetime.date) -> str:
    """Formats period directly without unnecessary verbose labels."""
    m, y, d = ref_date.month, ref_date.year, ref_date.day
    if period_type == "Month":
        return ref_date.strftime("%B, %Y")
    elif period_type == "Week":
        week_num = (d - 1) // 7 + 1
        return f"Week {week_num}, {ref_date.strftime('%B, %Y')}"
    elif period_type == "Day":
        return ref_date.strftime("%d-%m-%Y")
    elif period_type == "Quarter":
        if m in [7, 8, 9]: return f"Qtr 1, {y}/{str(y + 1)[-2:]}"
        elif m in [10, 11, 12]: return f"Qtr 2, {y}/{str(y + 1)[-2:]}"
        elif m in [1, 2, 3]: return f"Qtr 3, {y - 1}/{str(y)[-2:]}"
        else: return f"Qtr 4, {y - 1}/{str(y)[-2:]}"
    elif period_type == "Half-Year":
        if m >= 7: return f"H1, {y}/{str(y + 1)[-2:]}"
        else: return f"H2, {y - 1}/{str(y)[-2:]}"
    elif period_type == "Financial Year":
        if m >= 7: return f"FY {y}/{str(y + 1)[-2:]}"
        else: return f"FY {y - 1}/{str(y)[-2:]}"
    else:
        return str(y)

def calculate_operations_metrics(
    conn: sqlite3.Connection,
    period_type: str = "Month",
    reference_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates deterministic AMH Laboratory Operations & Performance metrics.
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

    # Query completed orders within the target period
    cur.execute("""
        SELECT 
            to_ord.id AS order_id,
            to_ord.visit_id,
            to_ord.test_id,
            to_ord.ordered_at,
            to_ord.order_category,
            t.name AS test_name,
            t.parent_rollup_id,
            s.id AS section_id,
            s.name AS section_name,
            v.ward_of_origin,
            MIN(tr.entered_at) AS min_entered_at,
            MAX(tr.verified_at) AS max_verified_at
        FROM test_orders to_ord
        JOIN tests t ON to_ord.test_id = t.id
        JOIN sections s ON t.section_id = s.id
        JOIN visits v ON to_ord.visit_id = v.id
        LEFT JOIN test_results tr ON tr.order_id = to_ord.id
        WHERE to_ord.status = 'completed'
          AND v.is_deleted = 0
          AND DATE(to_ord.ordered_at) >= ?
          AND DATE(to_ord.ordered_at) <= ?
        GROUP BY to_ord.id
        ORDER BY to_ord.ordered_at
    """, (s_str, e_str))
    order_rows = cur.fetchall()

    total_done = len(order_rows)
    distinct_visits = set()

    # Section accumulators
    cur.execute("SELECT id, name FROM sections ORDER BY sort_order, id")
    all_sections = cur.fetchall()
    section_stats: Dict[int, Dict[str, Any]] = {
        sec["id"]: {
            "section_id": sec["id"],
            "section_name": sec["name"],
            "test_count": 0,
            "tats": [],
            "on_time_count": 0
        }
        for sec in all_sections
    }

    # Ward of origin accumulators
    ward_counts: Dict[str, int] = {}

    # Category accumulators (In-House, Referral, Outreach)
    category_counts: Dict[str, int] = {
        "In-House": 0,
        "Referral": 0,
        "Outreach": 0
    }

    # Test count tallies for demand ranking
    test_order_tallies: Dict[int, Dict[str, Any]] = {}

    for row in order_rows:
        distinct_visits.add(row["visit_id"])

        sec_id = row["section_id"]
        sec_name = row["section_name"] or ""
        test_id = row["test_id"]
        test_name = row["test_name"] or ""
        order_cat = (row["order_category"] or "in-house").lower()
        w_origin = row["ward_of_origin"] or "Outpatient / GOPD"

        # Tally Ward of Origin
        ward_counts[w_origin] = ward_counts.get(w_origin, 0) + 1

        # Tally Category
        if "ref" in order_cat:
            cat_key = "Referral"
        elif "outreach" in order_cat:
            cat_key = "Outreach"
        else:
            cat_key = "In-House"
        category_counts[cat_key] += 1

        # Tally Section
        if sec_id in section_stats:
            section_stats[sec_id]["test_count"] += 1
        else:
            section_stats[sec_id] = {
                "section_id": sec_id,
                "section_name": sec_name,
                "test_count": 1,
                "tats": [],
                "on_time_count": 0
            }

        # Tally test demand (respecting parent tests)
        if test_id not in test_order_tallies:
            test_order_tallies[test_id] = {
                "test_id": test_id,
                "test_name": test_name,
                "section_name": sec_name,
                "count": 0
            }
        test_order_tallies[test_id]["count"] += 1

        # Determine benchmark
        if "microbiology" in sec_name.lower() or "culture" in sec_name.lower():
            sla_benchmark = 2880.0
        else:
            sla_benchmark = 120.0

        # Compute TAT
        ordered_at = row["ordered_at"]
        entered_at = row["min_entered_at"]
        if ordered_at and entered_at:
            cur.execute("SELECT (julianday(?) - julianday(?)) * 1440.0 AS diff_mins", (entered_at, ordered_at))
            diff_row = cur.fetchone()
            if diff_row and diff_row["diff_mins"] is not None:
                tat_val = max(0.0, float(diff_row["diff_mins"]))
                section_stats[sec_id]["tats"].append(tat_val)
                if tat_val <= sla_benchmark:
                    section_stats[sec_id]["on_time_count"] += 1

    # Menu coverage: Query parent / standalone orderable tests only (parent_rollup_id IS NULL)
    cur.execute("""
        SELECT 
            s.id AS section_id,
            s.name AS section_name,
            t.id AS test_id,
            t.name AS test_name
        FROM tests t
        JOIN sections s ON t.section_id = s.id
        WHERE t.is_active = 1 AND t.parent_rollup_id IS NULL
        ORDER BY s.sort_order, s.id, t.name
    """)
    all_orderable_catalog = cur.fetchall()
    total_active_menu_items = len(all_orderable_catalog) if all_orderable_catalog else 1
    
    orderable_test_ids = {t["test_id"] for t in all_orderable_catalog}
    unique_orderable_ordered = len([tid for tid in test_order_tallies.keys() if tid in orderable_test_ids])
    menu_coverage_rate = round((unique_orderable_ordered / total_active_menu_items) * 100.0, 1)

    # Categories breakdown list
    categories_breakdown = []
    for c_name in ["In-House", "Referral", "Outreach"]:
        c_cnt = category_counts.get(c_name, 0)
        c_pct = round((c_cnt / total_done) * 100.0, 1) if total_done > 0 else 0.0
        categories_breakdown.append({
            "category": c_name,
            "count": c_cnt,
            "percentage": c_pct
        })

    # Demand Dynamics:
    # 1. Top 5 Most Requested (count >= 1, sorted desc)
    ordered_orderable_tests = [t for tid, t in test_order_tallies.items() if t["count"] >= 1 and tid in orderable_test_ids]
    sorted_desc = sorted(ordered_orderable_tests, key=lambda x: x["count"], reverse=True)
    top_5_requested = sorted_desc[:5]

    # 2. Bottom 5 Least Requested (count >= 1, sorted asc)
    sorted_asc = sorted(ordered_orderable_tests, key=lambda x: x["count"])
    bottom_5_requested = sorted_asc[:5]

    # 3. Tests Not Requested (active orderable tests in catalog with count == 0)
    ordered_ids_set = set(test_order_tallies.keys())
    unrequested_tests = [
        {
            "test_id": t["test_id"],
            "test_name": t["test_name"],
            "section_name": t["section_name"],
            "count": 0
        }
        for t in all_orderable_catalog if t["test_id"] not in ordered_ids_set
    ]

    # 4. Appendix: Complete Diagnostic Menu Activity (Orderable Tests only)
    appendix_menu_activity = []
    for t in all_orderable_catalog:
        tid = t["test_id"]
        cnt = test_order_tallies.get(tid, {}).get("count", 0)
        appendix_menu_activity.append({
            "section_name": t["section_name"],
            "test_name": t["test_name"],
            "completed_count": cnt
        })

    # Section breakdown list
    sections_breakdown = []
    for s_id, s_info in section_stats.items():
        s_count = s_info["test_count"]
        pct = round((s_count / total_done) * 100.0, 1) if total_done > 0 else 0.0
        tats = s_info["tats"]
        if tats:
            avg_tat = round(sum(tats) / len(tats), 1)
            min_tat = round(min(tats), 1)
            max_tat = round(max(tats), 1)
            sla_pct = round((s_info["on_time_count"] / len(tats)) * 100.0, 1)
        else:
            avg_tat = 0.0
            min_tat = 0.0
            max_tat = 0.0
            sla_pct = 100.0

        sections_breakdown.append({
            "section_id": s_id,
            "section_name": s_info["section_name"],
            "test_count": s_count,
            "volume_percentage": pct,
            "avg_tat_mins": avg_tat,
            "min_tat_mins": min_tat,
            "max_tat_mins": max_tat,
            "sla_compliance_percent": sla_pct
        })

    # Ward of Origin breakdown list
    wards_breakdown = []
    for w_name, w_cnt in sorted(ward_counts.items(), key=lambda x: x[1], reverse=True):
        w_pct = round((w_cnt / total_done) * 100.0, 1) if total_done > 0 else 0.0
        wards_breakdown.append({
            "ward": w_name,
            "count": w_cnt,
            "percentage": w_pct
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

    monthly_trends = []
    for ty, tm, tmonth_str in trend_months:
        m_start = f"{tmonth_str}-01"
        if tm == 12:
            m_end = f"{ty}-12-31"
        else:
            m_end = (datetime.date(ty, tm + 1, 1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        cur.execute("""
            SELECT s.id as section_id, s.name as section_name, COUNT(to_ord.id) as count_done
            FROM test_orders to_ord
            JOIN tests t ON to_ord.test_id = t.id
            JOIN sections s ON t.section_id = s.id
            WHERE to_ord.status = 'completed'
              AND DATE(to_ord.ordered_at) >= ? AND DATE(to_ord.ordered_at) <= ?
            GROUP BY s.id, s.name
        """, (m_start, m_end))
        m_results = {r["section_name"]: r["count_done"] for r in cur.fetchall()}

        month_label = datetime.date(ty, tm, 1).strftime("%b %Y")
        month_entry = {"month_key": tmonth_str, "month_label": month_label, "total": 0}
        
        for sec in all_sections:
            sec_name = sec["name"]
            v = m_results.get(sec_name, 0)
            month_entry[sec_name] = v
            month_entry["total"] += v
            
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
            "total_done": total_done,
            "total_clients": len(distinct_visits),
            "menu_coverage_percent": menu_coverage_rate,
            "total_active_menu_items": total_active_menu_items,
            "unique_tests_ordered": unique_orderable_ordered
        },
        "categories_breakdown": categories_breakdown,
        "sections_breakdown": sections_breakdown,
        "wards_breakdown": wards_breakdown,
        "demand_dynamics": {
            "top_requested_tests": top_5_requested,
            "least_requested_tests": bottom_5_requested,
            "unrequested_tests": unrequested_tests
        },
        "appendix_menu_activity": appendix_menu_activity,
        "monthly_trends": {
            "sections": [s["name"] for s in all_sections],
            "trends": monthly_trends
        }
    }
