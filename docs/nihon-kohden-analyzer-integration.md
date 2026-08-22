# Nihon Kohden MEK-7222 Hematology Analyzer Integration & Parser

## 1. Executive Summary & Operational Context

The Complete Blood Count (CBC) is the highest-volume multi-parameter diagnostic test in the clinical laboratory, consisting of 22 sequential numeric parameters and morphological flags. Manual transcription of 22 parameters per client sample from analyzer printouts or screen displays into a LIMS introduces significant transcription risk, cognitive fatigue, and administrative delay.

### 1.1 Current Laboratory Workflow & Supplier Interfacing Setup
In the current hospital laboratory configuration:
1. **Instrument & Interfacing Host**: The Nihon Kohden MEK-7222 / Celltac series (and MEK-7300 series) hematology analyzer is connected via an RS-232 serial cable to a dedicated laboratory workstation running the supplier's proprietary Windows interfacing software (e.g., `NIHON KOHDEN 7300.exe` / `Interfacing.mdb`).
2. **Data Capture**: When the analyzer completes a blood sample run, the supplier interfacing application receives and displays the raw transmission log containing the sample ID, timestamp, and results.
3. **AMH Lab Tracker Import**: Rather than relying on fragile direct database hooks or proprietary ODBC drivers, the technologist simply copies the raw transmission text from the supplier interfacing window, clicks `[ Paste from Analyzer ]` inside the CBC result entry modal in AMH Lab Tracker, and pastes the content.
4. **Automated Population**: AMH Lab Tracker instantly parses the text, extracts the Sample ID and all 22 parameter values along with their machine-calibrated flags, and populates the editable result entry form for technologist inspection before saving.

---

## 2. Real Transmission Protocol & Wire Format Analysis

### 2.1 Serial Protocol Characteristics

The Nihon Kohden MEK-7222 analyzer transmits sample data over an RS-232 serial stream using standard ASCII control characters and bare carriage-return delimited fields:

| Element | ASCII Hex | Representation | Function |
| :--- | :--- | :--- | :--- |
| **STX** | `0x02` | `\x02` / `^B` | Start of Transmission Frame |
| **ETX** | `0x03` | `\x03` / `^C` | End of Transmission Frame |
| **CR** | `0x0D` | `\r` | Field Delimiter (Bare Carriage Return) |
| **LF** | `0x0A` | `\n` | Record Delimiter (Line Feed) |

---

### 2.2 Dual Record Structure & Calibrated Reference Intervals

Each sample transmission consists of two distinct records separated by a newline (`\n`):

1. **Record 1 (Patient Test Results)**: Starts with `[host] [Send]<STX>MEK-7222` and contains client sample identification, acquisition timestamp, run status code, 22 numerical parameters with instrument-derived flags (`*`, `H`, `L`), and morphology alert distributions.
2. **Record 2 (Analyzer-Calibrated Reference Intervals)**: Starts with `[host] [Send]<STX>EXP` and transmits the instrument's preset low and high reference limits for each parameter (e.g., `4.0 9.0` for WBC, `12.0 18.0` for Hb, `150 350` for PLT).

```
+-----------------------------------------------------------------------------------------+
| RECORD 1 (Patient Numerical Results & Machine Flags):                                   |
| [host] [Send]<STX>MEK-7222\r   22\r01024\rCLOSED\rCBC + Diff\r01\rBLOOD\r01\r0002413\r |
| V03-02\rV04-02\rV03-01\r01536\r1\r\r2026\r08\r17\r\r14\r57\r05\r102\r                   |
|  4.1\r30.4*\r55.3*\r10.0*\r 2.7*\r 1.6*\r 1.3*\r 2.3*\r 0.4*\r 0.1*\r 0.1*\r           |
| 6.92H\r16.9\r52.7H\r76.2L\r24.4L\r32.1\r12.9\r 175\r0.13L\r 7.6\r17.6H\r<flags...><ETX>  |
+-----------------------------------------------------------------------------------------+
| RECORD 2 (Analyzer-Preset Reference Thresholds):                                        |
| [host] [Send]<STX>EXP\r00512\rMEK-7222\r01\r... 4.0\r 9.0\r28.0\r78.0...\r<ETX>         |
+-----------------------------------------------------------------------------------------+
```

