import sqlite3
import json
from .database import get_connection, init_db

# Auto-generated from amh-comprehensive-test-reporting-specifications.md
SECTIONS = ['Hematology', 'Serology & Clinical Immunology', 'Clinical Biochemistry', 'Urinalysis Profile', 'Parasitology & Stool Diagnostics', 'Microbiology & Tuberculosis', 'Blood Transfusion & Immunohematology']

PANELS = {'Complete Blood Count (CBC)': ['Total WBC Count (White Blood Cells)', 'Red Blood Cells (RBC)', 'Hemoglobin (Hb)', 'Hematocrit (HCT)', 'Mean Cell Volume (MCV)', 'Mean Cell Hb (MCH)', 'Mean Cell Hb Conc (MCHC)', 'Platelets Count (PLT)', 'Neutrophils (%) [Relative Count]', 'Lymphocytes (%) [Relative Count]', 'Monocytes (%) [Relative Count]', 'Eosinophils (%) [Relative Count]', 'Basophils (%) [Relative Count]', 'Neutrophils (Absolute Count)', 'Lymphocytes (Absolute Count)', 'Monocytes (Absolute Count)', 'Eosinophils (Absolute Count)', 'Basophils (Absolute Count)', 'RBC Distribution Width (RDW)', 'Thrombocrit (PCT)', 'Mean Platelet Volume (MPV)', 'PLT Distribution Width (PDW)'], 'LFTS': ['ALT / SGPT (Alanine Aminotransferase)', 'AST / SGOT (Aspartate Aminotransferase)', 'Alkaline Phosphatase (ALP)', 'Total Bilirubin', 'Direct Bilirubin', 'Total Protein', 'Serum Albumin', 'Gamma-Glutamyl Transferase (GGT)', 'Total Cholesterol'], 'RFTS': ['Serum Urea', 'Serum Creatinine', 'Serum Uric Acid'], 'CARDIAC': ['Troponin I (cTnI)', 'Troponin T (cTnT)', 'CK-MB (Creatine Kinase-MB)', 'BNP / NT-proBNP', 'D-Dimer', 'LDH (Lactate Dehydrogenase)'], 'ELECTROLYTES': ['Serum Potassium (K+)', 'Serum Sodium (Na+)', 'Serum Chloride (Cl-)', 'Bicarbonate (HCO3-)'], 'URINALYSIS': ['Color', 'Turbidity', 'Pus Cells (WBCs)', 'Red Blood Cells (RBCs)', 'Epithelial Cells', 'Casts', 'Crystals', 'Specific Gravity (S.G)', 'PH', 'Proteins (Albuminuria Screening)', 'Glucose (Glucosuria Screening)', 'Bilirubin (Bilirubinuria)', 'Urobilinogen', 'Ketones (Ketonuria)', 'Blood (Hematuria/Hemoglobinuria)', 'Nitrates (Nitrite Screening)', 'Leukocytes (Leukocyte Esterase)'], 'STOOL ANALYSIS': ['Stool Analysis (Macroscopy)', 'Stool Analysis (Microscopy)', 'Stool Occult Blood'], 'HIV Testing Service': ['Determine', 'Stat-Pak', 'SD Bioline']}

