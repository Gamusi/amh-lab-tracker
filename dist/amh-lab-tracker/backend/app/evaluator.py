import json
import os
import datetime

# Load reference ranges once globally
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "reference_ranges.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        REFERENCE_RANGES = json.load(f)
except FileNotFoundError:
    REFERENCE_RANGES = {}

ALIAS_MAP = {
    "hemoglobin": "Hemoglobin (Hb)",
    "hb": "Hemoglobin (Hb)",
    "hemoglobin (hb)": "Hemoglobin (Hb)",
    "wbc": "WBC",
    "white blood cells": "WBC",
    "white blood cells (wbc)": "WBC",
    "fasting blood sugar": "Fasting Blood Sugar (FBS)",
    "fasting blood sugar (fbs)": "Fasting Blood Sugar (FBS)",
    "fbs": "Fasting Blood Sugar (FBS)",
}

def calculate_age(dob: datetime.date, entry_date: datetime.date) -> int:
    if not dob or not entry_date:
        return 0
    return entry_date.year - dob.year - ((entry_date.month, entry_date.day) < (dob.month, dob.day))

def evaluate_result(test_name: str, result_value: str, dob: datetime.date, sex: str, entry_date: datetime.date) -> dict:
    if not test_name:
        return {
            "unit": None,
            "reference": None,
            "flag": None,
            "is_abnormal": False
        }

    test_config = REFERENCE_RANGES.get(test_name)
    if not test_config:
        alias_key = ALIAS_MAP.get(test_name.strip().lower())
        if alias_key:
            test_config = REFERENCE_RANGES.get(alias_key)

    if not test_config:
        return {
            "unit": None,
            "reference": None,
            "flag": None,
            "is_abnormal": False
        }
    
    unit = test_config.get("unit")
    
    try:
        if result_value is None:
            val = None
        else:
            clean_str = str(result_value).strip().split()[0] if str(result_value).strip() else ""
            val = float(clean_str)
    except (ValueError, TypeError):
        val = None
    
    age = calculate_age(dob, entry_date) if dob else None
    
    matched_rule = None
    for rule in test_config.get("rules", []):
        age_min = rule.get("age_min", 0)
        age_max = rule.get("age_max", 999)
        rule_sex = rule.get("sex")
        
        if age is not None:
            if not (age_min <= age <= age_max):
                continue
                
        if not rule_sex or (sex and rule_sex.lower() == sex.lower()):
            matched_rule = rule
            break
            
    if not matched_rule and test_config.get("rules"):
        if age is None:
            for rule in test_config.get("rules", []):
                rule_sex = rule.get("sex")
                if not rule_sex or (sex and rule_sex.lower() == sex.lower()):
                    matched_rule = rule
                    break
            if not matched_rule:
                matched_rule = test_config.get("rules")[0]

    if not matched_rule:
        return {
            "unit": unit,
            "reference": None,
            "flag": None,
            "is_abnormal": False
        }
        
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
        ref_str = None
    
    flag = None
    if val is not None:
        if c_min is not None and val < c_min:
            flag = "*"
        elif c_max is not None and val > c_max:
            flag = "*"
        elif n_min is not None and val < n_min:
            flag = "L"
        elif n_max is not None and val > n_max:
            flag = "H"
        
    is_abnormal = (flag is not None)
    
    return {
        "unit": unit,
        "reference": ref_str,
        "flag": flag,
        "is_abnormal": is_abnormal
    }

