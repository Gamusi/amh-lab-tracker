### Task 5: Tailored Result Modals & Toast Removal
**Files:**
- Modify: rontend/static/index.html
- Modify: rontend/static/js/app.js

- [ ] **Step 1: Generic Modal for Notifications**
In index.html, add a #notification-modal. 
In pp.js, replace all usages of 	his.showToast(...) with 	his.showNotificationModal(title, message, type). Completely remove showToast logic.

- [ ] **Step 2: Tailored Result Entry Modals**
Update #result-entry-modal in index.html and showEnterResultModal in pp.js.
Instead of the generic esult_value input and the is_positive prompt, we need specialized inputs based on the test type.
The frontend should parse the test name (from 	estCatalog) to determine the type:
1. **Urinalysis**: Render a form with Appearance, Color, Specific Gravity, pH, Proteins, Glucose, Bilirubin, Urobilinogen, Ketones, Blood, Nitrites, Leukocytes, Pus Cells, RBCs, Epithelial Cells, Casts & Crystals.
2. **Widal**: Render a dropdown (Positive/Negative). If Positive, show an optional text input for Titers.
3. **Qualitative (HIV, Malaria, VDRL, H. pylori, etc.)**: Render a dropdown (Positive/Negative or Reactive/Non-Reactive or No malaria parasites seen).
4. **Quantitative (Numeric)**: Render a numeric input for value + dropdown for Unit (defaulting to the test's SI unit).

For the backend payload, just concatenate the values in a standard format or send as esult_value. Remember, the backend doesn't expect is_positive anymore, so the frontend just sends esult_value.

- [ ] **Step 3: Editing Visits**
In pp.js, in the "Pending Tests" or "Historical Reports" view (if not dispatched), add an "Add Test to Visit" button that opens a modal to select tests and hits the POST /api/visits/{visit_id}/orders endpoint.

- [ ] **Step 4: Verify & Commit**
Commit changes.
