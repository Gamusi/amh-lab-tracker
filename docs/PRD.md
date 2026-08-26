# Product Requirements Document (PRD)
## M-LIS — Laboratory Information System
**Airgapped Clinical Laboratory Database & Reporting System**

---

### 1. Executive Summary & Product Vision
**M-LIS** is a proprietary, offline-first clinical laboratory information system engineered specifically for resource-constrained, airgapped healthcare and diagnostic facilities.

The primary vision of M-LIS is to establish a secure, modern, and highly performant database-backed system that runs completely locally and offline. Designed to support 100% digital data capture, the system eliminates manual recording gaps by requiring all diagnostic tests to be logged in the application before results are printed.

The system delivers three core pillars of modern laboratory operations:
1. **Uncompromising Data Integrity:** A robust relational SQLite database that replaces manual registries, ensuring all records are securely structured, search-indexed, and immune to accidental file deletions or database corruption.
2. **Operational Accountability:** An automated background audit trail that logs every user login, client record creation, test configuration edit, and result update with precise time, date, and user stamps.
3. **Clinical Compliance & Standards:** Features built directly to support clinical laboratory standards of practice, such as role-based user access controls mapping directly to national Ministry of Health (MoH) cadres, automated verification, configurable critical value alerts, and individual technician attribution on all official printed report slips.

---

### 2. Operating Environment & Technical Constraints
To run effectively in constrained clinical environments, M-LIS is optimized for highly constrained infrastructure, strictly adhering to these operational boundaries:
* **Host Hardware Limitations:** The laboratory operates legacy workstation computers (typically Intel Core 2 Duo era processors with 2GB of RAM). The application must consume minimal system resources (prohibiting heavy modern shells like Electron) to prevent system freezes or slow-downs.
* **Network Isolation (Air-Gap):** The laboratory is completely offline, with no reliable internet connectivity. The application must run **100% locally** on a single computer, with zero external dependencies, CDNs, or cloud-hosted services.
* **Offline Deployment Strategy:** All software installations, upgrades, and library dependencies must be delivered on physical USB flash drives containing pre-compiled, offline Python wheel (`.whl`) files and local installation scripts (`install.py`, `pack_usb.bat`).
* **Local Loopback Security:** To ensure privacy and protect electronic health records from unauthorized external access over local Wi-Fi or LAN, the server must bind strictly to the local loopback interface (`127.0.0.1`) at port `8756`.

---

### 3. User Personas & Workflows

#### Persona A: The Laboratory Technician (The Core Operator)
* **Profile:** Trained clinical laboratory professionals who perform diagnostic assays, record results, and generate printed reports for clients. Their computer literacy is basic to moderate.
* **Operational Reality:** Techs work under highly dynamic diagnostic pressures, where client volume and test queues dictate their logging pace. They operate in two distinct workflows:
  * *Real-Time Entry:* Logging client demographics and test results immediately at the testing bench as assays are run.
  * *Batch Transcription:* Entering several records in rapid succession during peak hours or at the end of a high-volume shift.
* **Critical Needs:**
  * **Dynamic Printing Integration:** Every test run must be captured in the database to enable the printing of official results.
  * **Rapid Keyboard-Driven UI:** Tab and Enter-focused navigation keybinds to allow rapid batch data entry without taking hands off the keyboard.
  * **Strict Data Validation:** Constrained numeric fields and dropdown test selections to prevent invalid or corrupt data entries.

#### Persona B: The Laboratory Administrator / Director
* **Profile:** Senior laboratory director or supervisor responsible for general operations, quality assurance, and compliance with national standards.
* **Operational Reality:** Monitors overall testing throughput, positivity rates, and system audit logs. They require accurate, aggregated reporting to assist in disease surveillance.
* **Critical Needs:**
  * **Full Traceability:** Trace every printed report and database entry to the exact technician who performed the work.
  * **Audit Log Viewer:** A secure, read-only interface displaying an immutable ledger of all system edits.
  * **Flexible System Management:** A dedicated configuration panel to add/update tests and manage user accounts.

---

### 4. Functional Requirements & Epics

