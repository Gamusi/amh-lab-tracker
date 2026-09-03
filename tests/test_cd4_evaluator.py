import pytest
from backend.app.evaluator import evaluate_result, evaluate_cd4_interpretation, ALIAS_MAP
from backend.app.biochem_validator import validate_biochem_parameter
from backend.app.database import get_connection, init_db

def test_cd4_cytometry_evaluation():
    conn = get_connection()
    init_db()

    # Adult severe immunosuppression / AHD: < 200 cells/µL -> L*
    eval_ahd = evaluate_result("Absolute CD4 Count (Cytometry)", "150", db=conn, unit="cells/µL")
    assert eval_ahd["flag"] == "L*"
    assert eval_ahd["is_abnormal"] is True

    # Mild-to-moderate immunosuppression: 200 - 499 cells/µL -> L
    eval_mild = evaluate_result("Absolute CD4 Count (Cytometry)", "320", db=conn, unit="cells/µL")
    assert eval_mild["flag"] == "L"
    assert eval_mild["is_abnormal"] is True

    # Normal immunological status: 500 - 1500 cells/µL -> None
    eval_norm = evaluate_result("Absolute CD4 Count (Cytometry)", "750", db=conn, unit="cells/µL")
    assert eval_norm["flag"] is None
    assert eval_norm["is_abnormal"] is False

    # Physiological sanity bounds: negative or > 5000 cells/µL raises ValueError
    with pytest.raises(ValueError, match="sanity limits"):
        validate_biochem_parameter(conn, "Absolute CD4 Count (Cytometry)", "6500", unit="cells/µL")
    conn.close()

def test_cd4_rdt_qualitative_evaluation():
    conn = get_connection()
    init_db()

    # Below 200 cells/µL -> Critical L*
    res_below = evaluate_result("CD4 Count (Rapid Test Strip)", "CD4 Count: Below 200 cells/µL", db=conn)
    assert res_below["flag"] == "L*"
    assert res_below["is_abnormal"] is True

    # 200 cells/µL or above -> Normal
    res_above = evaluate_result("CD4 Count (Rapid Test Strip)", "CD4 Count: 200 cells/µL or above", db=conn)
    assert res_above["flag"] is None
    assert res_above["is_abnormal"] is False

    # Invalid run
    res_invalid = evaluate_result("CD4 Count (Rapid Test Strip)", "Invalid", db=conn)
    assert res_invalid["flag"] == "\u26A0"
    assert res_invalid["is_abnormal"] is True
    conn.close()

def test_evaluate_cd4_interpretation_helper():
    # Cytometry AHD
    interp_ahd = evaluate_cd4_interpretation("Absolute CD4 Count (Cytometry)", "186")
    assert interp_ahd["is_ahd"] is True
    assert interp_ahd["flag"] == "L*"
    assert "CRITICAL ALERT" in interp_ahd["interpretive_comment"]
    assert "Urine TB-LAM" in interp_ahd["interpretive_comment"]
    assert interp_ahd["ahd_package_indicated"] is True

    # Cytometry Stable
    interp_stable = evaluate_cd4_interpretation("Absolute CD4 Count (Cytometry)", "620")
    assert interp_stable["is_ahd"] is False
    assert interp_stable["flag"] is None
    assert "stability" in interp_stable["interpretive_comment"].lower()

    # RDT Below 200
    interp_rdt_below = evaluate_cd4_interpretation("CD4 Count (Rapid Test Strip)", "CD4 Count: Below 200 cells/µL")
    assert interp_rdt_below["is_ahd"] is True
    assert interp_rdt_below["flag"] == "L*"
    assert "Urine TB-LAM" in interp_rdt_below["interpretive_comment"]

    # RDT 200 or above
    interp_rdt_above = evaluate_cd4_interpretation("CD4 Count (Rapid Test Strip)", "CD4 Count: 200 cells/µL or above")
    assert interp_rdt_above["is_ahd"] is False
    assert interp_rdt_above["flag"] is None

    # Pediatric staging (< 60 months) with CD4% < 25%
    interp_ped = evaluate_cd4_interpretation("CD4 Percentage", "18.5", age_months=36)
    assert interp_ped["is_ahd"] is True
    assert interp_ped["flag"] == "L*"
    assert "Pediatric Advanced HIV Disease" in interp_ped["interpretive_comment"]
