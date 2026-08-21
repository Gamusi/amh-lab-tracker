import pytest
from backend.app.parsers.nihon_kohden import parse_nihon_kohden_output

RAW_NIHON_SAMPLE = """[host] [Send] MEK-7222     2201024CLOSED      CBC + Diff  01BLOOD           01  0002413   V03-02  V04-02  V03-01  015361       20260817     145705102             4.1  30.4* 55.3* 10.0*  2.7*  1.6*  1.3*  2.3*  0.4*  0.1*  0.1* 6.92H 16.9  52.7H 76.2L 24.4L 32.1  12.9   175  0.13L  7.6  17.6H                                                                                                                                                                                                                           +  +  +              +
[host] [Send] EXP00512MEK-7222  01                                                                                                                                                                                                                          00                                 4.0 9.028.078.017.057.0 0.010.0 0.010.0 0.0 2.0 1.1 7.0 0.7 5.1 0.0 0.9 0.0 0.9 0.0 0.23.765.7012.018.033.552.080.0 10028.032.031.035.011.614.0 150 3500.160.33 7.011.015.017.0"""

def test_parse_valid_nihon_kohden_output():
    res = parse_nihon_kohden_output(RAW_NIHON_SAMPLE)
    assert res["status"] == "success"
    assert res["sample_id"] == "0002413"
    assert "2026-08-17" in res["timestamp"]
    assert len(res["parameters"]) == 22

    params_by_name = {p["name"]: p for p in res["parameters"]}
    
    assert params_by_name["Total WBC Count (White Blood Cells)"]["value"] == "4.1"
    assert params_by_name["Total WBC Count (White Blood Cells)"]["flag"] is None

    assert params_by_name["Neutrophils (%) [Relative Count]"]["value"] == "30.4"
    assert params_by_name["Neutrophils (%) [Relative Count]"]["flag"] == "*"

    assert params_by_name["Lymphocytes (%) [Relative Count]"]["value"] == "55.3"
    assert params_by_name["Lymphocytes (%) [Relative Count]"]["flag"] == "*"

    assert params_by_name["Monocytes (%) [Relative Count]"]["value"] == "10.0"
    assert params_by_name["Monocytes (%) [Relative Count]"]["flag"] == "*"

    assert params_by_name["Eosinophils (%) [Relative Count]"]["value"] == "2.7"
    assert params_by_name["Eosinophils (%) [Relative Count]"]["flag"] == "*"

    assert params_by_name["Basophils (%) [Relative Count]"]["value"] == "1.6"
    assert params_by_name["Basophils (%) [Relative Count]"]["flag"] == "*"

    assert params_by_name["Neutrophils (Absolute Count)"]["value"] == "1.3"
    assert params_by_name["Neutrophils (Absolute Count)"]["flag"] == "*"

    assert params_by_name["Lymphocytes (Absolute Count)"]["value"] == "2.3"
    assert params_by_name["Lymphocytes (Absolute Count)"]["flag"] == "*"

    assert params_by_name["Monocytes (Absolute Count)"]["value"] == "0.4"
    assert params_by_name["Monocytes (Absolute Count)"]["flag"] == "*"

    assert params_by_name["Eosinophils (Absolute Count)"]["value"] == "0.1"
    assert params_by_name["Eosinophils (Absolute Count)"]["flag"] == "*"

    assert params_by_name["Basophils (Absolute Count)"]["value"] == "0.1"
    assert params_by_name["Basophils (Absolute Count)"]["flag"] == "*"

    assert params_by_name["Red Blood Cells (RBC)"]["value"] == "6.92"
    assert params_by_name["Red Blood Cells (RBC)"]["flag"] == "H"

    assert params_by_name["Hemoglobin (Hb)"]["value"] == "16.9"
    assert params_by_name["Hemoglobin (Hb)"]["flag"] is None

    assert params_by_name["Hematocrit (HCT)"]["value"] == "52.7"
    assert params_by_name["Hematocrit (HCT)"]["flag"] == "H"

    assert params_by_name["Mean Cell Volume (MCV)"]["value"] == "76.2"
    assert params_by_name["Mean Cell Volume (MCV)"]["flag"] == "L"

    assert params_by_name["Mean Cell Hb (MCH)"]["value"] == "24.4"
    assert params_by_name["Mean Cell Hb (MCH)"]["flag"] == "L"

    assert params_by_name["Mean Cell Hb Conc (MCHC)"]["value"] == "32.1"
    assert params_by_name["Mean Cell Hb Conc (MCHC)"]["flag"] is None

    assert params_by_name["RBC Distribution Width (RDW)"]["value"] == "12.9"
    assert params_by_name["RBC Distribution Width (RDW)"]["flag"] is None

    assert params_by_name["Platelets Count (PLT)"]["value"] == "175"
    assert params_by_name["Platelets Count (PLT)"]["flag"] is None

    assert params_by_name["Thrombocrit (PCT)"]["value"] == "0.13"
    assert params_by_name["Thrombocrit (PCT)"]["flag"] == "L"

    assert params_by_name["Mean Platelet Volume (MPV)"]["value"] == "7.6"
    assert params_by_name["Mean Platelet Volume (MPV)"]["flag"] is None

    assert params_by_name["PLT Distribution Width (PDW)"]["value"] == "17.6"
    assert params_by_name["PLT Distribution Width (PDW)"]["flag"] == "H"

def test_parse_invalid_text():
    res = parse_nihon_kohden_output("invalid random text here")
    assert res["status"] == "error"
    assert "detail" in res