#### Clinical Principle: Capturing Machine Calibration As-Is
The hematology analyzer is calibrated to operate with its own verified reference intervals, and the instrument's hardware flags (`*`, `H`, `L`) are directly derived from these preset intervals. AMH Lab Tracker captures the raw output as calculated and flagged by the instrument without recalculating or altering the clinical values. 

The parser isolates Record 1 to extract the patient values and hardware flags, while referencing the calibrated standard ranges to guarantee complete alignment with the instrument's official output.

---

### 2.3 Field Decomposition & Data Extraction Sequence

```
Index  Field Meaning                  Example Value      Extraction Rule
-----------------------------------------------------------------------------------------------
[0]    Device Header                  MEK-7222           Record validator ('MEK-7222' in line)
[1]    Parameter Count                22                 Verification marker
[2]    Machine Code                   01024              Hardware model config
[3]    Sampling Mode                  CLOSED / MANUAL    Tube presentation mode
[4]    Test Program                   CBC + Diff         Assay profile
[5]    Sample Type Code               01                 Matrix code
[6]    Sample Matrix Description      BLOOD              Matrix descriptor
[7]    Operator / Run ID              01 / MMM           Operator code
[8]    Sample ID                      0002413            6-8 digit regex match: ^\d{6,8}$
[9..11]Firmware Versions              V03-02, V04-02...  Analyzer firmware revisions
[12..14]Calibration Identifiers       01536, 1...        Calibration lot identifiers
[15..17]Date Fields (Split)           2026 \r 08 \r 17   Sequential: YYYY \r MM \r DD
[18]   Gap / Alignment Field          (whitespace)       Ignored spacer
[19..21]Time Fields (Split)           14 \r 57 \r 05     Sequential: HH \r MM \r SS
[22]   Run Status Code                102 / 134          3-digit integer code (100-999) - skipped
[23..44]22 CBC Numerical Values       4.1 \r 30.4* ...   Sequential value + flag extractor
[45+]  Morphology & Distribution      +  +  +            Flag matrices (RDW/PLT histograms)
```

---

### 2.4 Sequential CBC Parameter Mapping

The analyzer transmits parameters in a strict, unvarying sequence. The parser maps these positions directly to canonical database parameter definitions:

```
Seq  Database Parameter Name                      Unit       Clinical Category
-----------------------------------------------------------------------------------------------
01   Total WBC Count (White Blood Cells)          10³/µL     Main Leukocyte Index
02   Neutrophils (%) [Relative Count]             %          Relative Differential
03   Lymphocytes (%) [Relative Count]             %          Relative Differential
04   Monocytes (%) [Relative Count]               %          Relative Differential
05   Eosinophils (%) [Relative Count]             %          Relative Differential
06   Basophils (%) [Relative Count]               %          Relative Differential
07   Neutrophils (Absolute Count)                 10⁹/µL     Absolute Differential
08   Lymphocytes (Absolute Count)                 10⁹/µL     Absolute Differential
09   Monocytes (Absolute Count)                   10⁹/µL     Absolute Differential
10   Eosinophils (Absolute Count)                 10⁹/µL     Absolute Differential
11   Basophils (Absolute Count)                   10⁹/µL     Absolute Differential
12   Red Blood Cells (RBC)                        10⁶/µL     Main Erythrocyte Index
13   Hemoglobin (Hb)                              g/dL       Main Erythrocyte Index
14   Hematocrit (HCT)                             %          Main Erythrocyte Index
15   Mean Cell Volume (MCV)                       fL         Erythrocyte Constant
16   Mean Cell Hb (MCH)                           pg         Erythrocyte Constant
17   Mean Cell Hb Conc (MCHC)                     g/dL       Erythrocyte Constant
18   RBC Distribution Width (RDW)                 %          Erythrocyte Index
19   Platelets Count (PLT)                        10³/µL     Main Thrombocyte Index
20   Thrombocrit (PCT)                            %          Thrombocyte Index
21   Mean Platelet Volume (MPV)                   fL         Thrombocyte Index
22   PLT Distribution Width (PDW)                 %          Thrombocyte Index
```

---

## 3. Key Design Decisions & Technical Justifications

### 3.1 Dual-Mode Stream Parser (`_extract_fields`)

#### The Problem
When raw serial data is captured directly from an RS-232 COM port stream, fields are separated by bare carriage returns (`\r`). However, when laboratory technologists copy output from the supplier interfacing window and paste it into a web browser `<textarea>`, the operating system clipboard and browser DOM automatically normalize bare `\r` characters into newline characters (`\n`).

