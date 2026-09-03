import json
import os
import datetime
import sqlite3
from typing import Optional, Dict, Any, List

# Load reference ranges fallback from JSON or defaults
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "reference_ranges.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        FALLBACK_REFERENCE_RANGES = json.load(f)
except FileNotFoundError:
    FALLBACK_REFERENCE_RANGES = {}

ALIAS_MAP = {
    "hemoglobin": "Hemoglobin (Hb)",
    "hb": "Hemoglobin (Hb)",
    "hemoglobin (hb)": "Hemoglobin (Hb)",
    "wbc": "WBC",
    "white blood cells": "WBC",
    "white blood cells (wbc)": "WBC",
    "total wbc count (white blood cells)": "Total WBC Count (White Blood Cells)",
    "fasting blood sugar": "Fasting Blood Sugar (FBS)",
    "fasting blood sugar (fbs)": "Fasting Blood Sugar (FBS)",
    "fbs": "Fasting Blood Sugar (FBS)",
    "fbs (fasting blood sugar)": "FBS (Fasting Blood Sugar)",
    "rbs": "RBS (Random Blood Sugar)",
    "random blood sugar": "RBS (Random Blood Sugar)",
    "rbs (random blood sugar)": "RBS (Random Blood Sugar)",
    "cd4 count": "Absolute CD4 Count (Cytometry)",
    "cd4": "Absolute CD4 Count (Cytometry)",
    "absolute cd4 count": "Absolute CD4 Count (Cytometry)",
    "cd4_quant": "Absolute CD4 Count (Cytometry)",
    "cd4 quant": "Absolute CD4 Count (Cytometry)",
    "cd4 count (cytometry)": "Absolute CD4 Count (Cytometry)",
    "cd4 count (rapid test strip)": "CD4 Count (Rapid Test Strip)",
    "cd4_rdt": "CD4 Count (Rapid Test Strip)",
    "cd4 rdt": "CD4 Count (Rapid Test Strip)",
    "visitect": "CD4 Count (Rapid Test Strip)",
    "visitect cd4": "CD4 Count (Rapid Test Strip)",
    "cd4 percentage": "CD4 Percentage",
    "cd4%": "CD4 Percentage",
}

def calculate_age(dob: datetime.date, entry_date: datetime.date) -> int:
    if not dob or not entry_date:
        return 0
    return entry_date.year - dob.year - ((entry_date.month, entry_date.day) < (dob.month, dob.day))

def _get_rules_from_db(param_name: str, db=None, unit: Optional[str] = None) -> tuple[Optional[str], List[Dict[str, Any]]]:
    """Queries reference_ranges table for rules matching parameter_name or aliases."""
    if not param_name:
        return None, []
    
    candidates = [param_name.strip()]
    alias_target = ALIAS_MAP.get(param_name.strip().lower())
    if alias_target and alias_target not in candidates:
        candidates.append(alias_target)

    # Inverted lookup for aliases
    for k, v in ALIAS_MAP.items():
        if v.lower() == param_name.strip().lower() and k not in [c.lower() for c in candidates]:
            candidates.append(k)

    rules = []
    matched_unit = unit

    conn = None
    should_close = False
    try:
        if db is not None:
            cur = db.cursor() if hasattr(db, "cursor") else db
        else:
            from .database import DB_PATH
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                should_close = True
            else:
                cur = None

        if cur is not None:
            placeholders = ",".join("?" for _ in candidates)
            sql = f"""
                SELECT parameter_name, age_min, age_max, sex, normal_min, normal_max, critical_min, critical_max, unit
                FROM reference_ranges
                WHERE LOWER(parameter_name) IN ({placeholders})
            """
            params = [c.lower() for c in candidates]
            if unit:
                sql += " AND (LOWER(unit) = LOWER(?) OR unit IS NULL)"
                params.append(unit.strip())
            sql += " ORDER BY id ASC"

            cur.execute(sql, params)
            rows = cur.fetchall()

            if not rows and unit:
                # Fallback if no rules matched the requested unit
                sql_fallback = f"""
                    SELECT parameter_name, age_min, age_max, sex, normal_min, normal_max, critical_min, critical_max, unit
                    FROM reference_ranges
                    WHERE LOWER(parameter_name) IN ({placeholders})
                    ORDER BY id ASC
                """
                cur.execute(sql_fallback, [c.lower() for c in candidates])
                rows = cur.fetchall()

            for r in rows:
                if not matched_unit and r["unit"]:
                    matched_unit = r["unit"]
                rules.append({
                    "age_min": r["age_min"] if r["age_min"] is not None else 0,
                    "age_max": r["age_max"] if r["age_max"] is not None else 999,
                    "sex": r["sex"],
                    "normal_min": r["normal_min"],
                    "normal_max": r["normal_max"],
                    "critical_min": r["critical_min"],
                    "critical_max": r["critical_max"],
                    "unit": r["unit"]
                })
    except Exception:
        rules = []
    finally:
        if should_close and conn:
            conn.close()

    return matched_unit, rules

