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


