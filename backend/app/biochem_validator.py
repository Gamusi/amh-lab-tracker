from typing import Optional, Dict, Any, Tuple, List
from .evaluator import ALIAS_MAP, is_qualitative_abnormal

# Exact molecular / valence conversion factors from AMH biochemistry specifications
CONVERSION_FACTORS_TO_SI = {
    # parameter_name_lower: { from_unit_lower: factor_to_multiply }
    "serum creatinine": {"mg/dl": 88.4}, # to µmol/L
    "serum urea": {"mg/dl": 0.357}, # to mmol/L
    "serum uric acid": {"mg/dl": 59.5}, # to µmol/L
    "serum potassium (k+)": {"meq/l": 1.0}, # to mmol/L
    "serum sodium (na+)": {"meq/l": 1.0}, # to mmol/L
    "serum chloride (cl-)": {"meq/l": 1.0}, # to mmol/L
    "bicarbonate (hco3-)": {"meq/l": 1.0}, # to mmol/L
    "total calcium (ca2+)": {"mg/dl": 0.25, "meq/l": 0.50}, # to mmol/L
    "calcium (ca2+)": {"mg/dl": 0.25, "meq/l": 0.50},
    "magnesium (mg2+)": {"mg/dl": 0.4114, "meq/l": 0.50}, # to mmol/L
    "phosphate (po4)": {"mg/dl": 0.323}, # to mmol/L
    "total bilirubin": {"mg/dl": 17.1}, # to µmol/L
    "direct bilirubin": {"mg/dl": 17.1}, # to µmol/L
    "total protein": {"g/dl": 10.0}, # to g/L
    "serum albumin": {"g/dl": 10.0}, # to g/L
    "alt / sgpt (alanine aminotransferase)": {"u/l": 0.0167, "iu/l": 0.0167}, # to µkat/L
    "ast / sgot (aspartate aminotransferase)": {"u/l": 0.0167, "iu/l": 0.0167}, # to µkat/L
    "alkaline phosphatase (alp)": {"u/l": 0.0167, "iu/l": 0.0167}, # to µkat/L
    "gamma-glutamyl transferase (ggt)": {"u/l": 0.0167, "iu/l": 0.0167}, # to µkat/L
    "total cholesterol": {"mg/dl": 0.0259}, # to mmol/L
    "triglycerides": {"mg/dl": 0.0113}, # to mmol/L
    "hdl cholesterol": {"mg/dl": 0.0259}, # to mmol/L
    "ldl cholesterol": {"mg/dl": 0.0259}, # to mmol/L
    "total ck (creatine kinase)": {"u/l": 0.0167, "iu/l": 0.0167}, # to µkat/L
    "ck-mb (creatine kinase-mb)": {"u/l": 0.0167, "iu/l": 0.0167}, # to µkat/L
    "troponin i (ctni)": {"ng/ml": 1.0}, # to µg/L
    "myoglobin": {"ng/ml": 1.0}, # to µg/L
    "fbs (fasting blood sugar)": {"mg/dl": 0.0555}, # to mmol/L
    "fasting blood sugar (fbs)": {"mg/dl": 0.0555},
    "rbs (random blood sugar)": {"mg/dl": 0.0555}, # to mmol/L
    "random blood sugar (rbs)": {"mg/dl": 0.0555}
}

def to_si_value(param_name: str, val: float, unit: Optional[str]) -> float:
    """Converts a parameter value to standard SI units if conventional unit given."""
    if not unit or val is None:
        return val
    p_key = param_name.strip().lower()
    alias = ALIAS_MAP.get(p_key)
    if alias:
        p_key = alias.lower()
    
    u_key = unit.strip().lower()
    conversions = CONVERSION_FACTORS_TO_SI.get(p_key, {})
    factor = conversions.get(u_key)
    if factor:
        return val * factor
    return val

