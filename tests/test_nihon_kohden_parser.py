import pytest
from backend.app.parsers.nihon_kohden import parse_nihon_kohden_output

# Real MEK-7222 serial protocol output (from docs/reference/REPORT TEMPLATE/nihon output.txt).
# Fields are CR-delimited (\r). STX (\x02) opens the record, ETX (\x03) closes it.
# Record 2 (EXP...) carries reference ranges and must be ignored by the parser.
RAW_NIHON_SAMPLE = (
    "[host] [Send]\x02MEK-7222  \r   22\r01024\rCLOSED      \rCBC + Diff  \r01\r"
    "BLOOD           \r01  \r0002413   \rV03-02  \rV04-02  \rV03-01  \r01536\r1    \r   \r"
    "2026\r08\r17\r     \r14\r57\r05\r102            \r"
    " 4.1  \r30.4* \r55.3* \r10.0* \r 2.7* \r 1.6* \r"
    " 1.3* \r 2.3* \r 0.4* \r 0.1* \r 0.1* \r"
    "6.92H \r16.9  \r52.7H \r76.2L \r24.4L \r32.1  \r12.9  \r 175  \r0.13L \r 7.6  \r17.6H \r"
    "                                                                                     \r"
    " \r \r \r \r \r \r \r \r \r \r+\r \r \r+\r \r \r+\r \r             \r+\r \r \r \r \r \r \r"
    "         \r \r \r \r \r       \r\x03\r\n"
    "[host] [Send]\x02EXP\r00512\rMEK-7222  \r01\r"
    "                          \r      \r    \r  \r  \r   \r             \r"
    "                          \r        \r"
    "                                                                \r0\r0\r \r"
    "                               \r"
    " 4.0\r 9.0\r28.0\r78.0\r17.0\r57.0\r 0.0\r10.0\r 0.0\r10.0\r 0.0\r 2.0\r 1.1\r 7.0\r"
    " 0.7\r 5.1\r 0.0\r 0.9\r 0.0\r 0.9\r 0.0\r 0.2\r3.76\r5.70\r12.0\r18.0\r33.5\r52.0\r80.0\r"
    " 100\r28.0\r32.0\r31.0\r35.0\r11.6\r14.0\r 150\r 350\r0.16\r0.33\r 7.0\r11.0\r15.0\r17.0\r\x03\r\n"
)

# Second real sample (from docs/reference/REPORT TEMPLATE/OUTPUT2.txt) — different patient, MANUAL mode.
RAW_NIHON_SAMPLE_2 = (
    "[host] [Send]\x02MEK-7222  \r   22\r01024\rMANUAL      \rCBC + Diff  \r01\r"
    "BLOOD           \rMMM \r0002437   \rV03-02  \rV04-02  \rV03-01  \r01536\r1    \r   \r"
    "2026\r08\r21\r     \r17\r41\r52\r134            \r"
    " 4.2* \r26.5L \r45.6* \r20.1* \r 5.2  \r 2.6H \r"
    " 1.1  \r 1.9* \r 0.8* \r 0.2  \r 0.1  \r"
    "5.39* \r11.8L \r36.9  \r68.5L \r21.9L \r32.0  \r16.3H \r 233* \r0.17  \r 7.5  \r18.7H \r"
    "                                                                                     \r"
    " \r \r \r \r \r \r \r \r \r \r \r \r+\r \r+\r \r \r             \r \r \r \r+\r \r \r \r"
    "         \r \r \r \r+\r       \r\x03\r\n"
    "[host] [Send]\x02EXP\r00512\rMEK-7222  \r01\r"
    "                          \r      \r    \r  \r  \r   \r             \r"
    "                          \r        \r"
    "                                                                \r0\r0\r \r"
    "                               \r"
    " 4.0\r 9.0\r28.0\r78.0\r17.0\r57.0\r 0.0\r10.0\r 0.0\r10.0\r 0.0\r 2.0\r 1.1\r 7.0\r"
    " 0.7\r 5.1\r 0.0\r 0.9\r 0.0\r 0.9\r 0.0\r 0.2\r3.76\r5.70\r12.0\r18.0\r33.5\r52.0\r80.0\r"
    " 100\r28.0\r32.0\r31.0\r35.0\r11.6\r14.0\r 150\r 350\r0.16\r0.33\r 7.0\r11.0\r15.0\r17.0\r\x03\r\n"
)


# ---------------------------------------------------------------------------
# Sample 1 — nihon output.txt
# ---------------------------------------------------------------------------

def test_parse_valid_nihon_kohden_output():
    res = parse_nihon_kohden_output(RAW_NIHON_SAMPLE)
    assert res["status"] == "success"
    assert res["sample_id"] == "0002413"
    assert res["timestamp"] == "2026-08-17 14:57:05"
    assert res["device_model"] == "MEK-7222"
    assert len(res["parameters"]) == 22


