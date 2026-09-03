import sqlite3
import pytest
from backend.app.database import init_db, get_connection

def test_culture_schema_tables_exist(tmp_path, monkeypatch):
    test_db = str(tmp_path / 'test_cs.db')
    monkeypatch.setenv('MLIS_DB_PATH', test_db)
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('culture_orders', 'culture_isolates', 'culture_ast_results')")
    tables = {r[0] for r in cur.fetchall()}
    assert 'culture_orders' in tables
    assert 'culture_isolates' in tables
    assert 'culture_ast_results' in tables
    conn.close()

from backend.app.culture_engine import (
    evaluate_urine_colony_count,
    evaluate_blood_culture_isolate,
    evaluate_sterile_fluid_isolate,
    apply_phenotypic_safety_overrides,
    URINE_CATEGORY_NO_GROWTH,
    URINE_CATEGORY_CONTAMINATION,
    URINE_CATEGORY_SUSPICIOUS,
    URINE_CATEGORY_SIGNIFICANT
)

def test_urine_colony_quantification_gates():
    res1 = evaluate_urine_colony_count(cfu_str="< 10^3", organism_count=0)
    assert res1["category"] == URINE_CATEGORY_NO_GROWTH
    assert res1["allow_ast"] is False
    assert "No significant aerobic bacterial growth" in res1["reporting_text"]

    res2 = evaluate_urine_colony_count(cfu_str=">= 10^5", organism_count=3)
    assert res2["category"] == URINE_CATEGORY_CONTAMINATION
    assert res2["allow_ast"] is False
    assert "Polymicrobial growth detected" in res2["reporting_text"]

    res3 = evaluate_urine_colony_count(cfu_str="10^3 - 10^4", organism_count=1, organism_name="Escherichia coli")
    assert res3["category"] == URINE_CATEGORY_SUSPICIOUS
    assert res3["allow_ast"] is True
    assert "Low-count growth isolated" in res3["reporting_text"]

    res4 = evaluate_urine_colony_count(cfu_str=">= 10^5", organism_count=1, organism_name="Escherichia coli")
    assert res4["category"] == URINE_CATEGORY_SIGNIFICANT
    assert res4["allow_ast"] is True
    assert "Significant growth" in res4["reporting_text"]

def test_blood_culture_evaluation():
    # Skin contaminant isolated in 1 of 2 bottles
    skin_res = evaluate_blood_culture_isolate("Staphylococcus epidermidis", bottles_positive=1, total_bottles=2)
    assert skin_res["is_contaminant"] is True
    assert "Highly suggestive of skin contamination" in skin_res["warning_text"]

    # True pathogen in any bottle
    path_res = evaluate_blood_culture_isolate("Staphylococcus aureus", bottles_positive=1, total_bottles=2)
    assert path_res["is_pathogen"] is True
    assert path_res["is_contaminant"] is False
    assert path_res["is_panic_alert"] is True

def test_sterile_fluid_evaluation():
    csf_res = evaluate_sterile_fluid_isolate("Gram-negative intracellular diplococci", specimen="CSF")
    assert csf_res["is_critical_emergency"] is True
    assert csf_res["requires_15min_callback"] is True

def test_phenotypic_override_esbl():
    ast_input = [
        {"antimicrobial_class": "Cephalosporins", "agent_name": "Ceftriaxone", "raw_sir": "S"},
        {"antimicrobial_class": "Penicillins", "agent_name": "Ampicillin", "raw_sir": "S"},
        {"antimicrobial_class": "Fluoroquinolones", "agent_name": "Ciprofloxacin", "raw_sir": "S"},
        {"antimicrobial_class": "Carbapenems", "agent_name": "Meropenem", "raw_sir": "S"},
    ]
    overridden, alerts = apply_phenotypic_safety_overrides("Escherichia coli", ast_input, is_esbl_positive=True)
    ceft = next(a for a in overridden if a["agent_name"] == "Ceftriaxone")
    amp = next(a for a in overridden if a["agent_name"] == "Ampicillin")
    cipro = next(a for a in overridden if a["agent_name"] == "Ciprofloxacin")
    mero = next(a for a in overridden if a["agent_name"] == "Meropenem")
    
    assert ceft["overridden_sir"] == "R"
    assert amp["overridden_sir"] == "R"
    assert cipro["overridden_sir"] == "S"
    assert mero["overridden_sir"] == "S"
    assert any("CRITICAL ESBL RESISTANCE" in al for al in alerts)

def test_phenotypic_override_mrsa():
    ast_input = [
        {"antimicrobial_class": "Beta-Lactam/Inh.", "agent_name": "Amoxicillin/Clavulanate", "raw_sir": "S"},
        {"antimicrobial_class": "Cephalosporins", "agent_name": "Cefoxitin", "raw_sir": "R"},
        {"antimicrobial_class": "Glycopeptides", "agent_name": "Vancomycin", "raw_sir": "S"}
    ]
    overridden, alerts = apply_phenotypic_safety_overrides("Staphylococcus aureus", ast_input, is_mrsa_positive=True)
    amox = next(a for a in overridden if a["agent_name"] == "Amoxicillin/Clavulanate")
    vanc = next(a for a in overridden if a["agent_name"] == "Vancomycin")
    assert amox["overridden_sir"] == "R"
    assert vanc["overridden_sir"] == "S"
    assert any("CRITICAL MRSA ALERT" in al for al in alerts)

def test_phenotypic_override_cre():
    ast_input = [
        {"antimicrobial_class": "Carbapenems", "agent_name": "Meropenem", "raw_sir": "R"},
        {"antimicrobial_class": "Aminoglycosides", "agent_name": "Gentamicin", "raw_sir": "S"}
    ]
    overridden, alerts = apply_phenotypic_safety_overrides("Klebsiella pneumoniae", ast_input)
    assert any("EMERGENCY RESISTANCE ALERT" in al and "Carbapenem-Resistant Enterobacteriaceae" in al for al in alerts)

