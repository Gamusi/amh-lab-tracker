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


def _extract_fields(raw_text: str) -> tuple[List[str], List[str], str]:
    """
    Extracts ordered field lists for both patient-results and EXP reference ranges,
    along with the raw EXP line if found.
    Returns (patient_fields, exp_fields, raw_exp_line).

    Supports three copy formats from the Nihon Kohden host software:
    - Mode 1: raw serial protocol with embedded CR (\\r) field delimiters
    - Mode 2: clipboard paste where each CR-field renders as its own LF line
    - Mode 3: host software display copy — all fields space-separated on one long line
    """
    text = raw_text.replace('\r\n', '\n')
    lines = text.split('\n')

    # --- Mode 1: raw protocol (embedded \r within lines) ---
    patient_line = None
    exp_line = None
    for line in lines:
        if 'MEK-7222' in line and 'EXP' not in line and '\r' in line and line.strip():
            patient_line = line
        elif 'EXP' in line and '\r' in line and line.strip():
            exp_line = line

    if patient_line:
        p_fields = [f.strip() for f in patient_line.split('\r')]
        e_fields = [f.strip() for f in exp_line.split('\r')] if exp_line else []
        return p_fields, e_fields, exp_line or ""

    # --- Mode 3: inline display format (host software screen copy) ---
    # Detected when the MEK-7222 patient line is a single long line (> 200 chars).
    # All fields are space-separated on one long line per record.
    # EXP line also contains 'MEK-7222' and is > 50 chars.
    patient_line_inline = None
    exp_line_inline = None
    for line in lines:
        if 'MEK-7222' in line and 'EXP' not in line and len(line) > 200:
            patient_line_inline = line
        elif 'EXP' in line and 'MEK-7222' in line and len(line) > 50:
            exp_line_inline = line

    if patient_line_inline:
        p_fields = patient_line_inline.split()
        e_fields = exp_line_inline.split() if exp_line_inline else []
        return p_fields, e_fields, exp_line_inline or ""

    # --- Mode 2: clipboard-paste (one field per \n line) ---
    # Each CR-field from the analyzer renders as its own newline.
    p2: List[str] = []
    e2: List[str] = []
    current_target: Optional[List[str]] = None

    for line in lines:
        stripped = line.strip()
        if 'MEK-7222' in line and 'EXP' not in line:
            current_target = p2
            current_target.append(stripped)
            continue
        elif 'EXP' in line and ('[host]' in line or stripped == 'EXP' or 'EXP' in stripped):
            current_target = e2
            current_target.append(stripped)
            continue

        if current_target is not None:
            current_target.append(stripped)

    return p2, e2, ""


def _extract_exp_ranges(exp_fields: List[str], raw_exp_line: str = "") -> List[str]:
    """
    Extracts 22 low-high reference range strings from the EXP record fields.
    Returns a list of 22 formatted 'low - high' strings (or empty list if not found).

    Handles:
    - Delimited fields (Modes 1 & 2): 44 individual numeric tokens
    - Fixed-width inline format (Mode 3): 44 fixed 4-character width fields (176 characters total)
    """
    # Modes 1 & 2: one numeric token per field
    if exp_fields:
        num_tokens = []
        for f in exp_fields:
            m = re.match(r'^\s*(\d+(?:\.\d+)?)\s*$', f)
            if m:
                num_tokens.append(m.group(1))

        if len(num_tokens) >= 44:
            range_tokens = num_tokens[-44:]
            return [f"{range_tokens[i]} - {range_tokens[i+1]}" for i in range(0, 44, 2)]

    # Mode 3 fallback: Fixed-width 4-character columns at the tail of the EXP record (176 chars = 44 * 4)
    if raw_exp_line:
        s = raw_exp_line.rstrip()
        if len(s) >= 176:
            payload = s[-176:]
            tokens = [payload[i:i+4].strip() for i in range(0, 176, 4)]
            # Validate that tokens are numeric
            if all(re.match(r'^\d+(?:\.\d+)?$', t) for t in tokens if t):
                if len(tokens) == 44:
                    return [f"{tokens[i]} - {tokens[i+1]}" for i in range(0, 44, 2)]

    return []


def parse_nihon_kohden_output(raw_text: str) -> Dict[str, Any]:
    """
    Parses raw serial/clipboard output from Nihon Kohden MEK-7222 hematology analyzer.

    Supports three copy formats from the Nihon Kohden host software:
    - Raw serial protocol (CR-delimited fields, STX/ETX framing)
    - Clipboard paste (each CR-field rendered as its own LF line)
    - Inline display copy (all fields space-separated on one long line per record)
    """
    if not raw_text or not isinstance(raw_text, str):
        return {"status": "error", "detail": "Empty or invalid raw text input"}

    if not raw_text.strip():
        return {"status": "error", "detail": "No content to parse"}

    # Strip STX (0x02), ETX (0x03), and other non-printable control chars.
    # Preserve CR (\r = 0x0D) and LF (\n = 0x0A) — both are structural.
    clean_text = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]', '', raw_text)

    fields, exp_fields, raw_exp_line = _extract_fields(clean_text)
    if not fields:
        return {"status": "error", "detail": "No patient results record found. Ensure you paste the full analyzer output."}

    exp_ranges = _extract_exp_ranges(exp_fields, raw_exp_line)

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
    # Mode 3 (inline display): date is one 8-digit YYYYMMDD token (e.g. "20260821"),
    # and time is the first 6 digits of the immediately following token (e.g. "174152134" -> 17:41:52).
    # Modes 1 & 2: year / month / day / hour / min / sec are separate fields.
    timestamp = None
    time_end_idx = 0

    # Try 8-digit YYYYMMDD token first (Mode 3 inline format)
    inline_date_found = False
    for i, f in enumerate(fields):
        if re.match(r'^20\d{6}$', f):
            d_str = f
            # Next non-empty field should be HHMMSS[extra digits]
            for j in range(i + 1, min(i + 5, len(fields))):
                nf = fields[j]
                if re.match(r'^\d{6,}$', nf):
                    t_str = nf[:6]
                    timestamp = (
                        f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]} "
                        f"{t_str[:2]}:{t_str[2:4]}:{t_str[4:6]}"
                    )
                    time_end_idx = j
                    inline_date_found = True
                    break
            break

    if not inline_date_found:
        # Modes 1 & 2: year is a standalone 4-digit field (e.g. "2026")
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
                # Non-empty non-numeric field after values started -> end of values
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
        ref_range = exp_ranges[i] if i < len(exp_ranges) else None
        parsed_parameters.append({
            "name": p_def["name"],
            "value": num_val,
            "flag": flag_val,
            "unit": p_def["unit"],
            "reference_range": ref_range
        })

    return {
        "status": "success",
        "sample_id": sample_id or "UNKNOWN",
        "timestamp": timestamp,
        "device_model": "MEK-7222",
        "parameters": parsed_parameters
    }