#### Technical Solution
`backend/app/parsers/nihon_kohden.py` implements a dual-mode extractor that dynamically inspects input characteristics:
- **Mode 1 (Raw Protocol Stream)**: Triggered when the `MEK-7222` line contains embedded `\r` delimiters. The line is parsed by splitting on `\r`.
- **Mode 2 (Clipboard Paste Stream)**: Triggered when each field has been converted to an individual `\n` line. The extractor collects lines beginning at the `MEK-7222` header and terminates upon encountering the `[host] [Send]EXP` reference-range boundary.

```python
def _extract_fields(raw_text: str) -> List[str]:
    text = raw_text.replace('\r\n', '\n')
    lines = text.split('\n')

    # Mode 1: Raw protocol (embedded \r within line)
    for line in lines:
        if 'MEK-7222' in line and 'EXP' not in line and '\r' in line and line.strip():
            return [f.strip() for f in line.split('\r')]

    # Mode 2: Clipboard paste (\n per field)
    fields: List[str] = []
    in_record = False
    for line in lines:
        stripped = line.strip()
        if not in_record:
            if 'MEK-7222' in line and 'EXP' not in line:
                in_record = True
                fields.append(stripped)
            continue
        if 'EXP' in line and ('[host]' in line or stripped == 'EXP'):
            break
        fields.append(stripped)
    return fields
```

---

### 3.2 In-Modal Capture vs Heavy External Middleware

#### Justification
- **Zero Local Client Drivers**: Traditional LIMS require proprietary COM port listener services, Windows background daemons, or MS Access ODBC bridges (`Interfacing.mdb`). This creates brittle installation dependencies on client PCs.
- **Network Agnostic & Offline Resilient**: The in-modal clipboard capture works across modern web browsers without local installation, specialized browser extensions, or administrative OS privileges.
- **Technician-in-the-Loop Verification**: Direct automatic writing to the database bypasses clinical review. In-modal capture pre-populates editable form rows, highlighting panic flags (`*`, `H`, `L`), allowing the technologist to inspect, calibrate, or manually adjust any parameter before saving.
- **Unified Single-Visit Integrity**: Parsing does not create independent visits or fragmented records. All 22 parameters are attached to the existing CBC order within the active visit.

---

### 3.3 Dedicated Single-Page ReportLab PDF Formatting

#### Strict Clinical Standard (`docs/reference/rptrchemcour.pdf`)
The entire Complete Blood Count (CBC) report is formatted on **one single dedicated page** in the generated PDF report. The table structure exactly mirrors the clinical reference standard (`docs/reference/rptrchemcour.pdf`):

```
+-----------------------------------------------------------------------------------------------------+
|                                      HAEMATOLOGY CBC REPORT                                         |
+-----------------------------------------------------------------------------------------------------+
| Test Name                      | Result    | Units          | Flag     | Ref. Ranges                |
+--------------------------------+-----------+----------------+----------+----------------------------+
| MAIN INDICES                   |           |                |          |                            |
| Total WBC Count                | 4.1       | (10^3 / uL)    |          | [ 6.0-14.0 ]               |
| Red Blood Cells (RBC)          | 6.92      | (10^6 / uL)    | High     | [ 4.00 -5.20 ]             |
| Hemoglobin (Hb)                | 16.9      | g/dL           |          | [ 11.5-15.5 ]              |
| Hematocrit (HCT)               | 52.7      | %              | High     | [ 35.0-45.0 ]              |
| Mean Cell Volume (MCV)         | 76.2      | fL             | Low      | [ 77.0-95.0 ]              |
| Mean Cell Hb (MCH)             | 24.4      | pg             | Low      | [ 23.0-31.0 ]              |
| Mean Cell Hb Conc.(MCHC)       | 32.1      | g/dL           |          | [ 28.0-33.0 ]              |
| Platelets Count                | 175       | (10^3 / uL)    |          | [ 150-400 ]                |
+--------------------------------+-----------+----------------+----------+----------------------------+
| RELATIVE DIFFERENTIAL (%)      |           |                |          |                            |
| Neutrophils                    | 30.4      | %              | *        | [ 40.0-65.0 ]              |
| Lymphocytes                    | 55.3      | %              | *        | [ 19.2-49.5 ]              |
| Monocytes                      | 10.0      | %              | *        | [ 4.5-12.1 ]               |
| Eosinophils                    | 2.7       | %              | *        | [ 1.0-12.0 ]               |
| Basophils                      | 1.6       | %              | *        | [ 0.0-2.0 ]                |
+--------------------------------+-----------+----------------+----------+----------------------------+
| ABSOLUTE DIFFERENTIAL (10^9/uL)|           |                |          |                            |
| Neutrophils                    | 1.3       | 10^9 / uL      | *        | [ 2.0-7.0 ]                |
| Lymphocytes                    | 2.3       | 10^9 / uL      | *        | [ 1.0-4.8 ]                |
| Monocytes                      | 0.4       | 10^9 / uL      | *        | [ 0.2-1.0 ]                |
| Eosinophils                    | 0.1       | 10^9 / uL      | *        | [ 0.0-0.5 ]                |
| Basophils                      | 0.1       | 10^9 / uL      | *        | [ 0.0-0.2 ]                |
+--------------------------------+-----------+----------------+----------+----------------------------+
| RBC & PLATELET INDICES         |           |                |          |                            |
| RBC Distribution Width (RDW)   | 12.9      | %              |          | [ 11.0-16.0 ]              |
| Thrombocrit (PCT)              | 0.13      | %              | Low      | [ 0.15-0.50 ]              |
| Mean Platelet Volume (MPV)     | 7.6       | fL             |          | [ 7.0-11.0 ]               |
| PLT Distribution Width (PDW)   | 17.6      | %              | High     | [ 15.0-17.0 ]              |
+--------------------------------+-----------+----------------+----------+----------------------------+
```

