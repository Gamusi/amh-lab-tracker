# Functional Specification Document (FSD)
## M-LIS — Screens, Workflows & Edge Cases
**Laboratory Information System**

---

### 1. Navigation & Application Shell (Top Navigation Bar)

To maximize vertical and horizontal screen real estate on legacy monitors and support the "simplicity that works" design philosophy, **M-LIS** utilizes a flat, persistent **Top Navigation Bar**.

#### 1.1 Layout & Behavior Rules
*   **Header Section**: 
    *   **Fixed Height**: Persistent across all views to eliminate visual jumping.
    *   **Brand Integrations**: Configurable facility logo and title on the far left.
    *   **Navigation Links**: Centered, high-contrast text tabs. Active tabs are marked clearly.
    *   **User & Session Status**: Positioned on the far right. Displays the logged-in user's full name, role, a countdown timer showing seconds remaining before auto-logout (15 minutes), and a Logout button.
*   **Active Screen Container**: Takes up 100% of the remaining viewport height. Uses native browser scrolling.
*   **CSS-Based Theme Integration**: The layout uses browser-native media queries to match system preferences (`prefers-color-scheme`). No manual theme toggles are rendered to save memory.

---

### 2. Client Management & Registration Workflows

The system utilizes Domain-Driven Design, referring to subjects as **"Clients"**. Clients are registered once and can have multiple subsequent test orders.

#### 2.1 Sequential Lab Numbers & Monthly Lifecycle
The system utilizes a highly structured, sequential **Lab Number** format instead of random database identifiers.
*   **Syntax**: `[FACILITY_ACRONYM]-[YY]-[MM]-[SEQUENTIAL_NUMBER]` (e.g., `AMH-26-8-001` or `MLIS-26-8-001`).
*   **Monthly Reset**: The sequence automatically resets to `001` at `00:00:00` on the first day of each calendar month via a backend database trigger.
*   **Intraday Reuse**: If a client receives multiple separate tests on the same calendar day, the system reuses the same Lab Number for consolidated reporting.

#### 2.2 Screen 1: Client Directory
*   **The Directory Table**: Lists registered clients with their Client ID, Full Name, Sex, Date of Birth, and Contact Number.
*   **Active Directory Search**: Searching triggers an asynchronous request with a 150ms debounce window.

#### 2.3 Single-Screen Quick Registration (Modal Workflow)
To support high-throughput clinical queues, the registration form is hosted as a **pop-up Modal** rather than a dedicated page or side panel.
*   **Smart Client Autocomplete**: As the technician types a name into the "Client Name" field, the frontend issues a debounced request to suggest historical clients. Clicking a suggestion auto-populates the form. **Crucially**, selecting a historical client generates a brand-new sequential Lab Number for the current run to keep the daily ledger perfectly aligned.
*   **Dynamic DOB & Age Calculator**: Techs can enter a Date of Birth OR type the client's current age. If Age is entered, the backend calculates a mock birth date (e.g., July 1st of the calculated year) to satisfy schema consistency.

---

### 3. Screen 2: Test Result Entry Workbench

This is the technician's primary workbench. A test cannot be run or printed without first logging the client and result in the system.

#### 3.1 Dynamic Laboratory Department Selection
*   **Department Dropdown**: Groups tests by sections (e.g., Parasitology, Hematology).
*   **Test Selection**: Selecting a test and clicking `[Add]` generates the required backend rows and mounts the input fields.

#### 3.2 High-Throughput Keyboard Data Entry
To facilitate rapid batch-entry, fields are optimized for mouse-free transcription:
*   **Vertical Tab Navigation**: Pressing `Tab` or `Enter` moves the browser focus vertically down to the next parameter.
*   **Data Sanitization**: Inputs are bound to a strict numeric filter. Alphabetical keys trigger a subtle **red border glow** without disruptive pop-ups.
*   **Automated Analyzer Clipboard Portal**: For tests run on automated equipment (e.g., Hematology Analyzers), a generic text area allows technicians to paste raw data strings (SQL/HL7). A backend RegEx engine instantly extracts values (WBC, RBC, etc.) and auto-populates the fields, avoiding manual transcription fatigue and preventing vendor lock-in.

#### 3.3 Non-Blocking Clinical Alerts
As values are entered, the backend calculates clean, color-coded indicators inside the table without using disruptive blocking modals:
*   `[!] High` (Orange): Exceeds upper limits.
*   `[!] Low` (Blue): Falls below lower limits.
*   `[!!] Critical` (Red icon): Falls into extreme, life-threatening limits.

---

### 4. Screen 3: Test Verification and Release

To comply with ISO 15189 (verification prior to release), entering a result does not authorize it for printing.

#### 4.1 Granular Verification Rights
*   Administrators can selectively assign a boolean flag `has_verification_rights` to specific trusted staff members. Only users with this permission can access the Verification queue.

#### 4.2 Interactive Verification
*   **Audit Diff Insight**: The Verification Panel dynamically renders the audit log history for that specific test run, displaying a warning if a value was edited after its initial entry.
*   **Click-to-Sign**: Clicking `[Approve and Sign Report]` writes the verifier’s unique ID into the database.
*   **Unlocking the PDF**: The Official Report cannot be printed or generated until this digital signature is complete.

---

### 5. Role-Based Editing and Correction Workflows

#### 5.1 The "Trusted Technician" Model
The system uses a granular boolean flag: `can_edit_results`.
*   **Standard Staff**: Once results are submitted, fields become read-only. Modifications require an administrator or trusted technician.
*   **Trusted Staff**: Users granted the `can_edit_results` flag can click `[Edit Results]` to unlock fields and correct typos in real-time.
*   **Audit Trail**: Every modification is caught by the backend and logged in the immutable `audit_log` table (recording user ID, timestamp, old value, and new value).

---

### 6. Screen 4: Test Menu Configuration (Admin)

Administrators have access to a full Test Configuration Panel to adapt to changing clinical offerings.
*   **Full CRUD**: Create, read, and update test definitions and parameters.
*   **Soft-Deletion**: If a test is disabled, it is marked as `is_active = 0`. It disappears from the ordering list but remains permanently in the database to preserve historical relationships.
*   **Incidence Tracking**: Tests can be flagged to track positives (e.g., Malaria, HIV). Positive results are automatically appended to the Monthly Epidemic Report.

---

### 7. Screen 5: Reports & Epidemic Tracking

Generates administrative reports and public health summaries.
*   **Filtering**: Supports custom date ranges and standard presets (Daily, Monthly, Ugandan Financial Year).
*   **Export Options**: Reports can be exported as raw CSVs for MoH compliance or as text-selectable Vector PDFs (ReportLab intended final state).

---

### 8. Automated Database Backup & Restoration *(Intended State)*

To safeguard clinical data without relying on manual intervention, the system will implement an automated background service:
1.  **6-Hour Daemon**: A lightweight scheduler will automatically copy the database to a user-configured local folder every 6 hours of continuous runtime.
2.  **Safety Checks**: Backups will only execute if `PRAGMA integrity_check` passes.
3.  **UI-Based Restoration**: Administrators will be able to restore corrupted databases directly from the UI. The backend will verify the backup schema before safely overwriting the active file.
