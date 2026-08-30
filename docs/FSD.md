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

#### 3.2 High-Throughput Keyboard Data Entry & Analyzer Portal
To facilitate rapid batch-entry, fields are optimized for mouse-free transcription:
*   **Vertical Tab Navigation**: Pressing `Tab` or `Enter` moves the browser focus vertically down to the next parameter.
*   **Data Sanitization**: Inputs are bound to strict numeric filters with biochemical validator ranges. Alphabetical keys on numeric fields trigger a subtle red border indicator without disruptive pop-ups.
*   **Automated Analyzer Clipboard Portal (Nihon Kohden MEK-6500K)**: For automated CBC panels, technicians click `[Import Analyzer Data]` and paste the raw text dump. A dedicated backend RegEx engine (`backend/app/parsers/nihon_kohden.py`) instantly extracts all 18 parameters (WBC, RBC, HGB, HCT, MCV, MCH, MCHC, PLT, differentials) and auto-populates the input fields.

#### 3.3 Non-Blocking Clinical Alerts
As values are entered, the system dynamically renders high-contrast indicators directly within the results view:
*   `[!] High` (Orange): Exceeds upper reference limits.
*   `[!] Low` (Blue): Falls below lower reference limits.
*   `[!!] Critical` (Red icon): Falls into life-threatening threshold bounds.

---

### 4. Screen 3: Test Verification and Release

To comply with ISO 15189 (verification prior to release), entering a result does not authorize it for printing.

#### 4.1 Granular Verification Rights
*   Administrators can selectively assign the `has_verification_rights` permission to trusted clinical staff. Only authorized users can access the Verification queue.

#### 4.2 Interactive Verification & Digital Signature
*   **Audit Diff Insight**: The Verification Panel dynamically renders the audit log history for that specific test run, highlighting if a value was modified after initial entry.
*   **Click-to-Sign**: Clicking `[Approve and Sign Report]` writes the verifier’s unique user ID and timestamp to the record.
*   **Unlocking the PDF**: The official vector PDF cannot be generated or printed until digital verification is complete.

---

### 5. Screen 4: Test Menu Configuration (Admin)

Administrators have access to a full Test Configuration Panel to adapt to changing clinical offerings:
*   **Full CRUD**: Create, read, and update test definitions, units of measurement, reference ranges, and critical limits.
*   **Soft-Deletion**: If a test is disabled, it is marked as `is_active = 0`. It disappears from the ordering list but remains permanently in the database to preserve historical relationships.
*   **Incidence Tracking**: Tests can be flagged to track positivity rates (e.g., Malaria RDT, HIV 1/2). Positives automatically increment HMIS 105 Section 6 surveillance totals.

---

### 6. Screen 5: Reagents & Consumables Inventory Management

Technicians and administrators monitor stock levels, expiration dates, and consumption:
*   **Kits Summary Table**: Real-time view of available units, minimum buffer thresholds, and active batch lots.
*   **FIFO Lot Registry**: First-In, First-Out lot tracking displaying Lot Number, Expiry Date, Remaining Units, and status badges (`In Stock`, `Low Stock`, `Near Expiry`, `Expired`, `Depleted`).
*   **Receive Stock Modal**: One-click modal to register newly received kits, specify lot numbers, and set expiry dates.
*   **Wastage & QC Consumption**: Dedicated logging interface to record damaged kits, expired lot write-offs, and quality control usage with mandatory reason notes.

---

### 7. Screen 6: Reports & Epidemic Tracking

Generates administrative reports, surveillance aggregations, and official client softcopies:
*   **Multi-Period Filtering**: Supports custom date ranges and standard presets (Daily, Weekly, Monthly, Ugandan Financial Year).
*   **Uganda HMIS 105 Section 6 Surveillance**: Automated roll-up of positive/negative diagnostic counts for public health reporting.
*   **Export Options**:
    *   **Raw CSV Export**: Client demographic and ledger exports for offline spreadsheet analysis.
    *   **ISO 15189 Vector PDF**: Text-selectable, official diagnostic report slips generated via ReportLab with dual identifiers, 2-column CBC layout, and digital signatures.

---

### 8. Future Roadmap

1.  **Automated Database Backup Daemon**: 6-hour background scheduler to automatically snapshot `data/mlis.db` to configured backup directories after `PRAGMA integrity_check` validation.
2.  **Printable MoH Register Sheet Layout**: Formatted multi-column grid mirroring the physical Uganda Ministry of Health Health Unit Laboratory Register book.
