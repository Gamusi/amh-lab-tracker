from typing import List, Dict, Any, Tuple, Optional

# Category Constants (NO EMOJIS, per BEST_PRACTICES Rule A.1)
URINE_CATEGORY_NO_GROWTH = "no_growth"
URINE_CATEGORY_CONTAMINATION = "contamination"
URINE_CATEGORY_SUSPICIOUS = "suspicious_low_count"
URINE_CATEGORY_SIGNIFICANT = "significant"

# Safety Alert Headers (Text only)
ALERT_CRITICAL_ESBL = (
    "[CRITICAL ESBL RESISTANCE]: Phenotypic screening confirms Extended-Spectrum Beta-Lactamase (ESBL) "
    "production. All penicillins, cephalosporins, and monobactams are clinically ineffective and MUST be "
    "reported as RESISTANT (R). Carbapenem therapy (e.g., Imipenem/Meropenem) or sensitive aminoglycosides "
    "are recommended in consultation with Infectious Disease guidelines."
)

ALERT_CRITICAL_MRSA = (
    "[CRITICAL MRSA ALERT]: Isolate is confirmed as Methicillin-Resistant Staphylococcus aureus (MRSA). "
    "All penicillins, cephalosporins, and beta-lactamase inhibitor combinations are clinically ineffective "
    "and are reported as RESISTANT (R). Glycopeptides (e.g., Vancomycin) or sensitive non-beta-lactams "
    "should be reviewed for therapy."
)

ALERT_EMERGENCY_CRE = (
    "[EMERGENCY RESISTANCE ALERT]: Carbapenem-Resistant Enterobacteriaceae (CRE) phenotypic marker detected. "
    "Extreme multidrug resistance confirmed. Immediate contact isolation precautions must be enforced on "
    "the ward. Notification has been automatically transmitted to the Hospital Director and Infection "
    "Control Committee."
)

ALERT_BLOOD_CONTAMINANT = (
    "Isolated {organism} in {bottles_pos} of {total_bottles} bottles. Highly suggestive of skin "
    "contamination during venipuncture. Use clinical discretion before initiating aggressive antimicrobial "
    "therapy."
)

ALERT_STERILE_FLUID_EMERGENCY = (
    "[CRITICAL EMERGENCY]: Organism detected in sterile body fluid ({specimen}): {finding}. "
    "Immediate 15-minute verbal callback to attending ward required."
)

# CLSI Target Organisms for ESBL screening
ESBL_TARGET_ORGANISMS = {
    "escherichia coli", "e. coli",
    "klebsiella pneumoniae", "k. pneumoniae",
    "klebsiella oxytoca", "k. oxytoca",
    "proteus mirabilis", "p. mirabilis"
}

# Beta-lactams overridden by ESBL
ESBL_OVERRIDDEN_CLASSES = {"penicillins", "cephalosporins", "monobactams"}
ESBL_OVERRIDDEN_AGENTS = {
    "ampicillin", "amoxicillin", "amoxicillin/clavulanate", "ampicillin/sulbactam",
    "piperacillin", "piperacillin/tazobactam", "cefazolin", "cephalexin",
    "cefuroxime", "cefotaxime", "ceftriaxone", "ceftazidime", "cefepime",
    "aztreonam"
}

# Beta-lactams overridden by MRSA
MRSA_OVERRIDDEN_CLASSES = {"penicillins", "cephalosporins", "beta-lactam/inh."}
MRSA_OVERRIDDEN_AGENTS = {
    "penicillin", "ampicillin", "amoxicillin", "amoxicillin/clavulanate",
    "ampicillin/sulbactam", "piperacillin/tazobactam", "oxacillin", "cloxacillin",
    "cefazolin", "cephalexin", "cefuroxime", "cefotaxime", "ceftriaxone",
    "ceftazidime", "cefepime"
}

# Carbapenem agents
CARBAPENEM_AGENTS = {"imipenem", "meropenem", "ertapenem", "doripenem"}

# Blood culture common skin contaminants
BLOOD_SKIN_CONTAMINANTS = {
    "coagulase-negative staphylococci", "cons", "staphylococcus epidermidis",
    "s. epidermidis", "micrococcus", "micrococcus species", "micrococcus spp",
    "bacillus", "bacillus species", "bacillus spp", "corynebacterium", "corynebacterium spp"
}

# Blood culture high-virulence pathogens
BLOOD_TRUE_PATHOGENS = {
    "staphylococcus aureus", "s. aureus",
    "streptococcus pneumoniae", "s. pneumoniae",
    "escherichia coli", "e. coli",
    "pseudomonas aeruginosa", "p. aeruginosa",
    "klebsiella pneumoniae", "k. pneumoniae",
    "salmonella", "salmonella spp", "salmonella enterica"
}


