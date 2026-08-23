# Software Requirements Specification (SRS)
## AMH Lab Tracker — System Architecture, Data Models & Security
**Ahmadiyya Muslim Hospital (AMH) — Mbale, Uganda**

---

### 1. System Tech Stack & Environment Constraints

The **AMH Lab Tracker** is architected to perform seamlessly under stringent local hardware limitations while maintaining full portability and forward-compatibility with modern operating systems and potential future cloud/containerized deployments.

#### 1.1 Core Backend & Shell Runtime
*   **Application Language:** Python 3.11+
*   **Web Server Framework:** FastAPI. Selected for its high execution speed, automatic OpenAPI documentation, and minimal memory footprint.
*   **ASGI Server:** Uvicorn. Runs as a lightweight local background daemon.
*   **Local Desktop Container:** `pywebview` (Python desktop shell wrapping Edge WebView2 on Windows or WebKitGTK on Linux).
*   **Unconditional Browser Fallback:** If PyWebView initialization fails due to legacy graphics drivers or missing native OS web components, the launcher automatically triggers `webbrowser.open()` to launch the user's default browser pointed to localhost.
*   **No-Cloud Isolation:** The app operates 100% offline, binding exclusively to the local loopback adapter (`127.0.0.1`) at port `8756`. This provides an impenetrable hardware-level firewall against cross-network eavesdropping over local Wi-Fi or LAN.

#### 1.2 Target Hardware & Compatibility Tuning
To accommodate Ahmadiyya Muslim Hospital Mbale's low-specification computers (Intel Core 2 Duo era, 2GB RAM), the application is tuned with the following constraints:
*   **Process Isolation:** The Python FastAPI backend runs as a single-threaded local process with minimal active workers, consuming less than **50MB of RAM** at rest.
*   **No Developer-Mode Overhead:** Development flags such as Uvicorn's `reload=True` are strictly disabled in production. This eliminates continuous file-system scanning and directory watching, which would saturate legacy hard drive I/O and freeze the system.
*   **Offline Dependencies:** All application dependencies are packaged as pre-compiled Python wheel (`.whl`) files stored in `usb_drive/wheels/` to allow zero-network installations on air-gapped host machines.

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
Data ownership belongs solely to Ahmadiyya Muslim Hospital. The system employs a 3-tier RBAC system:
*   **Super Admin:** A strictly singular account generated upon bootstrap. The only account capable of approving Administrators and wiping audit tables if necessary.
*   **Admin Profile:** Authorized to perform password overrides, reset security questions, add or delete test items, configure critical limits, and inspect the immutable audit logs.
*   **Staff Profile (Technician):** Authorized to register client profiles, log orders, and input test values. Blocked from altering global settings, performing data deletions, or resetting other users' credentials.

#### 4.2 Unified Security Recovery Handshake
1.  **Administrative Override:** If a user forgets their password, the **Admin Profile** can execute a manual override to reset the account's password to a temporary placeholder and require a password change on next login (`password_reset_required`). 
2.  **Clinical Data Integrity Safeguard:** Under no circumstances shall password resets or account locking interfere with or touch existing test data, patient history, or clinical records.

---

### 5. Physical & Technical Session Security
Because lab workstations at AMH are shared physically by multiple technicians, session security must prevent "walk-away" vulnerabilities.
#### 5.1 The 15-Minute Inactivity Session Timeout
*   **Frontend Activity Daemon:** The client application (`app.js`) operates a background activity listener. If no interaction is detected for exactly **15 minutes**, the frontend daemon immediately logs the user out.
*   **Backend Token Expiration:** All user sessions are backed by short-lived tokens. The backend database `expires_at` timestamp is enforced.

#### 5.2 Physical Workstation Hardening
*   **Automatic Screen Lockouts:** Workstation operating systems must be configured with a matching 15-minute screen saver lockout.

---