def test_parse_sample1_all_parameters():
    res = parse_nihon_kohden_output(RAW_NIHON_SAMPLE)
    p = {r["name"]: r for r in res["parameters"]}

    assert p["Total WBC Count (White Blood Cells)"]["value"] == "4.1"
    assert p["Total WBC Count (White Blood Cells)"]["flag"] is None

    assert p["Neutrophils (%) [Relative Count]"]["value"] == "30.4"
    assert p["Neutrophils (%) [Relative Count]"]["flag"] == "*"

    assert p["Lymphocytes (%) [Relative Count]"]["value"] == "55.3"
    assert p["Lymphocytes (%) [Relative Count]"]["flag"] == "*"

    assert p["Monocytes (%) [Relative Count]"]["value"] == "10.0"
    assert p["Monocytes (%) [Relative Count]"]["flag"] == "*"

    assert p["Eosinophils (%) [Relative Count]"]["value"] == "2.7"
    assert p["Eosinophils (%) [Relative Count]"]["flag"] == "*"

    assert p["Basophils (%) [Relative Count]"]["value"] == "1.6"
    assert p["Basophils (%) [Relative Count]"]["flag"] == "*"

    assert p["Neutrophils (Absolute Count)"]["value"] == "1.3"
    assert p["Neutrophils (Absolute Count)"]["flag"] == "*"

    assert p["Lymphocytes (Absolute Count)"]["value"] == "2.3"
    assert p["Lymphocytes (Absolute Count)"]["flag"] == "*"

    assert p["Monocytes (Absolute Count)"]["value"] == "0.4"
    assert p["Monocytes (Absolute Count)"]["flag"] == "*"

    assert p["Eosinophils (Absolute Count)"]["value"] == "0.1"
    assert p["Eosinophils (Absolute Count)"]["flag"] == "*"

    assert p["Basophils (Absolute Count)"]["value"] == "0.1"
    assert p["Basophils (Absolute Count)"]["flag"] == "*"

    assert p["Red Blood Cells (RBC)"]["value"] == "6.92"
    assert p["Red Blood Cells (RBC)"]["flag"] == "H"

    assert p["Hemoglobin (Hb)"]["value"] == "16.9"
    assert p["Hemoglobin (Hb)"]["flag"] is None

    assert p["Hematocrit (HCT)"]["value"] == "52.7"
    assert p["Hematocrit (HCT)"]["flag"] == "H"

    assert p["Mean Cell Volume (MCV)"]["value"] == "76.2"
    assert p["Mean Cell Volume (MCV)"]["flag"] == "L"

    assert p["Mean Cell Hb (MCH)"]["value"] == "24.4"
    assert p["Mean Cell Hb (MCH)"]["flag"] == "L"

    assert p["Mean Cell Hb Conc (MCHC)"]["value"] == "32.1"
    assert p["Mean Cell Hb Conc (MCHC)"]["flag"] is None

    assert p["RBC Distribution Width (RDW)"]["value"] == "12.9"
    assert p["RBC Distribution Width (RDW)"]["flag"] is None

    assert p["Platelets Count (PLT)"]["value"] == "175"
    assert p["Platelets Count (PLT)"]["flag"] is None

    assert p["Thrombocrit (PCT)"]["value"] == "0.13"
    assert p["Thrombocrit (PCT)"]["flag"] == "L"

    assert p["Mean Platelet Volume (MPV)"]["value"] == "7.6"
    assert p["Mean Platelet Volume (MPV)"]["flag"] is None

    assert p["PLT Distribution Width (PDW)"]["value"] == "17.6"
    assert p["PLT Distribution Width (PDW)"]["flag"] == "H"


# ---------------------------------------------------------------------------
# Sample 2 — OUTPUT2.txt (MANUAL mode, different patient)
# ---------------------------------------------------------------------------

def test_parse_sample2_success():
    res = parse_nihon_kohden_output(RAW_NIHON_SAMPLE_2)
    assert res["status"] == "success"
    assert res["sample_id"] == "0002437"
    assert res["timestamp"] == "2026-08-21 17:41:52"
    assert len(res["parameters"]) == 22


def test_parse_sample2_key_parameters():
    res = parse_nihon_kohden_output(RAW_NIHON_SAMPLE_2)
    p = {r["name"]: r for r in res["parameters"]}

    assert p["Total WBC Count (White Blood Cells)"]["value"] == "4.2"
    assert p["Total WBC Count (White Blood Cells)"]["flag"] == "*"

    assert p["Neutrophils (%) [Relative Count]"]["value"] == "26.5"
    assert p["Neutrophils (%) [Relative Count]"]["flag"] == "L"

    assert p["Red Blood Cells (RBC)"]["value"] == "5.39"
    assert p["Red Blood Cells (RBC)"]["flag"] == "*"

    assert p["Hemoglobin (Hb)"]["value"] == "11.8"
    assert p["Hemoglobin (Hb)"]["flag"] == "L"

    assert p["Platelets Count (PLT)"]["value"] == "233"
    assert p["Platelets Count (PLT)"]["flag"] == "*"

    assert p["PLT Distribution Width (PDW)"]["value"] == "18.7"
    assert p["PLT Distribution Width (PDW)"]["flag"] == "H"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_parse_invalid_text():
    res = parse_nihon_kohden_output("invalid random text here")
    assert res["status"] == "error"
    assert "detail" in res


def test_parse_empty_string():
    res = parse_nihon_kohden_output("")
    assert res["status"] == "error"


def test_parse_none():
    res = parse_nihon_kohden_output(None)
    assert res["status"] == "error"


def test_reference_ranges_not_parsed_as_results():
    """EXP record (reference ranges line) must not be mistaken for patient results."""
    exp_only = (
        "[host] [Send]\x02EXP\r00512\rMEK-7222  \r01\r"
        " 4.0\r 9.0\r28.0\r78.0\r17.0\r57.0\r 0.0\r10.0\r 0.0\r10.0\r 0.0\r 2.0\r 1.1\r 7.0\r"
        " 0.7\r 5.1\r 0.0\r 0.9\r 0.0\r 0.9\r 0.0\r 0.2\r\x03\r\n"
    )
    res = parse_nihon_kohden_output(exp_only)
    # Should error since reference-range line has no patient results record
    assert res["status"] == "error"
