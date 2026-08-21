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
    Extracts Sample ID, timestamp, device model, and sequential CBC parameters with hardware flags.
    Robust against arbitrary clipboard prefixes, log wrappers, missing headers, tabs, or whitespace variance.
    """
    if not raw_text or not isinstance(raw_text, str):
        return {"status": "error", "detail": "Empty or invalid raw text input"}

    clean_text = raw_text.strip()
    if not clean_text:
        return {"status": "error", "detail": "No content to parse"}

    # Extract sample ID: 5 to 8 digits
    sample_id = None
    sample_match = re.search(r"\b(\d{5,8})\b", clean_text)
    if sample_match:
        sample_id = sample_match.group(1)

    # Extract date & time: YYYYMMDD and HHMMSS (e.g. 20260817 and 145705)
    timestamp = None
    date_match = re.search(r"\b(20\d{6})\b\s+\b(\d{6})", clean_text)
    if date_match:
        d_str = date_match.group(1)
        t_str = date_match.group(2)
        timestamp = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]} {t_str[:2]}:{t_str[2:4]}:{t_str[4:6]}"
        # Result values are on the SAME line as the timestamp.
        # Grab only that line to avoid reference ranges from a second [Send] line.
        search_scope = clean_text[date_match.end():]
        first_newline = search_scope.find('\n')
        if first_newline != -1:
            search_scope = search_scope[:first_newline]
    else:
        # No timestamp found — pick the line with the most flagged numeric values
        # (flags: *, H, L) — that is almost certainly the results line.
        lines = clean_text.splitlines()
        best_line = clean_text
        best_flag_count = 0
        for line in lines:
            flag_count = len(re.findall(r'\d+(?:\.\d+)?[*HLhl]', line))
            if flag_count > best_flag_count:
                best_flag_count = flag_count
                best_line = line
        search_scope = best_line

    # Extract all numeric values with optional flags (*, H, L, etc.)
    # Matches tokens like: 4.1, 30.4*, 6.92H, 76.2L, 175, 0.13L
    raw_tokens = re.findall(r"(\d+(?:\.\d+)?)\s*([*HLhl])?", search_scope)

    # Build clean token list
    filtered_tokens = []
    for num_str, flag_str in raw_tokens:
        flag_clean = flag_str.upper() if flag_str else None
        filtered_tokens.append((num_str, flag_clean))

    # Strip any leading 3-digit integer status/run codes (e.g. 102, 100, 001).
    # A status code is a pure integer (no decimal), value 100-999, no flag.
    while filtered_tokens:
        candidate, flag = filtered_tokens[0]
        is_integer = '.' not in candidate
        is_status_code = is_integer and 100 <= int(candidate) <= 999 and flag is None
        if is_status_code:
            filtered_tokens = filtered_tokens[1:]
        else:
            break

    if len(filtered_tokens) < 18:
        return {
            "status": "error",
            "detail": (
                f"Could not extract sufficient CBC parameters. "
                f"Found {len(filtered_tokens)} numeric tokens after parsing. "
                f"Ensure you paste the complete analyzer output line containing the results."
            )
        }

    # Map up to 22 parameters (take only the first 22 tokens)
    parsed_parameters: List[Dict[str, Any]] = []
    limit = min(len(filtered_tokens), len(CBC_PARAMETER_DEFINITIONS))
    for i in range(limit):
        p_def = CBC_PARAMETER_DEFINITIONS[i]
        num_val, flag_val = filtered_tokens[i]
        parsed_parameters.append({
            "name": p_def["name"],
            "value": num_val,
            "flag": flag_val,
            "unit": p_def["unit"]
        })

    return {
        "status": "success",
        "sample_id": sample_id or "UNKNOWN",
        "timestamp": timestamp,
        "device_model": "MEK-7222",
        "parameters": parsed_parameters
    }
