"""
M-LIS Laboratory Specimen Validation Engine
Grounded in docs/planning/mlis-laboratory-specimen-catalog.md and ISO 15189:2022 standards.
"""

from typing import List, Dict, Optional, Tuple, Set

SPECIMEN_EDTA = "EDTA Whole Blood"
SPECIMEN_CITRATE = "Sodium Citrate Whole Blood"
SPECIMEN_BLOOD_CULTURE = "Blood (for Culture)"
SPECIMEN_CAPILLARY = "Capillary / Fingerstick Blood"
SPECIMEN_SERUM_RED = "Serum (Red Top)"
SPECIMEN_SERUM_SST = "Serum (SST / Gel Separator)"
SPECIMEN_PLASMA_HEPARIN = "Plasma (Lithium Heparin)"
SPECIMEN_PLASMA_FLUORIDE = "Plasma (Fluoride / Oxalate)"
SPECIMEN_URINE = "Clean-Catch Midstream Urine"
SPECIMEN_STOOL = "Random Stool / Feces"
SPECIMEN_CSF = "Cerebrospinal Fluid (CSF)"
SPECIMEN_SPUTUM = "Sputum"
SPECIMEN_SWAB = "Swab (Wound / Throat / Pus / Urogenital)"
SPECIMEN_ORAL = "Oral Fluid / Saliva"
SPECIMEN_FNA_BIOPSY = "Fine Needle Aspirate (FNA) / Tissue Biopsy"

BIOCHEM_SERUM_PLASMA = [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST, SPECIMEN_PLASMA_HEPARIN]
SEROLOGY_SERUM = [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST]
SEROLOGY_RAPID = [SPECIMEN_CAPILLARY, SPECIMEN_EDTA, SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST]

SPECIMEN_REPORT_ALIASES = {
    "edta whole blood": "EDTA Whole Blood",
    "whole blood (edta)": "EDTA Whole Blood",
    "sodium citrate whole blood": "Citrate Blood",
    "blood (for culture)": "Blood Culture",
    "capillary / fingerstick blood": "Capillary Blood",
    "serum (red top)": "Serum",
    "serum (sst / gel separator)": "Serum",
    "plasma (lithium heparin)": "Heparin Plasma",
    "plasma (fluoride / oxalate)": "Fluoride Plasma",
    "clean-catch midstream urine": "Urine",
    "random stool / feces": "Stool",
    "cerebrospinal fluid (csf)": "CSF",
    "sputum": "Sputum",
    "swab (wound / throat / pus / urogenital)": "Swab",
    "oral fluid / saliva": "Oral Fluid",
    "fine needle aspirate (fna) / tissue biopsy": "FNA / Biopsy",
    "fna cytology": "FNA / Biopsy",
}

def get_specimen_report_alias(specimen_name: str) -> str:
    if not specimen_name:
        return ""
    sn = specimen_name.strip().lower()
    if sn in SPECIMEN_REPORT_ALIASES:
        return SPECIMEN_REPORT_ALIASES[sn]
    for k, v in SPECIMEN_REPORT_ALIASES.items():
        if k in sn or sn in k:
            return v
    cleaned = specimen_name.split('(')[0].strip()
    return cleaned if cleaned else specimen_name