def is_qualitative_abnormal(result_val: str, ref_val: str = None, param_name: str = None) -> bool:
    if not result_val:
        return False

    v_raw = str(result_val).strip()
    v_low = v_raw.lower()

    if param_name:
        p_low = str(param_name).strip().lower()
        if p_low in ["color", "colour"]:
            # Default normal color is yellow. All other colors are flagged abnormal.
            if v_low in ["", "nil", "negative", "yellow"]:
                return False
            return True
        if p_low == "turbidity":
            # Normal: clear, slightly turbid. Abnormal: turbid.
            if v_low in ["", "nil", "clear", "slightly turbid"]:
                return False
            if v_low == "turbid":
                return True
        if any(term in p_low for term in ["widal", "salmonella", "to", "th", "ao", "bh", "o antigen", "h antigen"]):
            if any(n in v_low for n in ["< 1:20", "<1:20", "1:20", "1:40", "not done", "negative", "nil", "not seen"]) and not any(t in v_low for t in ["1:80", "1:160", "1:320", "1:640", ">= 1:640", ">=1:640"]):
                return False
            if any(t in v_low for t in ["1:80", "1:160", "1:320", "1:640", ">= 1:640", ">=1:640"]) or "positive" in v_low or "reactive" in v_low:
                return True
        if any(term in p_low for term in ["afb", "tuberculosis", "sputum smear", "zn"]):
            if "negative" in v_low or "not seen" in v_low or "no bacilli" in v_low or "not done" in v_low:
                return False
            if any(k in v_low for k in ["scanty", "1+", "2+", "3+", "positive", "bacilli seen"]):
                return True

    # Normal exact matches
    normal_exact = {
        "nil", "negative", "not seen", "non-reactive", "non reactive",
        "clear", "slightly turbid", "normal", "yellow",
        "formed, no blood/mucus", "semi-formed, no blood/mucus",
        "no ova, cysts, or trophozoites seen", "hyaline casts (0-1 / lpf)",
        "1-2 / lpf", "3-4 / lpf", "few", "1.0 eu/dl", "normal (1.0 eu/dl)",
        "not done", "< 1:20", "<1:20", "1:20", "1:40",
        "negative (not detected)", "not detected", "no growth after 48 hours",
        "afb negative", "afb negative (no bacilli seen in 100 hpf)",
        "cd4 count: 200 cells/µl or above", "cd4 count: 200 cells/ul or above",
        "200 cells/µl or above", "200 cells/ul or above"
    }
    if v_low in normal_exact:
        return False

    if "below 200" in v_low:
        return True

    # Defensive check: if text clearly indicates non-reactivity / negativity
    if (v_low.startswith("non-reactive") or v_low.startswith("non reactive") or 
        (v_low.startswith("negative") and "positive" not in v_low) or
        "not detected" in v_low):
        return False

    # Explicit abnormal markers
    if (("positive" in v_low) or 
        ("reactive" in v_low and "non-reactive" not in v_low and "non reactive" not in v_low) or 
        ("abnormal" in v_low) or 
        ("detected" in v_low and "not detected" not in v_low) or 
        ("turbid" in v_low)):
        return True

    # Dipstick semiquantitative pluses or trace
    if any(p in v_low for p in ["trace", "1+", "2+", "3+", "4+", "(+)", "(++)", "(+++)", "(++++)"]):
        return True
    
    if any(p in v_low for p in ["small", "moderate", "large"]):
        if v_low not in ["nil", "negative", "not seen"]:
            return True

    # High cell counts, crystals, casts, parasites in microscopy
    if any(k in v_low for k in [
        ">15", "10-15", "5-10", "3-5", ">10",
        "cysts seen", "trophozoites seen", "ova seen", "casts", "crystals", "plenty",
        "blood present", "mucus present", "blood and mucus present"
    ]):
        if "not seen" in v_low or "no ova" in v_low:
            return False
        return True

    # If reference specifies negative/nil/not seen/non-reactive and result differs from it
    if ref_val:
        r_low = str(ref_val).strip().lower()
        if any(norm in r_low for norm in ["negative", "nil", "not seen", "non-reactive", "yellow"]):
            if v_low not in r_low:
                return True

    return False

