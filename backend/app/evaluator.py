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

def calculate_age(dob: datetime.date, entry_date: datetime.date) -> int:
    return entry_date.year - dob.year - ((entry_date.month, entry_date.day) < (dob.month, dob.day))

def evaluate_result(test_name: str, result_value: str, dob: datetime.date, sex: str, entry_date: datetime.date) -> dict:
    test_config = REFERENCE_RANGES.get(test_name)
    if not test_config:
        return {
            "unit": None,
            "reference": None,
            "flag": None,
            "is_abnormal": False
        }
    
    unit = test_config.get("unit")
    
    try:
        val = float(result_value)
    except ValueError:
        val = None
    
    age = calculate_age(dob, entry_date)
    
    matched_rule = None
    for rule in test_config.get("rules", []):
        age_min = rule.get("age_min", 0)
        age_max = rule.get("age_max", 999)
        rule_sex = rule.get("sex")
        
        if age_min <= age <= age_max:
            if not rule_sex or rule_sex.lower() == sex.lower():
                matched_rule = rule
                break
                
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
