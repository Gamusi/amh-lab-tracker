import os, datetime, sqlite3
from .database import get_connection, init_db
from .auth import hash_password

def seed_database():
    print("Initializing database schema...")
    init_db()
    
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()



    # 2. Sections
    sections = ["Main", "Referrals", "Out-Reaches", "Self-Request"]
    sec_map = {}
    for idx, name in enumerate(sections, 1):
        cur.execute("SELECT id FROM sections WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO sections (name, sort_order) VALUES (?, ?)", (name, idx))
            sec_id = cur.lastrowid
        else:
            sec_id = row["id"]
        sec_map[name.lower()] = sec_id
    
    conn.commit()

    # 3. Test Catalog
    tracked_tests = {
        "sickle cell test", "widal", "vdrl/rpr", "hts", "determine", "stat-pak", "sd-bioline",
        "hepatitis b surface antigen", "brucella agglutination test", "mrdt",
        "h. pylori antigen", "h. pylori antibody", "hcg", "rheumatoid factor",
        "blood smear (hemoparasites)", "blood smear (malaria)", "self test"
    }

    default_tests = {
        "main": [
            ("Hemoglobin", False), ("CBC", False), ("ABO Blood Grouping", False), ("Sickle Cell Test", True),
            ("ESR", False), ("Blood Smear (Hemoparasites)", True), ("Stool Analysis", False), ("Widal", True),
            ("VDRL/RPR", True), ("HTS", True), ("Determine", True), ("STAT-PAK", True), ("SD-Bioline", True),
            ("Hepatitis B surface Antigen", True), ("Brucella Agglutination Test", True), ("MRDT", True),
            ("H. pylori Antigen", True), ("H. pylori Antibody", True), ("Rheumatoid Factor", True), ("HCG", True),
            ("PSA", False), ("EID", False), ("Viral Load", False), ("Fasting Blood Sugar", False),
            ("Random Blood Sugar", False), ("Gram Staining", False), ("ZN Staining", False), ("CSF Analysis", False),
            ("Urinalysis", False), ("LFTs", False), ("RFTs", False), ("CD4", False), ("CRAG", False),
            ("LAM", False), ("Lipids", False)
        ],
        "referrals": [
            ("Alpha-Feto Protein", False), ("Thyroid Function Tests", False), ("Uric Acid", False),
            ("Hb Electrophoresis", False), ("Serum HCG", False), ("FSH", False), ("LH", False),
            ("Hepatitis Be Antigen", False), ("Lipase", False), ("HbA1c", False)
        ],
        "out-reaches": [
            ("MRDT", True), ("Determine", True), ("STAT-PAK", True), ("SD-Bioline", True),
            ("Hepatitis B surface Antigen", True), ("ZN Staining", False)
        ],
        "self-request": [
            ("Self Test", True), ("Blood Smear (Malaria)", True)
        ]
    }

    test_count = 0
    test_obj_map = {}
    for sec_key, t_list in default_tests.items():
        sec_id = sec_map[sec_key]
        for sort_i, (t_name, default_tracked) in enumerate(t_list, 1):
            cur.execute("SELECT id FROM tests WHERE name = ? AND section_id = ?", (t_name, sec_id))
            r = cur.fetchone()
            if not r:
                is_tr = (t_name.lower() in tracked_tests) or default_tracked
                cur.execute(
                    "INSERT INTO tests (name, section_id, is_tracked, sort_order) VALUES (?, ?, ?, ?)",
                    (t_name, sec_id, 1 if is_tr else 0, sort_i)
                )
                tid = cur.lastrowid
            else:
                tid = r["id"]
            test_obj_map[(sec_key, t_name.lower())] = tid
            test_count += 1

    conn.commit()

    # Link HIV Rapid Test Algorithm Rollup IDs (Determine, STAT-PAK, SD-Bioline -> HTS)
    for sec_k in ["main", "out-reaches"]:
        hts_id = test_obj_map.get((sec_k, "hts"))
        if hts_id:
            for kit_name in ["determine", "stat-pak", "sd-bioline"]:
                kit_id = test_obj_map.get((sec_k, kit_name))
                if kit_id:
                    cur.execute("UPDATE tests SET parent_rollup_id = ? WHERE id = ?", (hts_id, kit_id))

    # Seed Multi-Parameter Test Panels
    panel_definitions = {
        ("main", "cbc"): [
            ("Hemoglobin (Hb)", "g/dL", "12.0 - 16.0", 1),
            ("White Blood Cells (WBC)", "x10^9/L", "4.0 - 10.0", 2),
            ("Red Blood Cells (RBC)", "x10^12/L", "3.8 - 5.5", 3),
            ("Platelets (PLT)", "x10^9/L", "150 - 450", 4),
            ("Hematocrit (HCT)", "%", "36.0 - 48.0", 5)
        ],
        ("main", "lfts"): [
            ("ALT (SGPT)", "U/L", "7 - 56", 1),
            ("AST (SGOT)", "U/L", "10 - 40", 2),
            ("Alkaline Phosphatase (ALP)", "U/L", "44 - 147", 3),
            ("Total Bilirubin", "mg/dL", "0.1 - 1.2", 4)
        ],
        ("main", "rfts"): [
            ("Serum Urea", "mmol/L", "2.5 - 7.8", 1),
            ("Serum Creatinine", "µmol/L", "62 - 115", 2),
            ("Sodium (Na+)", "mmol/L", "135 - 145", 3),
            ("Potassium (K+)", "mmol/L", "3.5 - 5.1", 4)
        ]
    }

    for (sec_k, t_k), params in panel_definitions.items():
        tid = test_obj_map.get((sec_k, t_k))
        if tid:
            for pname, unit, ref_range, s_order in params:
                cur.execute("SELECT id FROM test_parameters WHERE test_id = ? AND parameter_name = ?", (tid, pname))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO test_parameters (test_id, parameter_name, unit, ref_range, sort_order)
                        VALUES (?, ?, ?, ?, ?)
                    """, (tid, pname, unit, ref_range, s_order))

    conn.commit()
    cur.execute("SELECT id FROM users LIMIT 1")
    user_row = cur.fetchone()
    admin_id = user_row["id"] if user_row else None

    # Audit Log
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
        (admin_id, "seed_database", f"Database seeded with {len(sec_map)} sections and {test_count} tests.")
    )
    conn.commit()
    conn.close()

    print(f"Seeding completed: {len(sec_map)} sections, {test_count} tests.")

if __name__ == "__main__":
    seed_database()
