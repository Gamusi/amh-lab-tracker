import re
from typing import Optional, Dict, Any, List

# Standard parameter definitions matching AMH Lab Tracker database names and units
CBC_PARAMETER_DEFINITIONS = [
    {"name": "Total WBC Count (White Blood Cells)", "unit": "10³/µL"},
    {"name": "Neutrophils (%) [Relative Count]", "unit": "%"},
    {"name": "Lymphocytes (%) [Relative Count]", "unit": "%"},
    {"name": "Monocytes (%) [Relative Count]", "unit": "%"},
    {"name": "Eosinophils (%) [Relative Count]", "unit": "%"},
    {"name": "Basophils (%) [Relative Count]", "unit": "%"},
    {"name": "Neutrophils (Absolute Count)", "unit": "10⁹/µL"},
    {"name": "Lymphocytes (Absolute Count)", "unit": "10⁹/µL"},
    {"name": "Monocytes (Absolute Count)", "unit": "10⁹/µL"},
    {"name": "Eosinophils (Absolute Count)", "unit": "10⁹/µL"},
    {"name": "Basophils (Absolute Count)", "unit": "10⁹/µL"},
    {"name": "Red Blood Cells (RBC)", "unit": "10⁶/µL"},
    {"name": "Hemoglobin (Hb)", "unit": "g/dL"},
    {"name": "Hematocrit (HCT)", "unit": "%"},
    {"name": "Mean Cell Volume (MCV)", "unit": "fL"},
    {"name": "Mean Cell Hb (MCH)", "unit": "pg"},
    {"name": "Mean Cell Hb Conc (MCHC)", "unit": "g/dL"},
    {"name": "RBC Distribution Width (RDW)", "unit": "%"},
    {"name": "Platelets Count (PLT)", "unit": "10³/µL"},
    {"name": "Thrombocrit (PCT)", "unit": "%"},
    {"name": "Mean Platelet Volume (MPV)", "unit": "fL"},
    {"name": "PLT Distribution Width (PDW)", "unit": "%"}
]

def parse_nihon_kohden_output(raw_text: str) -> Dict[str, Any]:
    """
    Parses raw transmission output from Nihon Kohden MEK-7222 / MEK series hematology analyzer.
    Extracts Sample ID, timestamp, device model, and the 22 sequential CBC parameters with hardware flags.
    """
    if not raw_text or not isinstance(raw_text, str):
        return {"status": "error", "detail": "Empty or invalid raw text input"}

    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    if not lines:
        return {"status": "error", "detail": "No content to parse"}

    line1 = lines[0]
    
    # Check for basic MEK format identification
    if "MEK-" not in line1 and "CBC" not in line1:
        return {"status": "error", "detail": "Unrecognized Nihon Kohden format. Expected MEK header."}

    # Extract sample ID: typically 7 digits e.g. 0002413
    sample_id = None
    sample_match = re.search(r"\b(\d{5,8})\b", line1)
    if sample_match:
        sample_id = sample_match.group(1)

    # Extract date & time: e.g. 20260817 and 145705102 (where 145705 is HHMMSS and 102 is run/flag code)
    timestamp = None
    date_match = re.search(r"(\d{8})\s+(\d{6})(\d+)?", line1)
    if date_match:
        d_str = date_match.group(1)
        t_str = date_match.group(2)
        timestamp = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]} {t_str[:2]}:{t_str[2:4]}:{t_str[4:6]}"
        data_after_date = line1[date_match.end():]
        value_tokens = re.findall(r"(\d+(?:\.\d+)?)\s*([*HL])?", data_after_date)
    else:
        value_tokens = re.findall(r"(\d+(?:\.\d+)?)\s*([*HL])?", line1)

    if len(value_tokens) < 22:
        return {
            "status": "error", 
            "detail": f"Incomplete result stream. Expected 22 parameters, found {len(value_tokens)}"
        }

    # Take the first 22 parameter tokens
    parsed_parameters: List[Dict[str, Any]] = []
    for i, p_def in enumerate(CBC_PARAMETER_DEFINITIONS):
        num_val, flag_val = value_tokens[i]
        parsed_parameters.append({
            "name": p_def["name"],
            "value": num_val,
            "flag": flag_val if flag_val else None,
            "unit": p_def["unit"]
        })

    return {
        "status": "success",
        "sample_id": sample_id,
        "timestamp": timestamp,
        "device_model": "MEK-7222",
        "parameters": parsed_parameters
    }