def evaluate_result(test_name: str, result_value: str, dob: datetime.date = None, sex: str = None, entry_date: datetime.date = None, db=None, unit: Optional[str] = None) -> dict:
    if not test_name:
        return {
            "unit": None,
            "reference": None,
            "flag": None,
            "is_abnormal": False
        }

    unit, rules = _get_rules_from_db(test_name, db=db, unit=unit)

    # Fallback to json configuration if no db rules found
    if not rules:
        test_config = FALLBACK_REFERENCE_RANGES.get(test_name)
        if not test_config:
            alias_key = ALIAS_MAP.get(test_name.strip().lower())
            if alias_key:
                test_config = FALLBACK_REFERENCE_RANGES.get(alias_key)
        if test_config:
            if not unit:
                unit = test_config.get("unit")
            rules = test_config.get("rules", [])

    try:
        if result_value is None:
            val = None
        else:
            clean_str = str(result_value).strip().split()[0] if str(result_value).strip() else ""
            val = float(clean_str)
    except (ValueError, TypeError):
        val = None

    age = calculate_age(dob, entry_date) if (dob and entry_date) else None

    matched_rule = None
    for rule in rules:
        age_min = rule.get("age_min", 0)
        age_max = rule.get("age_max", 999)
        rule_sex = rule.get("sex")

        if age is not None:
            if not (age_min <= age <= age_max):
                continue

        if not rule_sex or (sex and rule_sex.lower() == sex.lower()):
            matched_rule = rule
            break

    if not matched_rule and rules:
        if age is None:
            for rule in rules:
                rule_sex = rule.get("sex")
                if not rule_sex or (sex and rule_sex.lower() == sex.lower()):
                    matched_rule = rule
                    break
            if not matched_rule:
                matched_rule = rules[0]

    ref_str = None
    if matched_rule:
        if not unit and matched_rule.get("unit"):
            unit = matched_rule.get("unit")
        n_min = matched_rule.get("normal_min")
        n_max = matched_rule.get("normal_max")
        c_min = matched_rule.get("critical_min")
        c_max = matched_rule.get("critical_max")

        if n_min is not None and n_max is not None:
            ref_str = f"{n_min} - {n_max}"
        elif n_min is not None:
            ref_str = f">= {n_min}"
        elif n_max is not None:
            ref_str = f"<= {n_max}"
    else:
        n_min = None
        n_max = None
        c_min = None
        c_max = None

    flag = None
    if val is not None:
        if c_min is not None and val < c_min:
            flag = "L*"
        elif c_max is not None and val > c_max:
            flag = "H*"
        elif n_min is not None and val < n_min:
            flag = "L"
        elif n_max is not None and val > n_max:
            flag = "H"

    t_low = (test_name or "").lower()
    # CD4 specific quantitative gate: < 200 is severe immunosuppression (AHD) -> L*
    if val is not None and ("cd4" in t_low or "cytometry" in t_low):
        if val < 200.0:
            flag = "L*"
        elif val < 500.0:
            flag = "L"

    # Qualitative abnormal findings check
    if not flag and result_value:
        res_low = str(result_value).strip().lower()
        if "below 200" in res_low and ("cd4" in t_low or "visitect" in t_low or "strip" in t_low or "rdt" in t_low):
            flag = "L*"
        elif "invalid" in res_low and ("cd4" in t_low or "rdt" in t_low):
            flag = "\u26A0"
        elif is_qualitative_abnormal(result_value, ref_str, test_name):
            flag = "\u26A0"

    is_abnormal = (flag is not None)

    return {
        "unit": unit,
        "reference": ref_str,
        "flag": flag,
        "is_abnormal": is_abnormal
    }