def evaluate_urine_colony_count(
    cfu_str: str,
    organism_count: int = 1,
    organism_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates urine culture colony count logic gates (CFU/mL) per clinical spec.
    """
    clean_cfu = (cfu_str or "").strip().lower()
    org_name = (organism_name or "Bacterial species").strip()

    # Gate 2: Polymicrobial Contamination (>= 3 species)
    if organism_count >= 3:
        return {
            "category": URINE_CATEGORY_CONTAMINATION,
            "allow_ast": False,
            "reporting_text": (
                "Polymicrobial growth detected (>= 3 bacterial species isolated), strongly suggestive "
                "of specimen contamination during collection. A definitive susceptibility profile cannot "
                "be generated. Clinical correlation is recommended; please obtain a fresh, clean-catch "
                "midstream urine specimen if clinically indicated."
            ),
            "is_tracked_finding": False
        }

    # Gate 1: No Growth (< 10^3 CFU/mL)
    if "< 10^3" in clean_cfu or "no growth" in clean_cfu or organism_count == 0:
        return {
            "category": URINE_CATEGORY_NO_GROWTH,
            "allow_ast": False,
            "reporting_text": "No significant aerobic bacterial growth after 48 hours of incubation (< 10^3 CFU/mL).",
            "is_tracked_finding": False
        }

    # Gate 3: Suspicious Low-Count Growth (10^3 - 10^4 CFU/mL)
    if "10^3" in clean_cfu and "10^4" in clean_cfu:
        return {
            "category": URINE_CATEGORY_SUSPICIOUS,
            "allow_ast": True,
            "reporting_text": (
                f"Low-count growth isolated (10^3 - 10^4 CFU/mL of {org_name}). Susceptibility profile is "
                "provided below for clinical correlation (e.g., early-stage UTI, acute urethral syndrome, "
                "or catheterized patient)."
            ),
            "is_tracked_finding": False
        }

    # Gate 4: Clinically Significant Bacteriuria (>= 10^5 CFU/mL)
    return {
        "category": URINE_CATEGORY_SIGNIFICANT,
        "allow_ast": True,
        "reporting_text": (
            f"Significant growth of {org_name} isolated (colony count: >= 10^5 CFU/mL). "
            "Highly indicative of active Urinary Tract Infection (UTI)."
        ),
        "is_tracked_finding": True
    }


def evaluate_blood_culture_isolate(
    organism_name: str,
    bottles_positive: int = 1,
    total_bottles: int = 2
) -> Dict[str, Any]:
    """
    Distinguishes true septicemia pathogens from normal venipuncture skin contaminants.
    """
    org_clean = (organism_name or "").strip().lower()

    is_skin_contaminant = any(c in org_clean for c in BLOOD_SKIN_CONTAMINANTS)

    if is_skin_contaminant and bottles_positive < total_bottles:
        warning_msg = ALERT_BLOOD_CONTAMINANT.format(
            organism=organism_name,
            bottles_pos=bottles_positive,
            total_bottles=total_bottles
        )
        return {
            "is_contaminant": True,
            "is_pathogen": False,
            "is_panic_alert": False,
            "warning_text": warning_msg,
            "is_tracked_finding": False
        }

    return {
        "is_contaminant": False,
        "is_pathogen": True,
        "is_panic_alert": True,
        "warning_text": None,
        "is_tracked_finding": True
    }


def evaluate_sterile_fluid_isolate(
    finding_or_organism: str,
    specimen: str = "CSF"
) -> Dict[str, Any]:
    """
    Applies zero-tolerance policy to sterile body fluids (CSF, Pleural, Ascitic, Synovial).
    """
    warning_msg = ALERT_STERILE_FLUID_EMERGENCY.format(
        specimen=specimen,
        finding=finding_or_organism
    )
    return {
        "is_critical_emergency": True,
        "requires_15min_callback": True,
        "warning_text": warning_msg,
        "is_tracked_finding": True
    }


def apply_phenotypic_safety_overrides(
    organism_name: str,
    ast_list: List[Dict[str, Any]],
    is_esbl_positive: bool = False,
    is_mrsa_positive: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Applies CLSI M100 automated phenotypic overrides (ESBL, MRSA, CRE).
    """
    org_clean = (organism_name or "").strip().lower()
    overridden_ast = []
    alerts = []

    is_staph = "staphylococcus aureus" in org_clean or org_clean == "s. aureus"
    if is_staph:
        for ast in ast_list:
            agent = str(ast.get("agent_name") or ast.get("agent") or "").strip().lower()
            sir = str(ast.get("raw_sir") or "").strip().upper()
            if agent in ("cefoxitin", "oxacillin") and sir == "R":
                is_mrsa_positive = True
                break

    has_cre_resistance = False
    for ast in ast_list:
        agent = str(ast.get("agent_name") or ast.get("agent") or "").strip().lower()
        sir = str(ast.get("raw_sir") or "").strip().upper()
        if agent in CARBAPENEM_AGENTS and sir == "R":
            has_cre_resistance = True
            break

    for ast in ast_list:
        row = dict(ast)
        agent = str(row.get("agent_name") or row.get("agent") or "").strip().lower()
        aclass = str(row.get("antimicrobial_class") or row.get("class") or "").strip().lower()
        raw_sir = str(row.get("raw_sir") or "").strip().upper()

        overridden_sir = raw_sir
        override_reason = None

        if is_esbl_positive:
            if (
                aclass in ESBL_OVERRIDDEN_CLASSES
                or agent in ESBL_OVERRIDDEN_AGENTS
                or "penicillin" in aclass
                or "cephalosporin" in aclass
            ):
                if raw_sir != "R":
                    overridden_sir = "R"
                    override_reason = "Forced Resistant (R) due to confirmed ESBL phenotype."

        if is_mrsa_positive and is_staph:
            if (
                aclass in MRSA_OVERRIDDEN_CLASSES
                or agent in MRSA_OVERRIDDEN_AGENTS
                or "penicillin" in aclass
                or "cephalosporin" in aclass
                or "beta-lactam" in aclass
            ):
                if raw_sir != "R":
                    overridden_sir = "R"
                    override_reason = "Forced Resistant (R) due to confirmed MRSA phenotype."

        row["overridden_sir"] = overridden_sir
        row["override_reason"] = override_reason
        overridden_ast.append(row)

    if is_esbl_positive:
        alerts.append(ALERT_CRITICAL_ESBL)
    if is_mrsa_positive and is_staph:
        alerts.append(ALERT_CRITICAL_MRSA)
    if has_cre_resistance:
        alerts.append(ALERT_EMERGENCY_CRE)

    return overridden_ast, alerts
