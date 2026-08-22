# Nihon Kohden MEK-7222 Hematology Analyzer Integration & Parser

## 1. Executive Summary & Context

The Complete Blood Count (CBC) is the highest-volume multi-parameter diagnostic test in the clinical laboratory, consisting of 22 sequential numeric parameters and morphological flags. Manual transcription of 22 parameters per client sample from analyzer printouts or screen displays into a LIMS introduces significant transcription risk, cognitive fatigue, and administrative delay.

The AMH Lab Tracker integrates automated output parsing for the **Nihon Kohden MEK-7222 / Celltac series** (and compatible MEK-7300 serial communication formats). This module enables laboratory technologists to capture raw analyzer transmission streams via serial clipboard paste, instantaneously extracting Sample IDs, transmission timestamps, hardware flags, and all 22 CBC parameters into the interactive result entry workbench.

---

## 2. Real Transmission Protocol & Wire Format Analysis

### 2.1 Serial Protocol Characteristics

The Nihon Kohden MEK-7222 analyzer transmits sample data over an RS-232 serial interface using standard ASCII control characters and carriage-return delimited fields:

| Element | ASCII Hex | Representation | Function |
| :--- | :--- | :--- | :--- |
| **STX** | `0x02` | `\x02` / `^B` | Start of Transmission Frame |
| **ETX** | `0x03` | `\x03` / `^C` | End of Transmission Frame |
| **CR** | `0x0D` | `\r` | Field Delimiter (Bare Carriage Return) |
| **LF** | `0x0A` | `\n` | Record Delimiter (Line Feed) |

### 2.2 Dual Record Structure

Each sample transmission consists of two distinct records separated by a newline (`\n`):

1. **Record 1 (Patient Test Results)**: Starts with `[host] [Send]<STX>MEK-7222` and contains client sample identification, acquisition timestamp, run status code, 22 numerical parameters with machine flags, and morphology alert distributions.
2. **Record 2 (Analyzer Reference Ranges)**: Starts with `[host] [Send]<STX>EXP` and transmits internal factory reference intervals. **This record must be discarded by the parser** to prevent token bloat and numeric collisions.

```
+-----------------------------------------------------------------------------------------+
| RECORD 1 (Patient Data):                                                                |
| [host] [Send]<STX>MEK-7222\r   22\r01024\rCLOSED\rCBC + Diff\r01\rBLOOD\r01\r0002413\r |
| V03-02\rV04-02\rV03-01\r01536\r1\r\r2026\r08\r17\r\r14\r57\r05\r102\r                   |
|  4.1\r30.4*\r55.3*\r10.0*\r 2.7*\r 1.6*\r 1.3*\r 2.3*\r 0.4*\r 0.1*\r 0.1*\r           |
| 6.92H\r16.9\r52.7H\r76.2L\r24.4L\r32.1\r12.9\r 175\r0.13L\r 7.6\r17.6H\r<flags...><ETX>  |
+-----------------------------------------------------------------------------------------+
| RECORD 2 (Factory Reference Intervals - Ignored):                                       |
| [host] [Send]<STX>EXP\r00512\rMEK-7222\r01\r... 4.0\r 9.0\r28.0\r78.0...\r<ETX>         |
+-----------------------------------------------------------------------------------------+
```

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
When raw serial data is captured directly from an RS-232 COM port stream, fields are separated by bare carriage returns (`\r`). However, when laboratory technologists copy output from terminal software or host viewers and paste it into a web browser `<textarea>`, the operating system clipboard and browser DOM automatically normalize bare `\r` characters into newline characters (`\n`).

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

---

### 3.3 Dedicated ReportLab PDF Formatting

#### Justification
A 22-parameter CBC report exceeds the standard tabular constraints of regular chemistry or rapid diagnostic tests. To match standard laboratory printing conventions (e.g., matching the reference template `rptrchemcour.pdf`), the PDF generation engine (`backend/app/pdf_generator.py`) generates a dedicated **HAEMATOLOGY CBC REPORT** page organized into 4 logical clinical sections:
1. **Main Indices**: WBC, RBC, Hb, HCT, MCV, MCH, MCHC, PLT.
2. **Relative Differential (%)**: Neutrophils, Lymphocytes, Monocytes, Eosinophils, Basophils.
3. **Absolute Differential (10⁹/µL)**: Neutrophils, Lymphocytes, Monocytes, Eosinophils, Basophils.
4. **RBC & Platelet Indices**: RDW, PCT, MPV, PDW.

Columns include: `Test`, `Result`, `Units`, `Flag` (`Low`, `High`, `Panic *`), and `Ref. Ranges`.

---

## 4. Technology Stack

| Layer | Component | Implementation |
| :--- | :--- | :--- |
| **Parser Engine** | `backend/app/parsers/nihon_kohden.py` | Pure Python tokenizer and regular expression engine with zero external third-party dependencies. |
| **Integration API** | `backend/app/routers/integrations.py` | FastAPI route `POST /api/integrations/parse-analyzer-output` with schema validation and authentication guards. |
| **Frontend UI Controller** | `frontend/static/js/app.js` | Modal paste drawer toggle, clipboard async dispatch, and DOM element population across `.modal-param-row`. |
| **Clinical PDF Renderer** | `backend/app/pdf_generator.py` | ReportLab flowables, categorized section tables, keep-together flowables, and signature block rendering. |
| **Test Suite** | `tests/test_nihon_kohden_parser.py`, `tests/test_integrations_api.py`, `tests/test_pdf_cbc_report.py` | Pytest fixtures covering raw serial streams, clipboard text, edge cases, and PDF layout validation. |

---

## 5. Non-Negotiables for Maintaining Architecture

1. **Technician Review Gate**: Never automatically persist analyzer output to the database without explicit user confirmation in the result entry modal.
2. **Structural Control Character Preservation**: Sanitization steps must preserve `\r` and `\n` while stripping non-printable ASCII bytes (`\x00-\x09`, `\x0b-\x0c`, `\x0e-\x1f`, `\x7f`).
3. **Hardware Flag Preservation**: Machine flags (`*` for panic/uncertainty, `H` for high, `L` for low) must be extracted and preserved alongside numeric values for clinician decision support.
4. **Reference Range Record Rejection**: Any record identified with the `EXP` header must be discarded to prevent contamination of patient parameter values.
5. **No Emojis & Clean UI Standards**: In accordance with `docs/BEST_PRACTICES.md`, no emojis or pill badges may be introduced to the analyzer UI or logs.

---

## 6. Potential Future Improvements

1. **WebSerial API Direct Capture**: Integrate modern browser WebSerial API to allow technologists to connect RS-232 USB-to-Serial adapters directly to the browser, capturing transmissions with a single "Read Analyzer" button without manual clipboard copying.
2. **Support for Additional Hematology & Chemistry Analyzers**:
   - Mindray BC-series (BC-2800, BC-3000, BC-5000).
   - Human Diagnostics Humalyzer & HumaCount series.
   - Sysmex XP / XN hematology analyzers.
3. **Standard ASTM E1381 / E1394 & HL7 v2 Interfacing**: Implement a bidirectional background microservice supporting full ASTM/HL7 protocols for automated query and batch result uploads across hospital local area networks.