def _find_matching_rule(conn_or_cur, param_name: str, age: Optional[int] = None, sex: Optional[str] = None, unit: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Look up the most specific matching rule from reference_ranges table in SQLite."""
    cur = conn_or_cur.cursor() if hasattr(conn_or_cur, "cursor") else conn_or_cur
    
    candidates = [param_name.strip()]
    alias_target = ALIAS_MAP.get(param_name.strip().lower())
    if alias_target and alias_target not in candidates:
        candidates.append(alias_target)

    for k, v in ALIAS_MAP.items():
        if v.lower() == param_name.strip().lower() and k not in [c.lower() for c in candidates]:
            candidates.append(k)

    placeholders = ",".join("?" for _ in candidates)
    query = f"""
        SELECT id, test_id, parameter_name, age_min, age_max, sex,
               normal_min, normal_max, critical_min, critical_max,
               sanity_min, sanity_max, plausible_min, plausible_max, unit
        FROM reference_ranges
        WHERE LOWER(parameter_name) IN ({placeholders})
    """
    params: List[Any] = [c.lower() for c in candidates]
    
    if unit:
        query += " AND (LOWER(unit) = LOWER(?) OR unit IS NULL)"
        params.append(unit.strip())

    query += " ORDER BY id ASC"
    cur.execute(query, params)
    raw_rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = [dict(zip(cols, row)) if isinstance(row, (tuple, list)) else dict(row) for row in raw_rows]
    
    if not rows and unit:
        # Fallback without unit constraint if none matched
        query_fallback = f"""
            SELECT id, test_id, parameter_name, age_min, age_max, sex,
                   normal_min, normal_max, critical_min, critical_max,
                   sanity_min, sanity_max, plausible_min, plausible_max, unit
            FROM reference_ranges
            WHERE LOWER(parameter_name) IN ({placeholders})
            ORDER BY id ASC
        """
        cur.execute(query_fallback, [c.lower() for c in candidates])
        raw_fallback = cur.fetchall()
        cols_fallback = [d[0] for d in cur.description] if cur.description else cols
        rows = [dict(zip(cols_fallback, row)) if isinstance(row, (tuple, list)) else dict(row) for row in raw_fallback]

    if not rows:
        from .seed import DEFAULT_REFERENCE_RANGES
        c_lowers = [c.lower() for c in candidates]
        fallback_rows = []
        for item in DEFAULT_REFERENCE_RANGES:
            pname, a_min, a_max, s_sex, n_min, n_max, c_min, c_max, s_min, s_max, p_min, p_max, r_unit = item
            if pname.lower() in c_lowers:
                if unit and r_unit and unit.lower() != r_unit.lower():
                    continue
                fallback_rows.append({
                    "id": None, "test_id": None, "parameter_name": pname,
                    "age_min": a_min, "age_max": a_max, "sex": s_sex,
                    "normal_min": n_min, "normal_max": n_max,
                    "critical_min": c_min, "critical_max": c_max,
                    "sanity_min": s_min, "sanity_max": s_max,
                    "plausible_min": p_min, "plausible_max": p_max,
                    "unit": r_unit
                })
        rows = fallback_rows

    if not rows:
        return None

    matched = None
    # 1. Exact demographic match (age & sex)
    for r in rows:
        r_age_min = r["age_min"] if r["age_min"] is not None else 0
        r_age_max = r["age_max"] if r["age_max"] is not None else 999
        r_sex = r["sex"]

        if age is not None:
            if not (r_age_min <= age <= r_age_max):
                continue
        if r_sex and sex:
            if r_sex.lower() != sex.lower():
                continue
        elif r_sex and not sex:
            continue

        matched = dict(r)
        break

    # 2. Relax sex if no exact match
    if not matched:
        for r in rows:
            r_age_min = r["age_min"] if r["age_min"] is not None else 0
            r_age_max = r["age_max"] if r["age_max"] is not None else 999
            if age is not None and not (r_age_min <= age <= r_age_max):
                continue
            matched = dict(r)
            break

    # 3. Fallback to first rule
    if not matched and rows:
        matched = dict(rows[0])

    return matched

def validate_biochem_parameter(
    conn_or_cur,
    param_name: str,
    val_str: Optional[str],
    age: Optional[int] = None,
    sex: Optional[str] = None,
    unit: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates a biochemical parameter against database-backed reference ranges and sanity limits.
    Raises ValueError if value breaches physiological sanity boundaries.
    Returns evaluated reference range string, clinical flag, and abnormal boolean.
    """
    if not param_name or val_str is None or str(val_str).strip() == "":
        return {
            "unit": unit,
            "reference": None,
            "flag": None,
            "is_abnormal": False
        }

    val_clean = str(val_str).strip()
    try:
        # Extract leading numeric portion
        val_numeric_str = val_clean.split()[0]
        val = float(val_numeric_str)
    except (ValueError, TypeError):
        val = None

    rule = _find_matching_rule(conn_or_cur, param_name, age=age, sex=sex, unit=unit)
    
    effective_unit = unit or (rule.get("unit") if rule else None)
    
    # 1. Sanity Limits Check
    if val is not None and rule:
        s_min = rule.get("sanity_min")
        s_max = rule.get("sanity_max")
        
        if s_min is not None and val < s_min:
            unit_display = f" {effective_unit}" if effective_unit else ""
            bounds_display = f"{s_min} - {s_max}" if s_max is not None else f">= {s_min}"
            raise ValueError(
                f"Value for {param_name} ({val}{unit_display}) breaches physiological sanity limits ({bounds_display}). "
                f"Check specimen for dilution/contamination."
            )
        if s_max is not None and val > s_max:
            unit_display = f" {effective_unit}" if effective_unit else ""
            bounds_display = f"{s_min} - {s_max}" if s_min is not None else f"<= {s_max}"
            raise ValueError(
                f"Value for {param_name} ({val}{unit_display}) breaches physiological sanity limits ({bounds_display}). "
                f"Check specimen for dilution/contamination."
            )

    # 2. Compute reference interval text
    ref_str = None
    flag = None
    is_abnormal = False

    if rule:
        n_min = rule.get("normal_min")
        n_max = rule.get("normal_max")
        c_min = rule.get("critical_min")
        c_max = rule.get("critical_max")

        if n_min is not None and n_max is not None:
            ref_str = f"{n_min} - {n_max}"
        elif n_min is not None:
            ref_str = f">= {n_min}"
        elif n_max is not None:
            ref_str = f"<= {n_max}"

        if val is not None:
            if c_min is not None and val < c_min:
                flag = "L*"
            elif c_max is not None and val > c_max:
                flag = "H*"
            elif n_min is not None and val < n_min:
                flag = "L"
            elif n_max is not None and val > n_max:
                flag = "H"

    # 3. Diabetic and Hypoglycemic Alerts for Blood Sugars
    p_lower = param_name.strip().lower()
    if val is not None and ("glucose" in p_lower or "blood sugar" in p_lower or "fbs" in p_lower or "rbs" in p_lower):
        u_lower = (effective_unit or "").strip().lower()
        if "mg/dl" in u_lower:
            if "fbs" in p_lower or "fasting" in p_lower:
                if val > 126.0 and flag not in ["H*"]:
                    flag = "H*"
                elif val < 50.0 and flag not in ["L*"]:
                    flag = "L*"
            elif "rbs" in p_lower or "random" in p_lower:
                if val > 200.0 and flag not in ["H*"]:
                    flag = "H*"
                elif val < 50.0 and flag not in ["L*"]:
                    flag = "L*"
        else: # mmol/L default
            if "fbs" in p_lower or "fasting" in p_lower:
                if val > 7.0 and flag not in ["H*"]:
                    flag = "H*"
                elif val < 2.8 and flag not in ["L*"]:
                    flag = "L*"
            elif "rbs" in p_lower or "random" in p_lower:
                if val > 11.1 and flag not in ["H*"]:
                    flag = "H*"
                elif val < 2.8 and flag not in ["L*"]:
                    flag = "L*"

    # 4. Qualitative Abnormal Finding Flag
    if not flag and val_clean:
        if is_qualitative_abnormal(val_clean, ref_str, param_name):
            flag = "\u26A0"

    # 4. CD4 and Qualitative Abnormal Findings
    if not flag and val_clean:
        v_low = val_clean.lower()
        if "below 200" in v_low and ("cd4" in p_lower or "visitect" in p_lower):
            flag = "L*"
        elif "invalid" in v_low and ("cd4" in p_lower or "visitect" in p_lower):
            flag = "\u26A0"
        elif is_qualitative_abnormal(val_clean, ref_str, param_name):
            flag = "\u26A0"

    is_abnormal = (flag is not None)

    return {
        "unit": effective_unit,
        "reference": ref_str,
        "flag": flag,
        "is_abnormal": is_abnormal
    }

def validate_panel_consistency(param_values_map: Dict[str, Tuple[Any, Optional[str]]]) -> None:
    """
    Enforces hard clinical and mathematical consistency across multi-parameter panels.
    param_values_map: { parameter_name: (numeric_or_string_val, unit) }
    Raises ValueError on mathematically impossible or contaminated combinations.
    """
    norm_map: Dict[str, Tuple[float, Optional[str]]] = {}
    for k, (v, u) in param_values_map.items():
        if v is None or v == "":
            continue
        try:
            val_clean = str(v).strip().split()[0]
            val_num = float(val_clean)
            norm_map[k.strip().lower()] = (val_num, u)
            # Add alias if any
            alias = ALIAS_MAP.get(k.strip().lower())
            if alias:
                norm_map[alias.lower()] = (val_num, u)
        except (ValueError, TypeError):
            continue

    def get_val(key_fragment: str) -> Optional[Tuple[float, Optional[str]]]:
        for k, pair in norm_map.items():
            if key_fragment in k:
                return pair
        return None

    # 1. Direct Bilirubin <= Total Bilirubin
    tot_bili = get_val("total bilirubin")
    dir_bili = get_val("direct bilirubin")
    if tot_bili is not None and dir_bili is not None:
        tb_val, tb_u = tot_bili
        db_val, db_u = dir_bili
        # convert both to µmol/L for comparison
        tb_si = to_si_value("Total Bilirubin", tb_val, tb_u)
        db_si = to_si_value("Direct Bilirubin", db_val, db_u)
        if db_si > tb_si + 1e-5:
            raise ValueError(
                f"Direct (Conjugated) Bilirubin cannot exceed Total Bilirubin. "
                f"Entered: Direct={db_val} {db_u or ''}, Total={tb_val} {tb_u or ''}."
            )

    # 2. LDL Cholesterol <= Total Cholesterol
    tot_chol = get_val("total cholesterol")
    ldl_chol = get_val("ldl cholesterol")
    if tot_chol is not None and ldl_chol is not None:
        tc_val, tc_u = tot_chol
        ldl_val, ldl_u = ldl_chol
        tc_si = to_si_value("Total Cholesterol", tc_val, tc_u)
        ldl_si = to_si_value("LDL Cholesterol", ldl_val, ldl_u)
        if ldl_si > tc_si + 1e-5:
            raise ValueError(
                f"LDL Cholesterol cannot exceed Total Cholesterol. "
                f"Entered: LDL={ldl_val} {ldl_u or ''}, Total={tc_val} {tc_u or ''}."
            )

    # 3. CK-MB <= Total CK
    tot_ck = get_val("total ck")
    ck_mb = get_val("ck-mb")
    if tot_ck is not None and ck_mb is not None:
        tck_val, tck_u = tot_ck
        ckmb_val, ckmb_u = ck_mb
        tck_si = to_si_value("Total CK (Creatine Kinase)", tck_val, tck_u)
        ckmb_si = to_si_value("CK-MB (Creatine Kinase-MB)", ckmb_val, ckmb_u)
        if ckmb_si > tck_si + 1e-5:
            raise ValueError(
                f"CK-MB fraction cannot exceed Total CK activity. "
                f"Entered: CK-MB={ckmb_val} {ckmb_u or ''}, Total CK={tck_val} {tck_u or ''}."
            )

    # 4. EDTA Tube Contamination (Potassium > 10.0 mmol/L and Calcium < 0.5 mmol/L)
    k_item = get_val("potassium")
    ca_item = get_val("calcium")
    if k_item is not None and ca_item is not None:
        k_val, k_u = k_item
        ca_val, ca_u = ca_item
        k_si = to_si_value("Serum Potassium (K+)", k_val, k_u)
        ca_si = to_si_value("Total Calcium (Ca2+)", ca_val, ca_u)
        if k_si > 10.0 and ca_si < 0.5:
            raise ValueError(
                f"EDTA tube contamination detected: Potassium > 10.0 mmol/L ({k_val} {k_u or 'mmol/L'}) "
                f"paired with chelated Calcium < 0.5 mmol/L ({ca_val} {ca_u or 'mmol/L'}). Sample rejected."
            )