### 6. Flexible Reference Range & Clinical Flagging Engine
*Intended Final State:*
A critical requirement of the AMH Lab Tracker is its dual-mode clinical flagging engine, which accommodates both vendor-calibrated hardware and manual test parameters. The system will be seeded with standard clinical reference ranges for common panels (CBC, LFTs, RFTs).

#### 6.1 Device-Preset Mode (`DEVICE_PRESET`)
*   **Protocol:** For parameters flagged as `DEVICE_PRESET` (e.g., from an analyzer integration), the AMH Lab Tracker bypasses internal validation rules and records the clinical values and alerts exactly as transmitted from the analyzer to preserve calibration fidelity.

#### 6.2 LIMS-Evaluated Mode (`LIMS_EVALUATED`)
*   **Protocol:** The LIMS dynamically evaluates clinical ranges using the schema defined in `test_parameters`. If a value falls outside the defined range or breaches the `critical_low`/`critical_high` thresholds, it is dynamically stamped in the database with standard clinical codes (`H`, `L`, `CH`, `CL`).

---

### 7. Analyzer Integrations & PDF Exports (Intended State)
#### 7.1 Selectable PDF Export Engine (ReportLab)
To support the delivery of official clinical test results to clients as digital softcopies, the system will integrate a purely local PDF generation engine using **ReportLab** for vector-based, selectable text that requires no OS dependencies (like `wkhtmltopdf` or browser-engines).
*   **Compliance:** PDF layouts will comply with **ISO 15189**, containing laboratory headers, double-identifier client info, order metadata, codified results, reference intervals, and immutable signatures.

#### 7.2 Automated Analyzer Integration Workflow
The system will feature a generic "Analyzer Clipboard Portal":
1.  **Frontend Interface:** A generic text ingestion area on the test order screens labeled "Import Analyzer Data".
2.  **Modular Backend Parser:** A fast, adaptable RegEx parsing engine (`/api/orders/analyzer-import`) designed to interpret raw data strings (such as plain-text SQL or HL7 rows) exported from various automated analyzers. This enables instantaneous extraction of key values (e.g., WBC, RBC, HGB, HCT, PLT) without fragile OCR overhead or strict vendor lock-in.

---

### 8. Immutable Audit Logging & Data Integrity
#### 8.1 FDA 21 CFR Part 11 Standard Audit Trail
The `audit_log` table stores high-granularity technical payloads, including user attribution, loopback IP addresses, and complete JSON data diffs (`old_values` vs `new_values`). The table is append-only with no backend deletion functions.

#### 8.2 Soft Deletes & Statistics Integrity
No client files or diagnostic orders can be physically deleted.
*   **Implementation:** Primary tables will utilize the `is_deleted` BOOLEAN flag. Destructive actions execute `UPDATE is_deleted = 1`.
*   **Query Safety:** All analytical and reporting queries (e.g., daily aggregates) must explicitly include `WHERE is_deleted = 0` to prevent statistical contamination.

---

### 9. Security & Performance Benchmarks
To ensure the AMH Lab Tracker operates smoothly on Mbale's legacy computers, the following non-functional benchmarks are enforced:

| Operational Metric | Target Benchmark | Verification Method |
| :--- | :--- | :--- |
| **System RAM Footprint** | <= 150 MB (Uvicorn + Python + PyWebView) | Task Manager monitoring |
| **Client Search Latency** | <= 200 ms for database lookup (5k records) | Chrome DevTools profiling |
| **Page-View Load Time** | <= 100 ms (Instantaneous SPA Tab Switch) | Local lighthouse auditing |
| **PDF Generation Speed** | <= 1.5 seconds for multi-page vector PDF | ReportLab performance logging |

**Security Benchmarks:**
*   **Password Hashing Complexity:** PBKDF2 with SHA-256 and a minimum of 100,000 iterations.
*   **Local Port Isolation:** Binds strictly to `127.0.0.1:8756`, rejecting any inbound LAN or Wi-Fi traffic.