TESTS = [
    {'name': 'Complete Blood Count (CBC)', 'section': 'Hematology', 'is_tracked': 1, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'LFTS', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'RFTS', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'CARDIAC', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'ELECTROLYTES', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'URINALYSIS', 'section': 'Urinalysis Profile', 'is_tracked': 1, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'STOOL ANALYSIS', 'section': 'Parasitology & Stool Diagnostics', 'is_tracked': 1, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'HIV Testing Service', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'panel', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'E.S.R (Erythrocyte Sedimentation Rate)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mm/hour', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'Aptt (Activated Partial Thromboplastin Time)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'Seconds', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'Prothrombin Time (PT)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'Seconds', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'International Normalized Ratio (INR)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'Calculated ratio', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'Bleeding Time (BT)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'Minutes', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'Clotting Time (CT)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'Minutes', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'Reticulocyte Count', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'Sickling Test (Sodium Metabisulfite)', 'section': 'Hematology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'WIDAL (Salmonella Typhi Agglutination)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Negative', 'Positive (TO 1:80, TH 1:80)', 'Positive (TO 1:160, TH 1:160)', 'Positive (TO 1:320, TH 1:320)'], 'parent_name': None, 'sort_order': 0},
    {'name': 'VDRL/RPR (Syphilis Screening)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Non-Reactive', 'Reactive (1:2)', 'Reactive (1:4)', 'Reactive (1:8)', 'Reactive (1:16)', 'Reactive (1:32)', 'Reactive (1:64)'], 'parent_name': None, 'sort_order': 0},
    {'name': 'HBsAg (Hepatitis B)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'BAT (Brucella Antigen Test)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Negative', 'Positive (1:80)', 'Positive (1:160)', 'Positive (1:320)'], 'parent_name': None, 'sort_order': 0},
    {'name': 'RF (Rheumatoid Factor)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'HCG Urine', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'HCG Blood', 'section': 'Serology & Clinical Immunology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mIU/mL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'H.Pylori Ag (Stool Antigen)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'H.Pylori Ab (Serum Antibody)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Malaria RDT', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'TB LAM (Urine Tuberculosis LAM)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'COVID19RDT', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'CD4 COUNT', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'quantitative', 'default_unit': 'cells/µL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'CrAg (Cryptococcal Antigen)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'HCV Ab (Hepatitis C)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'TPHA (Confirmatory Syphilis Test)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Reactive', 'Non-Reactive'], 'parent_name': None, 'sort_order': 0},
    {'name': 'ASO Titer (Anti-Streptolysin O)', 'section': 'Serology & Clinical Immunology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'IU/mL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'FBS (Fasting Blood Sugar)', 'section': 'Clinical Biochemistry', 'is_tracked': 1, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'RBS (Random Blood Sugar)', 'section': 'Clinical Biochemistry', 'is_tracked': 1, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': None, 'sort_order': 0},
    {'name': 'Blood smear Mps (Malaria Microscopy)', 'section': 'Parasitology & Stool Diagnostics', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['No malaria parasites seen', '1+', '2+', '3+', '4+'], 'parent_name': None, 'sort_order': 0},
    {'name': 'ZN FOR AFBs (Tuberculosis Sputum Smear)', 'section': 'Microbiology & Tuberculosis', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['AFB Negative', 'Scanty', '1+', '2+', '3+'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Gram Stain', 'section': 'Microbiology & Tuberculosis', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['No bacteria seen', 'Gram-positive cocci in pairs/chains', 'Gram-positive cocci in clusters', 'Gram-negative rods', 'Gram-negative intracellular diplococci', 'Gram-positive rods'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Urine Culture & Sensitivity (C&S)', 'section': 'Microbiology & Tuberculosis', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['No growth after 48 hours', 'Significant growth of E. coli', 'Significant growth of Klebsiella spp', 'Significant growth of S. aureus', 'Significant growth of Proteus spp'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Blood group (ABO & Rh typing)', 'section': 'Blood Transfusion & Immunohematology', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['A Rh(D) Positive', 'A Rh(D) Negative', 'B Rh(D) Positive', 'B Rh(D) Negative', 'AB Rh(D) Positive', 'AB Rh(D) Negative', 'O Rh(D) Positive', 'O Rh(D) Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Direct coombs (Direct Antiglobulin Test)', 'section': 'Blood Transfusion & Immunohematology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Indirect coombs (Antibody Screen)', 'section': 'Blood Transfusion & Immunohematology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Positive', 'Negative'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Compatibility Testing (Cross-matching)', 'section': 'Blood Transfusion & Immunohematology', 'is_tracked': 1, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Compatible', 'Incompatible'], 'parent_name': None, 'sort_order': 0},
    {'name': 'Total WBC Count (White Blood Cells)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10³/µL', 'secondary_unit': '10⁹/L', 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 1},
    {'name': 'Red Blood Cells (RBC)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10⁶/µL', 'secondary_unit': '10¹²/L', 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 2},
    {'name': 'Hemoglobin (Hb)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'g/dL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 3},
    {'name': 'Hematocrit (HCT)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 4},
    {'name': 'Mean Cell Volume (MCV)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'fL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 5},
    {'name': 'Mean Cell Hb (MCH)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'pg', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 6},
    {'name': 'Mean Cell Hb Conc (MCHC)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'g/dL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 7},
    {'name': 'Platelets Count (PLT)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10³/µL', 'secondary_unit': '10⁹/L', 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 8},
    {'name': 'Neutrophils (%) [Relative Count]', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 9},
    {'name': 'Lymphocytes (%) [Relative Count]', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 10},
    {'name': 'Monocytes (%) [Relative Count]', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 11},
    {'name': 'Eosinophils (%) [Relative Count]', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 12},
    {'name': 'Basophils (%) [Relative Count]', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 13},
    {'name': 'Neutrophils (Absolute Count)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10⁹/µL', 'secondary_unit': '10⁹/L', 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 14},
    {'name': 'Lymphocytes (Absolute Count)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10⁹/µL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 15},
    {'name': 'Monocytes (Absolute Count)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10⁹/µL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 16},
    {'name': 'Eosinophils (Absolute Count)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10⁹/µL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 17},
    {'name': 'Basophils (Absolute Count)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '10⁹/µL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 18},
    {'name': 'RBC Distribution Width (RDW)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 19},
    {'name': 'Thrombocrit (PCT)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 20},
    {'name': 'Mean Platelet Volume (MPV)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'fL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 21},
    {'name': 'PLT Distribution Width (PDW)', 'section': 'Hematology', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': '%', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'Complete Blood Count (CBC)', 'sort_order': 22},
    {'name': 'ALT / SGPT (Alanine Aminotransferase)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'U/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 1},
    {'name': 'AST / SGOT (Aspartate Aminotransferase)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'U/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 2},
    {'name': 'Alkaline Phosphatase (ALP)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'U/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 3},
    {'name': 'Total Bilirubin', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'µmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 4},
    {'name': 'Direct Bilirubin', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'µmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 5},
    {'name': 'Total Protein', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'g/dL', 'secondary_unit': 'g/L', 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 6},
    {'name': 'Serum Albumin', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'g/dL', 'secondary_unit': 'g/L', 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 7},
    {'name': 'Gamma-Glutamyl Transferase (GGT)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'U/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 8},
    {'name': 'Total Cholesterol', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'LFTS', 'sort_order': 9},
    {'name': 'Serum Urea', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'RFTS', 'sort_order': 1},
    {'name': 'Serum Creatinine', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'µmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'RFTS', 'sort_order': 2},
    {'name': 'Serum Uric Acid', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'µmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'RFTS', 'sort_order': 3},
    {'name': 'Troponin I (cTnI)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Negative', 'Positive'], 'parent_name': 'CARDIAC', 'sort_order': 1},
    {'name': 'Troponin T (cTnT)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Negative', 'Positive'], 'parent_name': 'CARDIAC', 'sort_order': 2},
    {'name': 'CK-MB (Creatine Kinase-MB)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'U/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'CARDIAC', 'sort_order': 3},
    {'name': 'BNP / NT-proBNP', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'pg/mL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'CARDIAC', 'sort_order': 4},
    {'name': 'D-Dimer', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'µg/mL', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'CARDIAC', 'sort_order': 5},
    {'name': 'LDH (Lactate Dehydrogenase)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'U/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'CARDIAC', 'sort_order': 6},
    {'name': 'Serum Potassium (K+)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'ELECTROLYTES', 'sort_order': 1},
    {'name': 'Serum Sodium (Na+)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'ELECTROLYTES', 'sort_order': 2},
    {'name': 'Serum Chloride (Cl-)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'ELECTROLYTES', 'sort_order': 3},
    {'name': 'Bicarbonate (HCO3-)', 'section': 'Clinical Biochemistry', 'is_tracked': 0, 'result_type': 'quantitative', 'default_unit': 'mmol/L', 'secondary_unit': None, 'ref_range': None, 'options': None, 'parent_name': 'ELECTROLYTES', 'sort_order': 4},
    # --- URINALYSIS: Macroscopy (sort_order 1-2) ---
    {'name': 'Color', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Straw', 'Yellow', 'Amber', 'Red', 'Brown'], 'parent_name': 'URINALYSIS', 'sort_order': 1},
    {'name': 'Turbidity', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Clear', 'Slightly Turbid', 'Turbid'], 'parent_name': 'URINALYSIS', 'sort_order': 2},
    # --- URINALYSIS: Microscopy / Sediment Cytology (sort_order 3-7) — all lpf ---
    {'name': 'Pus Cells (WBCs)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Not Seen', '1-2 / lpf', '3-4 / lpf', '5-10 / lpf', '10-15 / lpf', '>15 / lpf'], 'parent_name': 'URINALYSIS', 'sort_order': 3},
    {'name': 'Red Blood Cells (RBCs)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Not Seen', '1-2 / lpf', '3-5 / lpf', '5-10 / lpf', '>10 / lpf'], 'parent_name': 'URINALYSIS', 'sort_order': 4},
    {'name': 'Epithelial Cells', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Not Seen', 'Few', 'Moderate', 'Plenty'], 'parent_name': 'URINALYSIS', 'sort_order': 5},
    {'name': 'Casts', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Not Seen', 'Hyaline Casts (0-1 / lpf)', 'Granular Casts', 'Waxy Casts', 'RBC Casts', 'WBC Casts'], 'parent_name': 'URINALYSIS', 'sort_order': 6},
    {'name': 'Crystals', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Not Seen', 'Calcium Oxalate (++)', 'Triple Phosphate (++)', 'Uric Acid Crystals'], 'parent_name': 'URINALYSIS', 'sort_order': 7},
    # --- URINALYSIS: Dry Chemistry Dipstick — Siemens Multistix (sort_order 8-17) ---
    {'name': 'Specific Gravity (S.G)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['1.000', '1.005', '1.010', '1.015', '1.020', '1.025', '1.030'], 'parent_name': 'URINALYSIS', 'sort_order': 8},
    {'name': 'PH', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['5.0', '6.0', '6.5', '7.0', '7.5', '8.0', '8.5'], 'parent_name': 'URINALYSIS', 'sort_order': 9},
    {'name': 'Proteins (Albuminuria Screening)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Nil', 'Trace (15 mg/dL)', '1+ (30 mg/dL)', '2+ (100 mg/dL)', '3+ (300 mg/dL)', '4+ (\u22652000 mg/dL)'], 'parent_name': 'URINALYSIS', 'sort_order': 10},
    {'name': 'Glucose (Glucosuria Screening)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Nil', 'Trace (100 mg/dL)', '1+ (250 mg/dL)', '2+ (500 mg/dL)', '3+ (1000 mg/dL)', '4+ (\u22652000 mg/dL)'], 'parent_name': 'URINALYSIS', 'sort_order': 11},
    {'name': 'Bilirubin (Bilirubinuria)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Nil', 'Small (+)', 'Moderate (++)', 'Large (+++)'], 'parent_name': 'URINALYSIS', 'sort_order': 12},
    {'name': 'Urobilinogen', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Normal (1.0 EU/dL)', '2.0 EU/dL', '4.0 EU/dL', '8.0 EU/dL'], 'parent_name': 'URINALYSIS', 'sort_order': 13},
    {'name': 'Ketones (Ketonuria)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Nil', 'Trace (5 mg/dL)', '1+ (15 mg/dL)', '2+ (40 mg/dL)', '3+ (80 mg/dL)', '4+ (160 mg/dL)'], 'parent_name': 'URINALYSIS', 'sort_order': 14},
    {'name': 'Blood (Hematuria/Hemoglobinuria)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Nil', 'Non-Hemolyzed Trace', 'Hemolyzed Trace', '1+ (Small)', '2+ (Moderate)', '3+ (Large)'], 'parent_name': 'URINALYSIS', 'sort_order': 15},
    {'name': 'Nitrates (Nitrite Screening)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Negative', 'Positive'], 'parent_name': 'URINALYSIS', 'sort_order': 16},
    {'name': 'Leukocytes (Leukocyte Esterase)', 'section': 'Urinalysis Profile', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Nil', 'Trace', '1+ (Small)', '2+ (Moderate)', '3+ (Large)'], 'parent_name': 'URINALYSIS', 'sort_order': 17},
    {'name': 'Stool Analysis (Macroscopy)', 'section': 'Parasitology & Stool Diagnostics', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Formed, No blood/mucus', 'Semi-formed, No blood/mucus', 'Loose', 'Watery', 'Blood present', 'Mucus present', 'Blood and mucus present'], 'parent_name': 'STOOL ANALYSIS', 'sort_order': 1},
    {'name': 'Stool Analysis (Microscopy)', 'section': 'Parasitology & Stool Diagnostics', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['No ova, cysts, or trophozoites seen', 'E. histolytica cysts seen', 'E. histolytica trophozoites seen', 'G. lamblia cysts seen', 'G. lamblia trophozoites seen', 'Hookworm ova seen', 'Ascaris lumbricoides ova seen', 'Schistosoma mansoni ova seen', 'Trichuris trichiura ova seen'], 'parent_name': 'STOOL ANALYSIS', 'sort_order': 2},
    {'name': 'Stool Occult Blood', 'section': 'Parasitology & Stool Diagnostics', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Negative', 'Positive'], 'parent_name': 'STOOL ANALYSIS', 'sort_order': 3},
    {'name': 'Determine', 'section': 'Serology & Clinical Immunology', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Non-Reactive', 'Reactive'], 'parent_name': 'HIV Testing Service', 'sort_order': 1},
    {'name': 'Stat-Pak', 'section': 'Serology & Clinical Immunology', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Non-Reactive', 'Reactive'], 'parent_name': 'HIV Testing Service', 'sort_order': 2},
    {'name': 'SD Bioline', 'section': 'Serology & Clinical Immunology', 'is_tracked': 0, 'result_type': 'options', 'default_unit': None, 'secondary_unit': None, 'ref_range': None, 'options': ['Non-Reactive', 'Reactive'], 'parent_name': 'HIV Testing Service', 'sort_order': 3}
]


def seed_database():
    print("Initializing database schema...")
    init_db()
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Wards
    wards = ["ANC", "MCH", "Emergency", "Theater", "Labour", "OPD", "IPD", "Pediatrics", "TB Clinic"]
    for w_name in wards:
        cur.execute("INSERT OR IGNORE INTO wards (name) VALUES (?)", (w_name,))

    # Sections
    sec_map = {}
    for idx, name in enumerate(SECTIONS, 1):
        cur.execute("SELECT id FROM sections WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO sections (name, sort_order) VALUES (?, ?)", (name, idx))
            sec_id = cur.lastrowid
        else:
            sec_id = row["id"]
        sec_map[name] = sec_id

    conn.commit()

    # Rename migrations
    cur.execute("UPDATE tests SET name = 'Complete Blood Count (CBC)' WHERE name = 'CBC'")
    cur.execute("UPDATE tests SET name = 'HIV Testing Service' WHERE name = 'HIV (MoH Three-Test Algorithm)'")

    # Clean relative count test names
    rel_names = [
        ('Neutrophils (%) \\[Relative Count\\]', 'Neutrophils (%) [Relative Count]'),
        ('Lymphocytes (%) \\[Relative Count\\]', 'Lymphocytes (%) [Relative Count]'),
        ('Monocytes (%) \\[Relative Count\\]', 'Monocytes (%) [Relative Count]'),
        ('Eosinophils (%) \\[Relative Count\\]', 'Eosinophils (%) [Relative Count]'),
        ('Basophils (%) \\[Relative Count\\]', 'Basophils (%) [Relative Count]')
    ]
    for old_n, new_n in rel_names:
        cur.execute("UPDATE tests SET name = ? WHERE name = ?", (new_n, old_n))

    # Urinalysis structure migration — remove old parameters replaced by the new tripartite structure
    old_urinalysis_params = [
        'Macroscopy (Physical Profile)',   # replaced by Color + Turbidity
        'Microscopy (Sediment Cytology)',  # replaced by 5 individual microscopy sub-parameters
    ]
    for old_param in old_urinalysis_params:
        # Delete result values referencing this test, then the test itself
        cur.execute("""
            DELETE FROM test_results WHERE parameter_id IN (
                SELECT id FROM tests WHERE name = ?
            )
        """, (old_param,))
        cur.execute("DELETE FROM tests WHERE name = ?", (old_param,))

    # Migrate Specific Gravity and PH from quantitative to options
    cur.execute("""
        UPDATE tests SET result_type = 'options', default_unit = NULL,
            options = '["1.000","1.005","1.010","1.015","1.020","1.025","1.030"]'
        WHERE name = 'Specific Gravity (S.G)'
    """)
    cur.execute("""
        UPDATE tests SET result_type = 'options', default_unit = NULL,
            options = '["5.0","6.0","6.5","7.0","7.5","8.0","8.5"]'
        WHERE name = 'PH'
    """)

    conn.commit()


    test_id_map = {}

    for t in TESTS:
        if t.get("parent_name"):
            continue
        sec_id = sec_map.get(t["section"])
        if not sec_id:
            continue
        opts = json.dumps(t["options"]) if t["options"] else None
        cur.execute("SELECT id FROM tests WHERE name = ? AND section_id = ?", (t["name"], sec_id))
        r = cur.fetchone()
        if not r:
            cur.execute("""
                INSERT INTO tests (name, section_id, is_tracked, sort_order, result_type,
                    default_unit, secondary_unit, ref_range, options)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (t["name"], sec_id, t["is_tracked"], t["sort_order"], t["result_type"],
                  t["default_unit"], t["secondary_unit"], t["ref_range"], opts))
            test_id_map[t["name"]] = cur.lastrowid
        else:
            cur.execute("""
                UPDATE tests SET is_tracked=?, result_type=?, default_unit=?, secondary_unit=?, ref_range=?, options=?
                WHERE id=?
            """, (t["is_tracked"], t["result_type"], t["default_unit"], t["secondary_unit"], t["ref_range"], opts, r["id"]))
            test_id_map[t["name"]] = r["id"]

    conn.commit()

    for t in TESTS:
        if not t.get("parent_name"):
            continue
        parent_id = test_id_map.get(t["parent_name"])
        if not parent_id:
            continue
        sec_id = sec_map.get(t["section"])
        if not sec_id:
            sec_id = list(sec_map.values())[0]
        opts = json.dumps(t["options"]) if t["options"] else None
        cur.execute("SELECT id FROM tests WHERE name = ? AND section_id = ?", (t["name"], sec_id))
        r = cur.fetchone()
        if not r:
            cur.execute("""INSERT OR IGNORE INTO tests (name, section_id, is_tracked, sort_order, result_type,
                    default_unit, secondary_unit, ref_range, options, parent_rollup_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (t["name"], sec_id, t["is_tracked"], t["sort_order"], t["result_type"],
                  t["default_unit"], t["secondary_unit"], t["ref_range"], opts, parent_id))
        else:
            cur.execute("""
                UPDATE tests SET result_type=?, default_unit=?, secondary_unit=?, ref_range=?, options=?, sort_order=?, parent_rollup_id=?
                WHERE id=?
            """, (t["result_type"], t["default_unit"], t["secondary_unit"], t["ref_range"], opts, t["sort_order"], parent_id, r["id"]))

        # Also sync into test_parameters for panel sub-parameter tracking and FK constraints
        cur.execute("SELECT id FROM test_parameters WHERE test_id = ? AND parameter_name = ?", (parent_id, t["name"]))
        tp_row = cur.fetchone()
        if not tp_row:
            cur.execute("""
                INSERT INTO test_parameters (test_id, parameter_name, unit, ref_range, sort_order, options)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (parent_id, t["name"], t["default_unit"], t["ref_range"], t["sort_order"], opts))
        else:
            cur.execute("""
                UPDATE test_parameters SET unit = ?, ref_range = ?, sort_order = ?, options = ?
                WHERE id = ?
            """, (t["default_unit"], t["ref_range"], t["sort_order"], opts, tp_row["id"]))

    conn.commit()
    conn.close()
    print(f"Seeding done: {len(sec_map)} sections, {len(TESTS)} tests.")


if __name__ == "__main__":
    seed_database()
