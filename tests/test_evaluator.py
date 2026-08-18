import pytest
import datetime
from backend.app.evaluator import evaluate_result

def test_evaluator_wbc_child_normal():
    dob = datetime.date(2015, 1, 1)
    entry_date = datetime.date(2025, 1, 1) # age 10
    res = evaluate_result("WBC", "10.0", dob, "Male", entry_date)
    assert res["unit"] == "10^3/uL"
    assert res["reference"] == "6.0 - 14.0"
    assert res["flag"] is None
    assert res["is_abnormal"] is False

def test_evaluator_wbc_child_high():
    dob = datetime.date(2015, 1, 1)
    entry_date = datetime.date(2025, 1, 1) # age 10
    res = evaluate_result("WBC", "15.0", dob, "Male", entry_date)
    assert res["flag"] == "H"
    assert res["is_abnormal"] is True

def test_evaluator_hb_female_low():
    dob = datetime.date(1990, 1, 1)
    entry_date = datetime.date(2025, 1, 1) # age 35
    # Verify a 35-year-old female with Hb 10.0 gets flagged as L
    res = evaluate_result("Hemoglobin (Hb)", "10.0", dob, "Female", entry_date)
    assert res["reference"] == "12.0 - 15.5"
    assert res["flag"] == "L"
    assert res["is_abnormal"] is True

def test_evaluator_hb_male_critical():
    dob = datetime.date(1990, 1, 1)
    entry_date = datetime.date(2025, 1, 1) # age 35
    # Verify an adult male with Hb 7.5 gets flagged as * (Critical)
    res = evaluate_result("Hemoglobin (Hb)", "7.5", dob, "Male", entry_date)
    assert res["reference"] == "13.5 - 17.5"
    assert res["flag"] == "*"
    assert res["is_abnormal"] is True

def test_evaluator_fbs_high():
    dob = datetime.date(1990, 1, 1)
    entry_date = datetime.date(2025, 1, 1)
    res = evaluate_result("Fasting Blood Sugar (FBS)", "6.0", dob, "Male", entry_date)
    assert res["flag"] == "H"
    assert res["is_abnormal"] is True

def test_evaluator_non_numeric():
    dob = datetime.date(1990, 1, 1)
    entry_date = datetime.date(2025, 1, 1)
    # Ensure it handles parsing errors gracefully (if result is text, no flagging unless defined)
    res = evaluate_result("WBC", "Positive", dob, "Male", entry_date)
    assert res["flag"] is None
    assert res["is_abnormal"] is False
    assert res["reference"] == "4.0 - 11.0"