def evaluate_cd4_interpretation(test_name: str, result_value: str, age_months: Optional[int] = None, unit: Optional[str] = None) -> dict:
    """
    Evaluates clinical decision pathways and mandatory interpretive comments for CD4 assays.
    Supports Absolute CD4 Count (Cytometry), CD4 Count (Rapid Test Strip), and CD4 Percentage (<60 months).
    """
    t_clean = (test_name or "").strip().lower()
    val_clean = str(result_value or "").strip()
    
    # 1. Pediatric CD4% (< 60 months / < 5 years)
    if "percent" in t_clean or "%" in t_clean:
        try:
            val_num = float(val_clean.replace("%", "").strip().split()[0])
        except (ValueError, TypeError):
            val_num = None
            
        if val_num is not None and val_num < 25.0:
            return {
                "flag": "L*",
                "is_abnormal": True,
                "is_ahd": True,
                "is_invalid": False,
                "interpretive_comment": "CRITICAL ALERT: CD4 percentage is < 25% in pediatric client under 5 years, defining Pediatric Advanced HIV Disease (AHD). Immediate pediatric ART regimen escalation and opportunistic infection screening indicated.",
                "ahd_package_indicated": True
            }
        else:
            return {
                "flag": None,
                "is_abnormal": False,
                "is_ahd": False,
                "is_invalid": False,
                "interpretive_comment": "Pediatric CD4 percentage is >= 25%, indicating immunological stability above the advanced disease threshold.",
                "ahd_package_indicated": False
            }

    # 2. Semi-Quantitative Lateral-Flow RDT (e.g. VISITECT CD4)
    if "rapid" in t_clean or "rdt" in t_clean or "strip" in t_clean or "visitect" in t_clean:
        v_low = val_clean.lower()
        if "invalid" in v_low:
            return {
                "flag": "\u26A0",
                "is_abnormal": True,
                "is_ahd": False,
                "is_invalid": True,
                "interpretive_comment": "Invalid test run: Control line failed to develop. Result cannot be released. Repeat test with a new cassette.",
                "ahd_package_indicated": False
            }
        elif "below 200" in v_low:
            return {
                "flag": "L*",
                "is_abnormal": True,
                "is_ahd": True,
                "is_invalid": False,
                "interpretive_comment": "CRITICAL ALERT: Absolute CD4 T-cell count evaluated semi-quantitatively via lateral-flow rapid diagnostic test. Results indicate the client's CD4 count has fallen below the 200 cells/µL clinical threshold, defining Advanced HIV Disease (AHD). Immediately initiate the national AHD package of care, including Urine TB-LAM, Sputum GeneXpert, and Serum/CSF Cryptococcal Antigen (CrAg) lateral flow screening.",
                "ahd_package_indicated": True
            }
        else:
            return {
                "flag": None,
                "is_abnormal": False,
                "is_ahd": False,
                "is_invalid": False,
                "interpretive_comment": "Absolute CD4 T-cell count evaluated semi-quantitatively via lateral-flow rapid diagnostic test. CD4 count is confirmed to be at or above the 200 cells/µL decision limit.",
                "ahd_package_indicated": False
            }

    # 3. Quantitative POC Cytometry (e.g. Alere PIMA / BD FACSPresto)
    try:
        val_num = float(val_clean.split()[0])
    except (ValueError, TypeError):
        val_num = None

    if val_num is not None:
        if val_num < 200.0:
            return {
                "flag": "L*",
                "is_abnormal": True,
                "is_ahd": True,
                "is_invalid": False,
                "interpretive_comment": "CRITICAL ALERT: Absolute CD4 count is < 200 cells/µL, indicating severe immunological collapse and defining Advanced HIV Disease (AHD). Immediately initiate the national AHD package of care, including Urine TB-LAM, Sputum GeneXpert, and Serum Cryptococcal Antigen (CrAg) lateral flow screening.",
                "ahd_package_indicated": True
            }
        elif val_num < 500.0:
            return {
                "flag": "L",
                "is_abnormal": True,
                "is_ahd": False,
                "is_invalid": False,
                "interpretive_comment": "Absolute CD4 T-lymphocyte count indicates mild-to-moderate immunosuppression (200 - 499 cells/µL). Result is above the advanced disease threshold.",
                "ahd_package_indicated": False
            }
        else:
            return {
                "flag": None,
                "is_abnormal": False,
                "is_ahd": False,
                "is_invalid": False,
                "interpretive_comment": "Absolute CD4 T-lymphocyte count performed via automated point-of-care cytometry. Results indicate immunological stability above the advanced disease threshold.",
                "ahd_package_indicated": False
            }

    return {
        "flag": None,
        "is_abnormal": False,
        "is_ahd": False,
        "is_invalid": False,
        "interpretive_comment": "",
        "ahd_package_indicated": False
    }