---

## 4. Technology Stack

| Layer | Component | Implementation |
| :--- | :--- | :--- |
| **Parser Engine** | `backend/app/parsers/nihon_kohden.py` | Pure Python tokenizer and regular expression engine with zero external third-party dependencies. |
| **Integration API** | `backend/app/routers/integrations.py` | FastAPI route `POST /api/integrations/parse-analyzer-output` with schema validation and authentication guards. |
| **Frontend UI Controller** | `frontend/static/js/app.js` | Modal paste drawer toggle, clipboard async dispatch, and DOM element population across `.modal-param-row`. |
| **Clinical PDF Renderer** | `backend/app/pdf_generator.py` | ReportLab flowables, categorized 4-section table, keep-together flowables, and signature block rendering on a single dedicated page. |
| **Test Suite** | `tests/test_nihon_kohden_parser.py`, `tests/test_integrations_api.py`, `tests/test_pdf_cbc_report.py` | Pytest fixtures covering raw serial streams, clipboard text, edge cases, and PDF layout validation. |

---

## 5. Non-Negotiables for Maintaining Architecture

1. **Technician Review Gate**: Never automatically persist analyzer output to the database without explicit user confirmation in the result entry modal.
2. **Structural Control Character Preservation**: Sanitization steps must preserve `\r` and `\n` while stripping non-printable ASCII bytes (`\x00-\x09`, `\x0b-\x0c`, `\x0e-\x1f`, `\x7f`).
3. **Hardware Flag & Range Preservation**: Machine flags (`*`, `H` for high, `L` for low) and calibrated reference ranges must be reported as-is without alteration.
4. **Single-Page CBC Layout**: The PDF generator must always render the complete 22-parameter CBC report on a single dedicated page matching `docs/reference/rptrchemcour.pdf`.
5. **No Emojis & Clean UI Standards**: In accordance with `docs/BEST_PRACTICES.md`, no emojis or pill badges may be introduced to the analyzer UI or logs.

---

## 6. Potential Future Improvements

1. **WebSerial API Direct Capture**: Integrate modern browser WebSerial API to allow technologists to connect RS-232 USB-to-Serial adapters directly to the browser, capturing transmissions with a single "Read Analyzer" button without manual clipboard copying.
2. **Support for Additional Hematology & Chemistry Analyzers**:
   - Mindray BC-series (BC-2800, BC-3000, BC-5000).
   - Human Diagnostics Humalyzer & HumaCount series.
   - Sysmex XP / XN hematology analyzers.
3. **Standard ASTM E1381 / E1394 & HL7 v2 Interfacing**: Implement a bidirectional background microservice supporting full ASTM/HL7 protocols for automated query and batch result uploads across hospital local area networks.

