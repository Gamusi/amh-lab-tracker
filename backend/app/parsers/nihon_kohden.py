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

# Matches a standalone CBC result field: optional whitespace, number, optional flag, optional whitespace.
# e.g. " 4.1  ", "30.4* ", "6.92H ", " 175  ", "0.13L "
_VALUE_FIELD_RE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*([*HLhl])?\s*$')
_YEAR_RE = re.compile(r'^20\d{2}$')
_TWO_DIGIT_RE = re.compile(r'^\d{1,2}$')


def _isolate_results_record(raw_text: str) -> Optional[str]:
    """
    The MEK-7222 outputs two records per sample, separated by \\n:
      Record 1 (patient results):  starts with [host] [Send]<STX>MEK-7222
      Record 2 (reference ranges): starts with [host] [Send]<STX>EXP
    Returns the patient-results record as a raw string (CR-delimited fields intact).
    Returns None if only an EXP record is present (no patient data to parse).
    """
    lines = raw_text.split('\n')
    for line in lines:
        # Must contain MEK-7222 and must NOT be the EXP reference-ranges record
        if 'MEK-7222' in line and 'EXP' not in line and line.strip():
            return line
    # No suitable line found — do NOT fall back to an EXP line
    return None



def parse_nihon_kohden_output(raw_text: str) -> Dict[str, Any]:
    """
    Parses raw serial/clipboard output from Nihon Kohden MEK-7222 hematology analyzer.

    Real protocol format (discovered from reference files):
    - STX (0x02) at record start, ETX (0x03) at record end.
    - Fields are delimited by bare CR (\\r, 0x0D).
    - Date is split across three consecutive CR-fields: YYYY \\r MM \\r DD
    - Time is split across three consecutive CR-fields: HH \\r MM \\r SS
      with a possible empty/whitespace field between date and time.
    - Result values are individual CR-fields, e.g. " 4.1  \\r30.4* \\r..."
    - A 3-digit status/run code (e.g. "102") immediately precedes the values.
    - Record 2 (reference ranges) starts with EXP and is discarded.
    """
    if not raw_text or not isinstance(raw_text, str):
        return {"status": "error", "detail": "Empty or invalid raw text input"}

    if not raw_text.strip():
        return {"status": "error", "detail": "No content to parse"}

    # Strip STX (0x02), ETX (0x03), and other non-printable control chars
    # but preserve CR (\r = 0x0D) and LF (\n = 0x0A) which are structural.
    clean_text = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]', '', raw_text)

    # Isolate the patient-results record (line 1, not the EXP reference-ranges line)
    record = _isolate_results_record(clean_text)
    if not record:
        return {"status": "error", "detail": "No content to parse"}

    # Split into fields on CR
    fields = [f.strip() for f in record.split('\r')]

    # --- Sample ID ---
    # The sample ID is a 6-8 digit field (distinct from 5-digit machine codes like 01024, 01536).
    sample_id = None
    for f in fields:
        if re.match(r'^\d{6,8}$', f):
            sample_id = f
            break
    if not sample_id:
        # Broader fallback: any 5-8 digit standalone field
        for f in fields:
            if re.match(r'^\d{5,8}$', f):
                sample_id = f
                break

    # --- Timestamp ---
    # Find the year field (20XX), then collect month, day, [gap?], hour, min, sec.
    timestamp = None
    year_idx = None
    for i, f in enumerate(fields):
        if _YEAR_RE.match(f):
            year_idx = i
            break

    time_end_idx = year_idx if year_idx is not None else 0

    if year_idx is not None:
        try:
            year = fields[year_idx]
            month = fields[year_idx + 1].zfill(2)
            day = fields[year_idx + 2].zfill(2)

            # Scan forward from year+3 for hour, minute, second (1-2 digit fields),
            # skipping empty/whitespace-only gap fields.
            time_parts: List[str] = []
            j = year_idx + 3
            while j < len(fields) and len(time_parts) < 3:
                candidate = fields[j]
                if _TWO_DIGIT_RE.match(candidate):
                    time_parts.append(candidate.zfill(2))
                    time_end_idx = j
                elif candidate == '':
                    pass  # gap between date and time
                else:
                    # Non-empty non-numeric: we've overshot
                    if time_parts:
                        break
                j += 1

            if len(time_parts) == 3:
                timestamp = f"{year}-{month}-{day} {time_parts[0]}:{time_parts[1]}:{time_parts[2]}"
        except (IndexError, ValueError):
            pass

    # --- Result values ---
    # Start scanning from just after the last time field.
    # Skip leading 3-digit integer status/run codes (e.g. "102").
    # Collect fields that match the value pattern; stop at the first
    # non-empty, non-numeric field (start of the flags/morphology section).
    filtered_tokens: List[tuple] = []
    started_values = False

    for i in range(time_end_idx + 1, len(fields)):
        f = fields[i]
        m = _VALUE_FIELD_RE.match(f)
        if m:
            num_str = m.group(1)
            flag_str = m.group(2)
            flag_clean = flag_str.upper() if flag_str else None

            if not started_values:
                # Skip leading status code(s): integer, 100-999, no flag
                if '.' not in num_str and flag_clean is None and 100 <= int(num_str) <= 999:
                    continue
                started_values = True

            filtered_tokens.append((num_str, flag_clean))

            # Stop once we have all 22 — avoids bleeding into flag columns
            if len(filtered_tokens) == len(CBC_PARAMETER_DEFINITIONS):
                break
        elif started_values:
            if f:
                # Non-empty non-numeric field after values started → end of values
                break
            # Empty gap — continue

    if len(filtered_tokens) < 18:
        return {
            "status": "error",
            "detail": (
                f"Could not extract sufficient CBC parameters. "
                f"Found {len(filtered_tokens)} numeric tokens after parsing. "
                f"Ensure you paste the complete analyzer output including the results line."
            )
        }

    # --- Map to parameter definitions ---
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
