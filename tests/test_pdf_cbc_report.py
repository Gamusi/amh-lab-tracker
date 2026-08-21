import pytest
from backend.app.pdf_generator import generate_pdf

def test_generate_pdf_with_cbc_dedicated_page():
    order_data = {
        "full_name": "WANELOBA DANIEL",
        "client_number": "AMH-C26-0094",
        "lab_number": "94",
        "age": "12y",
        "sex": "Male",
        "ordered_date": "2026-08-15",
        "requested_by": "DR. TUGUME",
        "ward_of_origin": "OPD"
    }
    results_data = [
        {
            "department": "Hematology",
            "tests": [
                {
                    "test_name": "Complete Blood Count (CBC)",
                    "result": "Completed",
                    "parameters": [
                        {"name": "Total WBC Count (White Blood Cells)", "result": "3.7", "unit": "10^3 / uL", "flag": "Low", "reference": "6.0-14.0"},
                        {"name": "Red Blood Cells (RBC)", "result": "4.56", "unit": "10^6 / uL", "flag": "", "reference": "4.00 -5.20"},
                        {"name": "Hemoglobin (Hb)", "result": "12.1", "unit": "g/dL", "flag": "", "reference": "11.5-15.5"},
                        {"name": "Hematocrit (HCT)", "result": "37.2", "unit": "%", "flag": "", "reference": "35.0-45.0"},
                        {"name": "Mean Cell Volume (MCV)", "result": "81.6", "unit": "fL", "flag": "", "reference": "77.0-95.0"},
                        {"name": "Mean Cell Hb (MCH)", "result": "26.5", "unit": "pg", "flag": "", "reference": "23.0-31.0"},
                        {"name": "Mean Cell Hb Conc (MCHC)", "result": "32.5", "unit": "g/dL", "flag": "", "reference": "28.0-33.0"},
                        {"name": "Platelets Count (PLT)", "result": "85", "unit": "10^3 / uL", "flag": "Low", "reference": "150-400"},
                        {"name": "Neutrophils (%) [Relative Count]", "result": "47.7", "unit": "%", "flag": "", "reference": "40.0-65.0"},
                        {"name": "Lymphocytes (%) [Relative Count]", "result": "30.6", "unit": "%", "flag": "", "reference": "19.2-49.5"},
                        {"name": "Monocytes (%) [Relative Count]", "result": "3.8", "unit": "%", "flag": "Low", "reference": "4.5-12.1"},
                        {"name": "Eosinophils (%) [Relative Count]", "result": "17.1", "unit": "%", "flag": "High", "reference": "1.0-12.0"},
                        {"name": "Basophils (%) [Relative Count]", "result": "0.8", "unit": "%", "flag": "", "reference": "0.0-1.0"},
                        {"name": "Neutrophils (Absolute Count)", "result": "1.8", "unit": "10^9 / uL", "flag": "Low", "reference": "2.00-6.00"},
                        {"name": "Lymphocytes (Absolute Count)", "result": "1.1", "unit": "10^9 / uL", "flag": "Low", "reference": "5.00-8.50"},
                        {"name": "Monocytes (Absolute Count)", "result": "0.1", "unit": "10^9 / uL", "flag": "Low", "reference": "0.70-1.50"},
                        {"name": "Eosinophils (Absolute Count)", "result": "0.6", "unit": "10^9 / uL", "flag": "", "reference": "0.30-0.80"},
                        {"name": "Basophils (Absolute Count)", "result": "0.0", "unit": "10^9 / uL", "flag": "", "reference": "0.0-0.5"},
                        {"name": "RBC Distribution Width (RDW)", "result": "13.2", "unit": "%", "flag": "", "reference": "11.0-16.0"},
                        {"name": "Thrombocrit (PCT)", "result": "0.06", "unit": "%", "flag": "Low", "reference": "0.16-0.33"},
                        {"name": "Mean Platelet Volume (MPV)", "result": "6.8", "unit": "fL", "flag": "", "reference": "6.0 - 10.0"},
                        {"name": "PLT Distribution Width (PDW)", "result": "20.9", "unit": "%", "flag": "High", "reference": "12.0 - 18.0"}
                    ]
                }
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b'%PDF-')
