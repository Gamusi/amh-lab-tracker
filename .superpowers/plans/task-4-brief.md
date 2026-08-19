### Task 4: Frontend "Create Visit" UX & Config Tab
**Files:**
- Modify: rontend/static/index.html
- Modify: rontend/static/js/app.js

- [ ] **Step 1: Update Visit UI (app.js)**
In rontend/static/js/app.js, inside selectClient():
1. Change "Select Tests..." text to "Select Test(s):".
2. Add a search input above the checkboxes for tests:
`html
<input type="text" id="visit-test-search" placeholder="Search tests..." onkeyup="app.filterVisitTests()" style="width: 100%; padding: 8px; margin-bottom: 8px;">
`
3. Update loadTestOptionsMulti() to populate the isit-tests-container. Ensure each checkbox row has a CSS class isit-test-row and includes a data-name attribute containing the lowercase test name for filtering.
4. Implement ilterVisitTests():
`javascript
  filterVisitTests() {
    const query = document.getElementById('visit-test-search').value.toLowerCase();
    const rows = document.querySelectorAll('.visit-test-row');
    rows.forEach(row => {
      if (row.getAttribute('data-name').includes(query)) {
        row.style.display = 'block';
      } else {
        row.style.display = 'none';
      }
    });
  }
`

- [ ] **Step 2: Update Wards UI (app.js)**
In rontend/static/js/app.js, update loadWards() or similar function to fetch wards from /api/config/wards.
Update selectClient() to populate the "Ward of origin" dropdown with the fetched wards.

- [ ] **Step 3: Update Config Tab**
In rontend/static/js/app.js, inside enderConfig():
Make the "Test Catalog", "Pending Users", and "Active Users" cards collapsible using <details> and <summary> tags.
Add two more collapsible cards: "Clinicians Configuration" and "Wards Configuration".
Implement loadCliniciansConfig() and loadWardsConfig() to fetch and display editable/deletable tables for Clinicians and Wards.

- [ ] **Step 4: Verify & Commit**
Commit changes.
