# AMH Lab Tracker - Best Practices

This document outlines the coding standards and design principles that all developers must adhere to when contributing to the AMH Lab Tracker.

## A. UI & Design Rules

1. **No Emojis:** Do not use emojis anywhere in the user interface, documentation, or codebase (including comments and commit messages).

2. **Icons:** Only use **Lucide icons**. Do not mix icon sets.
   **No Pill Tags or Badges:** Avoid using pill tags or badges. Use plain text to represent statuses and tags, as badges are rarely necessary and can clutter the interface.
   **Simplicity:** Prioritize a clean, function-driven design that favors maximum legibility and plain text over decorative elements.
   **Dropdown Selection for Consistency:** Prefer <select> dropdowns over free-text input for qualitative and semi-quantitative tests to ensure strict data validation and faster, error-free client result entry.

## B. General Guidelines

* *This document will be updated as the project evolves. Always refer back to this file for the latest coding and design standards.*

## C. Development Philosophy

1. **Terminology**: **Client vs Patient:** Always use the term **'Client'**, never 'Patient'. This generalizes testing to include routine checkups and non-pathological testing, as not everyone in the lab is suffering from an illness.

2. **Avoid Large Code Refactors**: Unless completely necessary and warranted, developers **must** avoid large code refactors.

3. **Small, Surgical Changes**: Always make small, targeted changes to implement new features, fix bugs, or modify an existing feature. Do not attempt a full rewrite of existing logic or UI components when a surgical insertion or removal will suffice



## D. Additional Core Rules

1. No toast notifications for anything in the app. Only use clean, uncluttered modals for success/error states and prompts.
2. **Frontend is an interaction layer only. It must not contain any business logic.**
   - All data validation, authorization checks, computation, and state mutation belong exclusively in backend API endpoints.
   - The frontend sends requests and renders responses. It never decides what is valid, who is allowed, or what the outcome should be.
   - If a frontend call returns an error, the error message originates from the backend. The frontend only presents it.
   - Any validation duplicated in the frontend (e.g., field presence checks before submission) is acceptable only as UX convenience, never as the authoritative gate. The backend is always the authoritative gate.
   - A 405 Method Not Allowed error means the server was not restarted after a new endpoint was added, or the route was not registered. Never work around this with client-side hacks. Restart the server and confirm the endpoint is registered.
3. **Multi-Parameter Test Reports on Dedicated Single Pages**:
   - Diagnostic tests with multiple sub-parameters (currently **Complete Blood Count (CBC)** and **Urinalysis**) must always render on their own dedicated, isolated page in generated PDF reports.
   - They must never share a page or overlap with general single-parameter lab tests.
   - All rows, sections, metadata, and signatures for a multi-parameter test must strictly fit within that single page (A4) without spilling over onto a second page. Vertical padding, table padding, row heights, and font sizes must be tuned to guarantee single-page containment across all client records.

## E. Surveillance & Incidence Tracking Standards

**Target Finding vs Binary Positive:** The concept of "Positive" applies strictly to binary infectious assays (e.g., HIV, Malaria, HBsAg). For composite panels and quantitative assays, the tracked event represents a specific **Target Clinical Finding** (e.g., Severe Anemia for CBC, Pathological Abnormality for Urinalysis, Parasites Detected for Stool, Diabetic Range for Blood Sugar).

##### **Default Tracking Rules:**

1. **Qualitative & Semi-Quantitative Tests:** `is_tracked = 1` by default. Any non-negative/non-normal outcome is counted as a tracked finding.

2. **Quantitative Panels (RFTs, LFTs, Electrolytes):** `is_tracked = 0` by default (standard tests done count only), unless a specific surveillance metric (such as FBS/RBS diabetic range or CBC severe anemia) is explicitly configured.

3. **Automated Daily Surveillance Ledger (Read-Only):** Technicians log individual test results on the Lab Reports / Workbench interface, which automatically tallies `done` counts and `positive/finding` counts in real-time. The Daily Log is a live, automated surveillance summary ledger (Read-Only) displaying calculated totals and positivity rates rather than an editable manual entry grid. Manual typing inputs and save buttons must not be used on the Daily Log table.


## F. Offline Distribution & Deployment Policy

AMH Lab Tracker is designed to run even on airgapped workstations in a hospital setting. The following rules govern how the project is packaged and distributed.

1. **Commit offline wheels and packages to git.** The `offline_packages/wheels/` directory contains pre-downloaded Python dependency wheels (targeting Python 3.11 & 3.14 Windows). These **must be committed to the repository** and must never be added to `.gitignore`. Pushing wheels to the remote makes it easy to clone the repo onto a USB drive or new workstation and run `setup.bat` without any internet access.

2. **Commit release ZIP archives when produced.** Packaged release ZIPs (output of `pack_release.py`) may also be committed because they are the primary distribution artifact for a given release. Do not blanket-ignore `*.zip`.

3. **The owner controls `.gitignore`.** Do not modify `.gitignore` without explicit instruction from the repository owner.

4. **`setup.bat` is the single entry point for new installations.** It installs dependencies from local wheels, seeds the database, and creates the desktop shortcut — all without touching the internet. Keep it working and well-tested.

## G. Frontend & Browser Engine Compatibility (Strict ES6 Baseline)

The system is deployed to low-spec clinical workstations in Uganda that frequently run **Legacy Microsoft Edge (EdgeHTML 12–18 / early Windows 10 & Windows 7 LTSB)**. All frontend code must strictly adhere to the following rules:

1. **Zero Node.js / Zero Build Tools:** The frontend is strictly Vanilla JS and CSS. No Webpack, Vite, Babel, or npm build steps are permitted in development or production.
2. **Prohibited JavaScript Syntax (ES2017+):**
   - **`async` / `await`:** Prohibited. Legacy Edge (Edge 12–14) throws `SCRIPT1009: Expected '}'` at parse time. Use native ES6 generator-to-promise coroutines (`__async(function*() { ... yield ... })`) or standard Promises (`.then()`).
   - **Optional Chaining (`?.`):** Prohibited (ES2020). Throws `SCRIPT1002: Syntax error` in Edge 12–18. Use explicit guard checks (`el ? el.value : null`).
   - **Nullish Coalescing (`??`):** Prohibited (ES2020). Use standard boolean fallback (`||` with explicit null checks).
   - **Regex Lookbehinds (`(?<=...)`) & Named Captures:** Prohibited (ES2018). Use standard capturing groups and submatch extraction.
3. **Defensive Polyfills:** Core Array and Object helper methods (`Array.prototype.includes`, `Array.prototype.find`, `Object.values`, `Object.entries`) must be polyfilled at the top of `app.js` to ensure stability on Edge 12/13.
4. **HTML Inline SVG Tags:** Inline SVGs in HTML templates must explicitly close all child elements (e.g. `<path ...></path>`, `<rect ...></rect>`, `<line ...></line>`) rather than using self-closing slashes (`<path .../>`) to prevent `HTML1500` parser warnings in Microsoft Edge/IE.