def derive_hiv_outcome(kit_results: list | dict) -> dict:
    """
    Derives conclusive HIV diagnosis according to the Uganda MoH / UVRI 3-Test Algorithm:
    A1: MHS Kwiq Test / Determine (Screening)
    A2: HIV 1/2 Stat-Pak (Confirmatory)
    A3: SD Bioline / Uni-Gold (Tie-Breaker)
    Also supports HIVST self-tests and EID Molecular PCR protocols.
    """
    if isinstance(kit_results, dict):
        kit_map = {str(k).strip().lower(): str(v).strip() for k, v in kit_results.items()}
    elif isinstance(kit_results, list):
        kit_map = {}
        for item in kit_results:
            if isinstance(item, dict):
                k_name = str(item.get("name") or item.get("parameter_name") or "").strip().lower()
                k_res = str(item.get("result") if item.get("result") is not None else item.get("result_value", "")).strip()
                if k_name:
                    kit_map[k_name] = k_res
    else:
        kit_map = {}

    def is_pos_or_react(val: str) -> bool:
        v = str(val).strip().lower()
        if not v or v in ("not done", "none", "null", ""):
            return False
        if v.startswith("non-reactive") or v.startswith("non reactive") or "not detected" in v:
            return False
        return any(x in v for x in ("reactive", "positive", "detected"))

    def is_neg_or_non_react(val: str) -> bool:
        v = str(val).strip().lower()
        if not v or v in ("not done", "none", "null", ""):
            return False
        return any(x in v for x in ("non-reactive", "non reactive", "negative", "not detected"))

    # 1. Check EID Molecular PCR protocols (if passed directly)
    eid_keys = [k for k in kit_map if "pcr" in k or "eid" in k]
    if eid_keys:
        eid_pos = any(is_pos_or_react(kit_map[k]) for k in eid_keys)
        eid_neg = any(is_neg_or_non_react(kit_map[k]) for k in eid_keys)
        if eid_pos:
            return {
                "conclusive_status": "Positive",
                "display_result": "Positive",
                "clinical_flag": "\u26A0",
                "reference": "Negative",
                "advisory": "Infant HIV DNA/RNA detected. Immediate pediatric ART referral recommended."
            }
        elif eid_neg:
            return {
                "conclusive_status": "Negative",
                "display_result": "Negative",
                "clinical_flag": None,
                "reference": "Negative",
                "advisory": "No infant HIV DNA/RNA detected on current PCR run."
            }

    # 2. Check HIVST Self-Tests (if only HIVST tested)
    hivst_keys = [k for k in kit_map if "oraquick" in k or "self-test" in k or "hivst" in k]
    rdt_keys = [k for k in kit_map if any(x in k for x in ("kwiq", "determine", "stat-pak", "statpak", "bioline", "uni-gold"))]
    
    if hivst_keys and not any(is_pos_or_react(kit_map[k]) or is_neg_or_non_react(kit_map[k]) for k in rdt_keys):
        if any(is_pos_or_react(kit_map[k]) for k in hivst_keys):
            return {
                "conclusive_status": "Inconclusive",
                "display_result": "Inconclusive",
                "clinical_flag": "\u26A0",
                "reference": "Negative",
                "advisory": "Self-test is screening only. Must undergo full 3-test clinical algorithm before ART."
            }
        elif any(is_neg_or_non_react(kit_map[k]) for k in hivst_keys):
            return {
                "conclusive_status": "Negative",
                "display_result": "Negative",
                "clinical_flag": None,
                "reference": "Negative",
                "advisory": "Routine prevention counseling recommended."
            }

    # 3. Standard Ugandan National 3-Test RDT Algorithm
    a1_val = None
    for k, v in kit_map.items():
        if any(x in k for x in ("kwiq", "determine")):
            if v and v.lower() != "not done":
                a1_val = v
                break

    a2_val = None
    for k, v in kit_map.items():
        if any(x in k for x in ("stat-pak", "statpak")):
            if v and v.lower() != "not done":
                a2_val = v
                break

    a3_val = None
    for k, v in kit_map.items():
        if any(x in k for x in ("bioline", "uni-gold")):
            if v and v.lower() != "not done":
                a3_val = v
                break

    if not a1_val and not a2_val and not a3_val:
        raw_vals = [v for v in kit_map.values() if v and v.lower() != "not done"]
        if any(is_pos_or_react(v) for v in raw_vals):
            return {
                "conclusive_status": "Positive",
                "display_result": "Positive",
                "clinical_flag": "\u26A0",
                "reference": "Negative",
                "advisory": "Reactive antibody finding."
            }
        else:
            return {
                "conclusive_status": "Negative",
                "display_result": "Negative",
                "clinical_flag": None,
                "reference": "Negative",
                "advisory": "Routine prevention counseling recommended."
            }

    a1_pos = is_pos_or_react(a1_val) if a1_val else False
    a2_pos = is_pos_or_react(a2_val) if a2_val else False
    a3_pos = is_pos_or_react(a3_val) if a3_val else False

    # A1 Non-Reactive -> Final Negative
    if a1_val and not a1_pos:
        return {
            "conclusive_status": "Negative",
            "display_result": "Negative",
            "clinical_flag": None,
            "reference": "Negative",
            "advisory": "Screening test non-reactive. Routine prevention counseling recommended."
        }

    # A1 Reactive
    if a1_pos:
        if a2_val is not None:
            if a2_pos:
                if a3_val is not None:
                    if a3_pos:
                        # Concordant Positive: A1+, A2+, A3+
                        return {
                            "conclusive_status": "Positive",
                            "display_result": "Positive",
                            "clinical_flag": "\u26A0",
                            "reference": "Negative",
                            "advisory": "Concordant 3-test reactive. Refer to ART clinic for baseline CD4/VL."
                        }
                    else:
                        # Inconclusive: A1+, A2+, A3-
                        return {
                            "conclusive_status": "Inconclusive",
                            "display_result": "Inconclusive",
                            "clinical_flag": "\u26A0",
                            "reference": "Negative",
                            "advisory": "Discrepant antibody pattern. Do NOT initiate ART. Repeat blood draw in 14 days."
                        }
                else:
                    # A1+ and A2+ entered, A3 pending / not done
                    return {
                        "conclusive_status": "Positive",
                        "display_result": "Positive",
                        "clinical_flag": "\u26A0",
                        "reference": "Negative",
                        "advisory": "Concordant reactive screening and confirmatory tests."
                    }
            else:
                # A1+ and A2-
                if a3_val is not None:
                    if not a3_pos:
                        # Discordant resolved negative: A1+, A2-, A3-
                        return {
                            "conclusive_status": "Negative",
                            "display_result": "Negative",
                            "clinical_flag": None,
                            "reference": "Negative",
                            "advisory": "Discordance resolved negative (A2 & A3 non-reactive)."
                        }
                    else:
                        # Inconclusive: A1+, A2-, A3+
                        return {
                            "conclusive_status": "Inconclusive",
                            "display_result": "Inconclusive",
                            "clinical_flag": "\u26A0",
                            "reference": "Negative",
                            "advisory": "Discrepant antibody pattern (Stat-Pak negative). Repeat blood draw in 14 days."
                        }
                else:
                    # A1+ and A2-, A3 pending
                    return {
                        "conclusive_status": "Inconclusive",
                        "display_result": "Inconclusive",
                        "clinical_flag": "\u26A0",
                        "reference": "Negative",
                        "advisory": "Discordant screening/confirmation. Perform tie-breaker test (SD Bioline / Uni-Gold)."
                    }

    return {
        "conclusive_status": "Negative",
        "display_result": "Negative",
        "clinical_flag": None,
        "reference": "Negative",
        "advisory": "Routine prevention counseling recommended."
    }




