# Software Requirements Specification (SRS)
## M-LIS — System Architecture, Data Models & Security
**Laboratory Information System**

---

### 1. System Tech Stack & Environment Constraints

**M-LIS** is architected to perform seamlessly under stringent local hardware limitations while maintaining full portability and forward-compatibility with modern operating systems and potential future cloud/containerized deployments.

#### 1.1 Core Backend & Shell Runtime
*   **Application Language:** Python 3.11+
*   **Web Server Framework:** FastAPI. High execution speed, automatic OpenAPI documentation, and minimal memory footprint.
*   **ASGI Server:** Uvicorn. Runs as a lightweight local background daemon bound to `127.0.0.1:8756`.
*   **Zero-Install Desktop Browser:** **Firefox ESR Portable** bundled directly in `portable_browser/firefox/`. Pre-configured to render full modern HTML5/CSS3/ES2022 without depending on the host operating system's installed browser versions.
*   **No-Cloud Isolation:** The app operates 100% offline, binding exclusively to the local loopback adapter (`127.0.0.1`) at port `8756`. This provides an impenetrable hardware-level firewall against cross-network eavesdropping over local Wi-Fi or LAN.

#### 1.2 Target Hardware & Compatibility Tuning
To accommodate low-specification clinical workstations (Intel Core 2 Duo era, **1.0 GB RAM**), the application is tuned with the following constraints:
*   **Process Isolation:** The Python FastAPI backend runs as a single-process local daemon consuming less than **50MB of RAM** at rest.
*   **Predictable Client Footprint:** The bundled portable browser runs with a low baseline memory profile (~**80MB RAM**), preventing pagefile thrashing on 1GB physical memory machines.
*   **No Developer-Mode Overhead:** Development flags such as Uvicorn's `reload=True` are strictly disabled in production. This eliminates continuous file-system scanning and directory watching, which would saturate legacy hard drive I/O and freeze the system.
*   **Offline Dependencies:** All application dependencies are packaged as pre-compiled Python wheel (`.whl`) files stored in `offline_packages/wheels/` to allow zero-network installations on air-gapped host machines.

---

### 2. Database Engine: SQLite with WAL (Write-Ahead Logging)

To achieve maximum data integrity and reliable concurrent operation without the resource overhead of heavy client-server database engines, the system utilizes **SQLite**. 

#### 2.1 WAL Mode Mechanics
*   **Concurrent Reads/Writes:** In WAL mode, writes do not block readers, and readers do not block writes. This ensures that while a technician is saving a large daily batch log, another view can concurrently run intensive trend queries or generate reports without experiencing system freezes.
*   **Foreign Key Enforcement:** Foreign keys are explicitly turned on for every connection to guarantee relational integrity.

#### 2.2 Connection Factory Implementation
The database connection factory (`backend/app/database.py`) enforces WAL mode and relational integrity during initialization:
```python
import sqlite3
import os

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn
```

---

### 3. Relational Database Schema & Data Models

To align the codebase with clean domain-driven laboratory practices, the schema has been fully refactored to use the **`clients`** domain vocabulary. All diagnostic services are recorded for "Clients". 
*Note: The schema below represents the intended final state, including planned soft-delete flags and critical value columns.*

#### 3.1 Relational SQLite Schema
```sql
BEGIN TRANSACTION;

-- 1. User Management & Authorization
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff', -- 'staff', 'admin', 'superadmin'
    cadre TEXT, -- e.g., 'Medical Laboratory Assistant'
    is_active BOOLEAN NOT NULL DEFAULT 1,
    password_reset_required BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token TEXT UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Client Registry
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_number TEXT UNIQUE NOT NULL, 
    full_name TEXT NOT NULL,
    date_of_birth DATE,
    sex TEXT,
    phone TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Laboratory Catalog Configuration
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL, 
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    section_id INTEGER NOT NULL REFERENCES sections(id),
    is_tracked BOOLEAN NOT NULL DEFAULT 0, 
    is_active BOOLEAN NOT NULL DEFAULT 1,  
    parent_rollup_id INTEGER REFERENCES tests(id),
    sort_order INTEGER DEFAULT 0,
    UNIQUE(name, section_id)
);

CREATE TABLE IF NOT EXISTS test_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES tests(id),
    parameter_name TEXT NOT NULL,
    unit TEXT,                    
    ref_range TEXT,               
    critical_low REAL, -- Intended state: seeded default thresholds
    critical_high REAL, -- Intended state: seeded default thresholds
    sort_order INTEGER DEFAULT 0
);

-- 4. Clinical Workflow Transactions
CREATE TABLE IF NOT EXISTS test_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    test_id INTEGER NOT NULL REFERENCES tests(id),
    sample_id TEXT, 
    ordered_by_user_id INTEGER REFERENCES users(id),
    ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    is_deleted BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES test_orders(id),
    parameter_id INTEGER REFERENCES test_parameters(id),
    result_value TEXT,            
    is_positive BOOLEAN,          
    entered_by_user_id INTEGER REFERENCES users(id),
    entered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified_by_user_id INTEGER REFERENCES users(id),
    verified_at DATETIME,
    is_deleted BOOLEAN NOT NULL DEFAULT 0
);

-- 5. Legacy/Aggregated Daily Entries Log
CREATE TABLE IF NOT EXISTS daily_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE NOT NULL,
    test_id INTEGER NOT NULL REFERENCES tests(id),
    done INTEGER NOT NULL DEFAULT 0,
    positive INTEGER,
    entered_by_user_id INTEGER REFERENCES users(id),
    entered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by_user_id INTEGER REFERENCES users(id),
    updated_at DATETIME,
    UNIQUE(entry_date, test_id)
);

-- 6. Central Audit Trail (Immutable)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL, 
    detail TEXT,         
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
```