TEST_SPECIMEN_MAP = {
    # Hematology
    "complete blood count (cbc)": [SPECIMEN_EDTA],
    "cbc": [SPECIMEN_EDTA],
    "full blood count": [SPECIMEN_EDTA],
    "erythrocyte sedimentation rate (esr)": [SPECIMEN_EDTA, SPECIMEN_CITRATE],
    "esr": [SPECIMEN_EDTA, SPECIMEN_CITRATE],
    "sickling test": [SPECIMEN_EDTA],
    "reticulocyte count": [SPECIMEN_EDTA],
    "cd4 count": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "absolute cd4 count (cytometry)": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "cd4 count (rapid test strip)": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "cd4_quant": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "cd4_rdt": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "cd4 percentage": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "blood smear for malaria parasites": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "blood smear": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "malaria microscopy": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "coagulation profile": [SPECIMEN_CITRATE],
    "prothrombin time (pt/inr)": [SPECIMEN_CITRATE],
    "aptt": [SPECIMEN_CITRATE],
    "pt/inr": [SPECIMEN_CITRATE],

    # Clinical Biochemistry Panels
    "liver function tests (lfts)": BIOCHEM_SERUM_PLASMA,
    "lfts": BIOCHEM_SERUM_PLASMA,
    "renal function tests (rfts)": BIOCHEM_SERUM_PLASMA,
    "rfts": BIOCHEM_SERUM_PLASMA,
    "electrolytes": BIOCHEM_SERUM_PLASMA,
    "cardiac biomarkers": BIOCHEM_SERUM_PLASMA,
    "cardiac profile": BIOCHEM_SERUM_PLASMA,
    "lipid profile": [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "fbs (fasting blood sugar)": [SPECIMEN_PLASMA_FLUORIDE, SPECIMEN_CAPILLARY, SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "fasting blood sugar (fbs)": [SPECIMEN_PLASMA_FLUORIDE, SPECIMEN_CAPILLARY, SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "rbs (random blood sugar)": [SPECIMEN_PLASMA_FLUORIDE, SPECIMEN_CAPILLARY, SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "random blood sugar (rbs)": [SPECIMEN_PLASMA_FLUORIDE, SPECIMEN_CAPILLARY, SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "serum uric acid": BIOCHEM_SERUM_PLASMA,
    "serum amylase": [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "serum lipase": [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "serum calcium": [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST, SPECIMEN_PLASMA_HEPARIN],
    "serum phosphorus": [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST],
    "serum magnesium": [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST, SPECIMEN_PLASMA_HEPARIN],
    "total protein": BIOCHEM_SERUM_PLASMA,
    "albumin": BIOCHEM_SERUM_PLASMA,
    "bilirubin": BIOCHEM_SERUM_PLASMA,
    "alt": BIOCHEM_SERUM_PLASMA,
    "ast": BIOCHEM_SERUM_PLASMA,
    "alp": BIOCHEM_SERUM_PLASMA,
    "creatinine": BIOCHEM_SERUM_PLASMA,
    "urea": BIOCHEM_SERUM_PLASMA,

    # Urinalysis Profile
    "urinalysis": [SPECIMEN_URINE],
    "routine urinalysis": [SPECIMEN_URINE],
    "urine pregnancy test": [SPECIMEN_URINE],
    "hcg (urine)": [SPECIMEN_URINE],
    "urine tb-lam": [SPECIMEN_URINE],
    "tb-lam (urine)": [SPECIMEN_URINE],
    "tb lam (urine tuberculosis lam)": [SPECIMEN_URINE],
    "urine bence jones protein": [SPECIMEN_URINE],

    # Parasitology & Stool Diagnostics
    "stool analysis": [SPECIMEN_STOOL],
    "stool analysis (macroscopy/microscopy)": [SPECIMEN_STOOL],
    "stool occult blood": [SPECIMEN_STOOL],
    "fecal occult blood": [SPECIMEN_STOOL],
    "h.pylori ag (stool)": [SPECIMEN_STOOL],
    "h.pylori stool antigen": [SPECIMEN_STOOL],

    # Serology & Immunology
    "malaria rdt": [SPECIMEN_CAPILLARY, SPECIMEN_EDTA, SPECIMEN_SERUM_RED],
    "hiv testing": SEROLOGY_RAPID,
    "hiv (moh three-test algorithm)": SEROLOGY_RAPID,
    "mhs hiv 1/2 kwiq test": SEROLOGY_RAPID,
    "determine hiv-1/2": SEROLOGY_RAPID,
    "determine™ hiv-1/2": SEROLOGY_RAPID,
    "hiv 1/2 stat-pak®": SEROLOGY_RAPID,
    "hiv 1/2 stat-pak": SEROLOGY_RAPID,
    "sd bioline hiv-1/2": SEROLOGY_RAPID,
    "oraquick® hiv self-test": [SPECIMEN_ORAL],
    "oraquick hiv self-test": [SPECIMEN_ORAL],
    "fingerstick hivst": [SPECIMEN_CAPILLARY],
    "eid 1st pcr (4-6 weeks)": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "eid 2nd pcr (9 months)": [SPECIMEN_EDTA, SPECIMEN_CAPILLARY],
    "eid final rapid test (18 months)": SEROLOGY_RAPID,
    "hbsag (hepatitis b)": SEROLOGY_SERUM,
    "hbsag (hepatitis b surface antigen)": SEROLOGY_SERUM,
    "hcv ab (hepatitis c)": SEROLOGY_SERUM,
    "vdrl / rpr (syphilis screening)": SEROLOGY_SERUM,
    "vdrl/rpr (syphilis screening)": SEROLOGY_SERUM,
    "vdrl/rpr": SEROLOGY_SERUM,
    "tpha (confirmatory syphilis test)": SEROLOGY_SERUM,
    "brucella antigen test (bat)": SEROLOGY_SERUM,
    "bat (brucella agglutination)": SEROLOGY_SERUM,
    "widal (typhoid agglutination)": SEROLOGY_SERUM,
    "aso titer (anti-streptolysin o)": SEROLOGY_SERUM,
    "rheumatoid factor (rf)": SEROLOGY_SERUM,
    "h.pylori ab (blood)": SEROLOGY_SERUM,
    "cryptococcal antigen (crag)": [SPECIMEN_SERUM_RED, SPECIMEN_SERUM_SST, SPECIMEN_CSF],
    "hcg (blood)": SEROLOGY_SERUM,
    "covid-19 rdt (antigen)": [SPECIMEN_SWAB, SPECIMEN_CAPILLARY],
    "alpha-fetoprotein (afp)": SEROLOGY_SERUM,

    # Microbiology & TB
    "zn staining for afbs": [SPECIMEN_SPUTUM, SPECIMEN_CSF, SPECIMEN_SWAB],
    "zn for afbs (tuberculosis sputum smear)": [SPECIMEN_SPUTUM, SPECIMEN_CSF, SPECIMEN_SWAB],
    "genexpert mtb/rif": [SPECIMEN_SPUTUM, SPECIMEN_CSF],
    "gram stain": [SPECIMEN_SWAB, SPECIMEN_URINE, SPECIMEN_CSF, SPECIMEN_SPUTUM],
    "urine culture & sensitivity (c&s)": [SPECIMEN_URINE],
    "stool culture & sensitivity (c&s)": [SPECIMEN_STOOL],
    "blood culture & sensitivity (c&s)": [SPECIMEN_BLOOD_CULTURE],
    "blood culture": [SPECIMEN_BLOOD_CULTURE],
    "high vaginal swab (hvs)": [SPECIMEN_SWAB],
    "urethral swab": [SPECIMEN_SWAB],

    # Blood Transfusion
    "blood group (abo & rh typing)": [SPECIMEN_EDTA, SPECIMEN_SERUM_RED],
    "direct coombs (direct antiglobulin test)": [SPECIMEN_EDTA],
    "indirect coombs (antibody screen)": [SPECIMEN_SERUM_RED, SPECIMEN_EDTA],
    "compatibility testing (cross-matching)": [SPECIMEN_EDTA, SPECIMEN_SERUM_RED],

    # Histopathology & Cytology
    "tissue biopsy": [SPECIMEN_FNA_BIOPSY],
    "fine needle aspirate (fna)": [SPECIMEN_FNA_BIOPSY],
    "fna cytology": [SPECIMEN_FNA_BIOPSY],
}

def get_compatible_specimens_for_test(test_name: str, section_name: Optional[str] = None) -> List[str]:
    """Return the list of accredited specimen types for a given test name."""
    t_clean = (test_name or "").strip().lower()
    
    if t_clean in TEST_SPECIMEN_MAP:
        return TEST_SPECIMEN_MAP[t_clean]
        
    for k, v in TEST_SPECIMEN_MAP.items():
        if k in t_clean or t_clean in k:
            return v

    if section_name:
        sec = section_name.strip().lower()
        if "urinalysis" in sec:
            return [SPECIMEN_URINE]
        if "stool" in sec or "parasitology" in sec:
            return [SPECIMEN_STOOL]
        if "biochemistry" in sec:
            return BIOCHEM_SERUM_PLASMA
        if "serology" in sec or "immunology" in sec:
            return SEROLOGY_SERUM
        if "hematology" in sec:
            return [SPECIMEN_EDTA]
        if "microbiology" in sec or "tuberculosis" in sec:
            return [SPECIMEN_SPUTUM, SPECIMEN_SWAB, SPECIMEN_URINE]
        if "transfusion" in sec:
            return [SPECIMEN_EDTA, SPECIMEN_SERUM_RED]

    return [SPECIMEN_SERUM_RED]


def _is_compatible_specimen(req_spec: str, sel_spec: str) -> bool:
    if not req_spec or not sel_spec:
        return False
    if req_spec.strip().lower() == sel_spec.strip().lower():
        return True
    
    r = req_spec.strip().lower()
    s = sel_spec.strip().lower()

    # EDTA Whole Blood
    if "edta" in r:
        return "edta" in s
    if "edta" in s:
        return "edta" in r

    # Sodium Citrate Whole Blood
    if "citrate" in r:
        return "citrate" in s
    if "citrate" in s:
        return "citrate" in r

    # Serum (Red Top / SST)
    if "serum" in r:
        return "serum" in s or ("heparin" in s and "plasma" in s)
    if "serum" in s:
        return "serum" in r or ("heparin" in r and "plasma" in r)

    # Plasma Fluoride / Oxalate
    if "fluoride" in r or "oxalate" in r:
        return "fluoride" in s or "oxalate" in s
    if "fluoride" in s or "oxalate" in s:
        return "fluoride" in r or "oxalate" in r

    # Plasma Lithium Heparin
    if "heparin" in r:
        return "heparin" in s or "serum" in s
    if "heparin" in s:
        return "heparin" in r or "serum" in r

    # Clean-Catch Midstream Urine
    if "urine" in r:
        return "urine" in s
    if "urine" in s:
        return "urine" in r

    # Stool
    if "stool" in r or "feces" in r:
        return "stool" in s or "feces" in s
    if "stool" in s or "feces" in s:
        return "stool" in r or "feces" in r

    # Sputum
    if "sputum" in r:
        return "sputum" in s
    if "sputum" in s:
        return "sputum" in r

    # CSF
    if "csf" in r or "cerebrospinal" in r:
        return "csf" in s or "cerebrospinal" in s
    if "csf" in s or "cerebrospinal" in s:
        return "csf" in r or "cerebrospinal" in r

    # Blood Culture
    if "culture" in r and "blood" in r:
        return "culture" in s and "blood" in s
    if "culture" in s and "blood" in s:
        return "culture" in r and "blood" in r

    # Capillary
    if "capillary" in r or "fingerstick" in r:
        return "capillary" in s or "fingerstick" in s
    if "capillary" in s or "fingerstick" in s:
        return "capillary" in r or "fingerstick" in r

    # Swabs
    if "swab" in r:
        return "swab" in s
    if "swab" in s:
        return "swab" in r

    return False

def validate_test_specimen_selection(
    tests: List[Dict[str, str]], 
    selected_specimen_names: List[str]
) -> Tuple[bool, List[str], Dict[str, str]]:
    """
    Validate that each ordered test is satisfied by at least one selected specimen.
    """
    if not selected_specimen_names:
        return False, ["At least one specimen type must be selected for the visit."], {}

    errors = []
    test_best_specimen = {}

    for t in tests:
        t_name = t.get("name", "Unknown Test")
        sec_name = t.get("section")
        compatible = get_compatible_specimens_for_test(t_name, sec_name)
        
        matched = []
        for s in selected_specimen_names:
            for c in compatible:
                if _is_compatible_specimen(c, s):
                    matched.append(s)
                    break
                    
        if not matched:
            req_str = ", ".join(compatible)
            errors.append(
                f"Test '{t_name}' requires [{req_str}], but selected specimen(s) [{', '.join(selected_specimen_names)}] do not match."
            )
        else:
            test_best_specimen[t_name] = matched[0]

    return len(errors) == 0, errors, test_best_specimen


def validate_specimen_for_test(test_name: str, specimen_name: str, section_name: Optional[str] = None) -> bool:
    """Validate if a specific specimen is accredited/compatible for a given test."""
    compatible = get_compatible_specimens_for_test(test_name, section_name)
    return any(_is_compatible_specimen(c, specimen_name) for c in compatible)
