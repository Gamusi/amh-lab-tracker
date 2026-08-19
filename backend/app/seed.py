import os, datetime, sqlite3
from .database import get_connection, init_db
import json

def seed_database():
    print("Initializing database schema...")
    init_db()
    
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Sections
    sections = [
        "Hematology & Coagulation", 
        "Serology & Clinical Immunology", 
        "Clinical Biochemistry", 
        "Parasitology & Stool Diagnostics", 
        "Microbiology", 
        "Blood Transfusion & Immunohematology"
    ]
    sec_map = {}
    for idx, name in enumerate(sections, 1):
        cur.execute("SELECT id FROM sections WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO sections (name, sort_order) VALUES (?, ?)", (name, idx))
            sec_id = cur.lastrowid
        else:
            sec_id = row["id"]
        sec_map[name] = sec_id
    
    conn.commit()

    # Wards
    wards = ["ANC", "MCH", "Emergency", "Theater", "Labour", "OPD", "IPD", "Pediatrics", "TB Clinic"]
    for w_name in wards:
        cur.execute("INSERT OR IGNORE INTO wards (name) VALUES (?)", (w_name,))
    conn.commit()

    # 3. Test Catalog
    # Tuples: (name, section, is_tracked, result_type, default_unit, options_list)
    tests = [
        ("CBC", "Hematology & Coagulation", False, "quantitative", None, None),
        ("Hemoglobin", "Hematology & Coagulation", False, "quantitative", "g/dL", None),
        ("Blood Smear (Hemoparasites)", "Hematology & Coagulation", True, "qualitative", None, ["No hemoparasites seen", "Seen"]),
        
        ("Widal", "Serology & Clinical Immunology", True, "semi_quantitative", None, None),
        ("VDRL/RPR", "Serology & Clinical Immunology", True, "qualitative", None, ["Reactive", "Non-Reactive"]),
        ("MRDT", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative", "Invalid"]),
        ("Determine", "Serology & Clinical Immunology", True, "qualitative", None, ["Reactive", "Non-Reactive", "Invalid"]),
        ("STAT-PAK", "Serology & Clinical Immunology", True, "qualitative", None, ["Reactive", "Non-Reactive", "Invalid"]),
        ("SD-Bioline", "Serology & Clinical Immunology", True, "qualitative", None, ["Reactive", "Non-Reactive", "Invalid"]),
        ("HTS", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative"]),
        ("Hepatitis B surface Antigen", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative", "Invalid"]),
        ("Brucella Agglutination Test", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative"]),
        ("H. pylori Antigen", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative", "Invalid"]),
        ("H. pylori Antibody", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative", "Invalid"]),
        ("Rheumatoid Factor", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative"]),
        ("HCG Urine", "Serology & Clinical Immunology", True, "qualitative", None, ["Positive", "Negative", "Invalid"]),
        
        ("Urinalysis", "Clinical Biochemistry", False, "semi_quantitative", None, None),
        ("LFTs", "Clinical Biochemistry", False, "quantitative", None, None),
        ("RFTs", "Clinical Biochemistry", False, "quantitative", None, None),
        ("Fasting Blood Sugar", "Clinical Biochemistry", False, "quantitative", "mg/dL", None),
        ("Random Blood Sugar", "Clinical Biochemistry", False, "quantitative", "mg/dL", None),
        
        ("Blood smear for Malaria Parasites", "Parasitology & Stool Diagnostics", True, "qualitative", None, ["No malaria parasites seen", "+", "++", "+++", "++++"]),
        ("Stool Analysis", "Parasitology & Stool Diagnostics", False, "qualitative", None, None),
        
        ("ZN Staining", "Microbiology", False, "qualitative", None, ["Negative", "Positive"]),
        ("Gram Staining", "Microbiology", False, "qualitative", None, ["Negative", "Positive"]),
        ("Culture & Sensitivity", "Microbiology", False, "qualitative", None, ["No growth", "Growth"]),
        
        ("Blood Grouping", "Blood Transfusion & Immunohematology", False, "qualitative", None, ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]),
        ("Cross-matching", "Blood Transfusion & Immunohematology", False, "qualitative", None, ["Compatible", "Incompatible"])
    ]

    test_count = 0
    test_obj_map = {}
    for t_name, sec_name, is_tracked, result_type, default_unit, options in tests:
        sec_id = sec_map[sec_name]
        cur.execute("SELECT id FROM tests WHERE name = ? AND section_id = ?", (t_name, sec_id))
        r = cur.fetchone()
        options_json = json.dumps(options) if options else None
        
        if not r:
            cur.execute(
                "INSERT INTO tests (name, section_id, is_tracked, sort_order, result_type, default_unit, options) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (t_name, sec_id, 1 if is_tracked else 0, 0, result_type, default_unit, options_json)
            )
            tid = cur.lastrowid
        else:
            tid = r["id"]
            cur.execute(
                "UPDATE tests SET result_type = ?, default_unit = ?, options = ? WHERE id = ?",
                (result_type, default_unit, options_json, tid)
            )
        test_obj_map[t_name.lower()] = tid
        test_count += 1

    conn.commit()

    # Link HIV Rapid Test Algorithm Rollup IDs (Determine, STAT-PAK, SD-Bioline -> HTS)
    hts_id = test_obj_map.get("hts")
    if hts_id:
        for kit_name in ["determine", "stat-pak", "sd-bioline"]:
            kit_id = test_obj_map.get(kit_name)
            if kit_id:
                cur.execute("UPDATE tests SET parent_rollup_id = ? WHERE id = ?", (hts_id, kit_id))

    # Seed Multi-Parameter Test Panels
    panel_definitions = {
        "cbc": [
            ("Hemoglobin (Hb)", "g/dL", "12.0 - 16.0", 1),
            ("White Blood Cells (WBC)", "x10^9/L", "4.0 - 10.0", 2),
            ("Red Blood Cells (RBC)", "x10^12/L", "3.8 - 5.5", 3),
            ("Platelets (PLT)", "x10^9/L", "150 - 450", 4),
            ("Hematocrit (HCT)", "%", "36.0 - 48.0", 5)
        ],
        "lfts": [
            ("ALT (SGPT)", "U/L", "7 - 56", 1),
            ("AST (SGOT)", "U/L", "10 - 40", 2),
            ("Alkaline Phosphatase (ALP)", "U/L", "44 - 147", 3),
            ("Total Bilirubin", "mg/dL", "0.1 - 1.2", 4)
        ],
        "rfts": [
            ("Serum Urea", "mmol/L", "2.5 - 7.8", 1),
            ("Serum Creatinine", "µmol/L", "62 - 115", 2),
            ("Sodium (Na+)", "mmol/L", "135 - 145", 3),
            ("Potassium (K+)", "mmol/L", "3.5 - 5.1", 4)
        ]
    }

    for t_k, params in panel_definitions.items():
        tid = test_obj_map.get(t_k)
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