---

### 4. User Governance & Access Control
#### 4.1 Data Ownership & Role-Based Access Control (RBAC)
Data ownership belongs solely to the implementing medical facility. The system employs a 3-tier RBAC system:
*   **Super Admin:** A strictly singular account generated upon bootstrap. The only account capable of approving Administrators, configuring facility identity, and managing audit tables if necessary.
*   **Admin Profile:** Authorized to perform password overrides, reset security questions, add or delete test items, configure critical limits, and inspect the immutable audit logs.
*   **Staff Profile (Technician):** Authorized to register client profiles, log orders, and input test values. Blocked from altering global settings, performing data deletions, or resetting other users' credentials.

#### 4.2 Unified Security Recovery Handshake
1.  **Administrative Override:** If a user forgets their password, the **Admin Profile** can execute a manual override to reset the account's password to a temporary placeholder and require a password change on next login (`password_reset_required`). 
2.  **Clinical Data Integrity Safeguard:** Under no circumstances shall password resets or account locking interfere with or touch existing test data, patient history, or clinical records.

---

### 5. Physical & Technical Session Security
Because lab workstations are shared physically by multiple technicians, session security must prevent "walk-away" vulnerabilities.
#### 5.1 The 15-Minute Inactivity Session Timeout
*   **Frontend Activity Daemon:** The client application (`app.js`) operates a background activity listener. If no interaction is detected for exactly **15 minutes**, the frontend daemon immediately logs the user out.
*   **Backend Token Expiration:** All user sessions are backed by short-lived tokens. The backend database `expires_at` timestamp is enforced.

#### 5.2 Physical Workstation Hardening
*   **Automatic Screen Lockouts:** Workstation operating systems must be configured with a matching 15-minute screen saver lockout.

---

### 6. Flexible Reference Range & Clinical Flagging Engine
M-LIS implements a high-performance clinical flagging engine (`backend/app/evaluator.py`, `backend/app/biochem_validator.py`) accommodating both vendor-calibrated hardware and manual test parameters. The system is pre-seeded with standard clinical reference ranges for common panels (CBC, LFTs, RFTs, Blood Glucose, Urinalysis).

#### 6.1 Device-Preset Mode (`DEVICE_PRESET`)
*   **Protocol:** For parameters flagged as `DEVICE_PRESET` (e.g., from an automated analyzer integration), M-LIS bypasses internal range validation and records clinical values and flags exactly as transmitted from the analyzer to preserve calibration fidelity.

#### 6.2 LIMS-Evaluated Mode (`LIMS_EVALUATED`)
*   **Protocol:** The LIMS dynamically evaluates clinical ranges using the configuration defined in `test_parameters`. If a value falls outside defined limits or breaches `critical_low`/`critical_high` thresholds, it is stamped in the database with standard clinical codes (`H`, `L`, `CH`, `CL`) and triggers real-time UI indicator badges.

#### 6.3 Algorithmic Diagnostic Outcome Derivation (Uganda MoH HIV 3-Test Protocol)
The evaluation engine (`backend/app/evaluator.py:derive_hiv_outcome`) executes a deterministic truth table for sequential rapid antibody testing:

| Screening ($A_1$) | Confirmatory ($A_2$) | Tie-Breaker ($A_3$) | Conclusive Status | Display Result | Clinical Action / Advisory |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Non-Reactive** | *Not Required* | *Not Required* | `Negative` | `Negative` | Non-reactive screening. Routine counseling. |
| **Reactive** | **Reactive** | *Not Done* / **Reactive** | `Positive` | `Positive` | Concordant reactive. ART baseline referral. |
| **Reactive** | **Reactive** | **Non-Reactive** | `Inconclusive` | `Inconclusive` | Discrepant antibody finding. Repeat draw in 14 days. |
| **Reactive** | **Non-Reactive** | **Non-Reactive** | `Negative` | `Negative` | Discordance resolved negative. |
| **Reactive** | **Non-Reactive** | **Reactive** | `Inconclusive` | `Inconclusive` | Discordant pattern. Repeat draw in 14 days. |
| **Reactive** | **Non-Reactive** | *Not Done* | `Inconclusive` | `Inconclusive` | Discordant confirmation; $A_3$ tie-breaker required. |

*   **HIVST Self-Test Screening:** Reactive self-test yields `Inconclusive` with clinical advisory mandating full 3-test clinical algorithm prior to ART initiation. Non-reactive self-test yields `Negative`.
*   **Decoupled EID Assays:** Molecular Early Infant Diagnosis (`EID 1st PCR`, `EID 2nd PCR`, and `EID Final Rapid Test`) are evaluated independently as standalone assays, isolated from rapid antibody panel logic.

---


### 7. Analyzer Integrations & ReportLab PDF Engine

#### 7.1 ISO 15189 Selectable PDF Generator (ReportLab)
Official clinical test results are generated as digital softcopies and printable reports via **ReportLab** (`backend/app/routers/pdf_report_generator.py`):
*   **Compliance:** Meets **ISO 15189** guidelines: institutional header, dual client identifiers (Client Name & Sequential Lab Number), test metadata, structured 2-column CBC layout, reference intervals, biochemical flags, and verifier digital signature timestamp.
*   **Zero External Dependencies:** Pure Python implementation; requires no external browser drivers, headless daemons, or `wkhtmltopdf`.

#### 7.2 Automated Analyzer Integration Workflow (Nihon Kohden MEK-6500K)
The system features a generic "Analyzer Clipboard Portal":
*   **Frontend Interface:** Direct paste modal accessible from CBC result entry.
*   **Modular Backend Parser:** RegEx parser (`backend/app/parsers/nihon_kohden.py`) extracts all 18 CBC parameters (WBC, RBC, HGB, HCT, MCV, MCH, MCHC, PLT, NE%, LY%, MO%, EO%, BA%, etc.) instantly without vendor lock-in or manual typing.

---

### 8. Reagents & Consumables Inventory Architecture

#### 8.1 FIFO Stock Ledger Engine
Diagnostic reagents and test kits (e.g., HIV Determine/STAT-PAK, Malaria RDTs) are tracked via `backend/app/routers/stock.py`:
*   **Batch Lot Allocation:** First-In, First-Out (FIFO) lot allocation with automatic depletion tracking.
*   **Buffer Threshold Alerts:** Dynamic calculation of `LOW_STOCK` and `EXPIRED` status flags with prominent UI alert banners.
*   **Immutable Transaction Audit:** Logs all receipts, consumptions, and manual QC wastage.

---

### 9. Immutable Audit Logging & Data Integrity

#### 9.1 FDA 21 CFR Part 11 Standard Audit Trail
The `audit_log` table stores high-granularity technical payloads, including user attribution, loopback IP addresses, and complete JSON data diffs (`old_values` vs `new_values`). The table is append-only with no backend deletion functions.

#### 9.2 Soft Deletes & Statistics Integrity
No client files or diagnostic orders can be physically deleted.
*   **Implementation:** Primary tables utilize the `is_deleted` BOOLEAN flag. Destructive actions execute `UPDATE is_deleted = 1`.
*   **Query Safety:** All analytical and reporting queries (e.g., daily aggregates) explicitly include `WHERE is_deleted = 0` to prevent statistical contamination.

---

### 10. Security & Performance Benchmarks
To ensure M-LIS operates smoothly on legacy computers, the following non-functional benchmarks are enforced:

| Operational Metric | Target Benchmark | Verification Method |
| :--- | :--- | :--- |
| **System RAM Footprint** | <= 150 MB combined (FastAPI <50MB, Portable Firefox ~80MB) | Task Manager monitoring |
| **Client Search Latency** | <= 200 ms for database lookup (5k records) | Performance profiling |
| **Page-View Load Time** | <= 100 ms (Instantaneous SPA Tab Switch) | DOM timing benchmarks |
| **PDF Generation Speed** | <= 1.5 seconds for vector PDF report | ReportLab performance logging |

**Security Benchmarks:**
*   **Password Hashing Complexity:** PBKDF2 with SHA-256 and a minimum of 100,000 iterations.
*   **Local Port Isolation:** Binds strictly to `127.0.0.1:8756`, rejecting any inbound LAN or Wi-Fi traffic.