#### Epic 1: Multi-User Profile Governance & RBAC
To ensure compliance with clinical standards (ISO 15189), the system enforces strict individual accountability:
* **Self-Registration:** Staff can register unique accounts.
* **3-Tier Role-Based Access Control (RBAC):**
  * *Staff:* Can register clients, log tests, enter results, view trends, and print reports. Prohibited from deleting records or altering configs.
  * *Administrators:* Can manage lower-tier user accounts, modify/disable tests, and view the immutable audit log.
  * *Super Admin:* A strictly singular account generated upon bootstrap. The only account capable of approving Administrators and wiping audit tables if necessary. No user can be promoted to Super Admin.
* **Uganda MoH Cadres:** Every user must be mapped to one of the 7 official MoH cadres (e.g., Medical Laboratory Assistant, Medical Laboratory Technologist) for strict professional accountability.
* **Auto-Session Timeout:** The frontend automatically locks the screen and logs the user out if no mouse or keyboard activity is detected for 15 minutes.

#### Epic 2: Dynamic Test Menu Configuration
The lab menu is dynamic and must expand or contract with clinical offerings:
* **Custom Test Definition:** Administrators can create new tests, define reference ranges, specify units of measure, and group them by laboratory section.
* **Test Soft-Deletion:** If a test has historical logs attached, the system performs a soft-delete (marking it inactive) to preserve historical data integrity while removing it from the active menu.

#### Epic 3: Complete Paperless Operations & Printing Integration
M-LIS replaces the physical paper register entirely:
* **100% Database Capture:** The database acts as the single source of truth.
* **Result Printing Workflow:** The web frontend dynamically triggers the system print dialog. CSS `@media print` rules strip the UI to generate clean, formatted results in a standardized letterhead layout.

#### Epic 4: Configurable Clinical Critical Value Alerts
To comply with ISO 15189 regarding alert values, the system features a built-in clinical warning engine:
* **Seeded Standards:** The database will be seeded with standard critical values for common panels (CBC, LFTs, RFTs, Blood Sugar) based on Ugandan national clinical standards.
* **Dynamic Configuration:** Administrators can dynamically update these critical thresholds via the UI.
* **Non-Disruptive UI Alerts:** Out-of-bounds results trigger high-visibility, high-contrast visual indicators (red highlights, 'CRITICAL' flag) directly on the results screen, without using disruptive modal pop-ups that block typing flow.

#### Epic 5: Immutable System Audit Logging
To meet international regulatory requirements, the application runs a background audit system:
* **Background Recording:** Every database modification is caught automatically.
* **Immutability:** The audit log captures precise timestamps, the active user, and before/after values in a read-only sequence.

---

### 5. UI/UX & Interface Specifications

#### "Less is More" Aesthetic Philosophy
* **Performance Over Decoration:** The interface utilizes a lightweight, highly functional design. While the system must feel modern, warm, and welcoming, performance on legacy hardware is the absolute highest priority. 
* **Resource Constraint:** The UI avoids heavy UI frameworks, complex dark-mode engines, and resource-heavy JavaScript. Lightweight CSS (such as subtle, CSS-only micro-animations or soft borders) is permitted *only* if it does not compromise the instantaneous feel of the application.
* **High-Contrast Clinical Colors:** A high-contrast medical color scheme ensures readable text on low-brightness clinical monitors.

#### Interaction Guidelines
* **Dual-Mode Data Entry:** Optimized for both real-time individual entries and high-speed batch transcription.
* **Keyboard Navigation:** Technicians can navigate through forms purely using the keyboard.
* **Destructive Action Guards:** Any destructive admin action triggers a clear confirmation prompt before execution.

---

### 6. Success Metrics
1. **100% Digital Capture:** Zero unrecorded tests prior to printing.
2. **Zero System Freezes:** The application maintains a memory footprint below 150MB, running smoothly on legacy 2GB RAM workstations.
3. **Instantaneous Report Aggregation:** Compilation of aggregate reports in under 5 seconds.
4. **Complete Regulatory Traceability:** 100% of database-altering actions are captured in the immutable background audit ledger.
