import io
import pytest
import pypdf
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
        "ward_of_origin": "OPD",
        "technician_name": "Lab Tech John",
        "verified_by": "Dr. Sarah"
    }
    results_data = [
        {
            "department": "Hematology",
            "tests": [
                {
                    "test_name": "Complete Blood Count (CBC)",
                    "result": "Completed",
                    "timestamp": "2026-08-17 14:57:05",
                    "sample_id": "0002413",
                    "parameters": [
                        {"name": "Total WBC Count (White Blood Cells)", "result": "3.7", "unit": "10^3 / uL", "flag": "Low", "reference_range": "4.0 - 9.0"},
                        {"name": "Red Blood Cells (RBC)", "result": "4.56", "unit": "10^6 / uL", "flag": "", "reference_range": "3.76 - 5.70"},
                        {"name": "Hemoglobin (Hb)", "result": "12.1", "unit": "g/dL", "flag": "", "reference_range": "12.0 - 18.0"},
                        {"name": "Hematocrit (HCT)", "result": "37.2", "unit": "%", "flag": "", "reference_range": "33.5 - 52.0"},
                        {"name": "Mean Cell Volume (MCV)", "result": "81.6", "unit": "fL", "flag": "", "reference_range": "80.0 - 100"},
                        {"name": "Mean Cell Hb (MCH)", "result": "26.5", "unit": "pg", "flag": "", "reference_range": "28.0 - 32.0"},
                        {"name": "Mean Cell Hb Conc (MCHC)", "result": "32.5", "unit": "g/dL", "flag": "", "reference_range": "31.0 - 35.0"},
                        {"name": "Platelets Count (PLT)", "result": "85", "unit": "10^3 / uL", "flag": "Low", "reference_range": "150 - 350"},
                        {"name": "Neutrophils (%) [Relative Count]", "result": "47.7", "unit": "%", "flag": "", "reference_range": "28.0 - 78.0"},
                        {"name": "Lymphocytes (%) [Relative Count]", "result": "30.6", "unit": "%", "flag": "", "reference_range": "17.0 - 57.0"},
                        {"name": "Monocytes (%) [Relative Count]", "result": "3.8", "unit": "%", "flag": "Low", "reference_range": "0.0 - 10.0"},
                        {"name": "Eosinophils (%) [Relative Count]", "result": "17.1", "unit": "%", "flag": "High", "reference_range": "0.0 - 10.0"},
                        {"name": "Basophils (%) [Relative Count]", "result": "0.8", "unit": "%", "flag": "", "reference_range": "0.0 - 2.0"},
                        {"name": "Neutrophils (Absolute Count)", "result": "1.8", "unit": "10^9 / uL", "flag": "Low", "reference_range": "1.1 - 7.0"},
                        {"name": "Lymphocytes (Absolute Count)", "result": "1.1", "unit": "10^9 / uL", "flag": "Low", "reference_range": "0.7 - 5.1"},
                        {"name": "Monocytes (Absolute Count)", "result": "0.1", "unit": "10^9 / uL", "flag": "Low", "reference_range": "0.0 - 0.9"},
                        {"name": "Eosinophils (Absolute Count)", "result": "0.6", "unit": "10^9 / uL", "flag": "", "reference_range": "0.0 - 0.9"},
                        {"name": "Basophils (Absolute Count)", "result": "0.0", "unit": "10^9 / uL", "flag": "", "reference_range": "0.0 - 0.2"},
                        {"name": "RBC Distribution Width (RDW)", "result": "13.2", "unit": "%", "flag": "", "reference_range": "11.6 - 14.0"},
                        {"name": "Thrombocrit (PCT)", "result": "0.06", "unit": "%", "flag": "Low", "reference_range": "0.16 - 0.33"},
                        {"name": "Mean Platelet Volume (MPV)", "result": "6.8", "unit": "fL", "flag": "", "reference_range": "7.0 - 11.0"},
                        {"name": "PLT Distribution Width (PDW)", "result": "20.9", "unit": "%", "flag": "High", "reference_range": "15.0 - 17.0"}
                    ]
                }
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b'%PDF-')
    
    # Assert single dedicated page fit
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    
    page_text = reader.pages[0].extract_text()
    assert "HAEMATOLOGY CBC REPORT" in page_text
    assert "Specimen :" in page_text
    assert "Blood" in page_text
    assert "Client No :" in page_text
    assert "Child" in page_text
    assert "3.7" in page_text
    assert "4.56" in page_text
    assert "12.1" in page_text
    assert "85" in page_text
    assert "Low" in page_text
    assert "High" in page_text
    assert "Technologist Signature" in page_text



def test_cbc_with_unbundled_parameters_in_results_data():
    """Verify that if CBC parameters are passed as separate tests, they are bundled onto dedicated CBC page."""
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
                {"test_name": "Total WBC Count (White Blood Cells)", "result": "3.7", "unit": "10^3 / uL", "flag": "Low", "reference_range": "6.0-14.0"},
                {"test_name": "Red Blood Cells (RBC)", "result": "4.56", "unit": "10^6 / uL", "flag": "", "reference_range": "4.00 -5.20"},
                {"test_name": "Hemoglobin (Hb)", "result": "12.1", "unit": "g/dL", "flag": "", "reference_range": "11.5-15.5"},
                {"test_name": "Platelets Count (PLT)", "result": "85", "unit": "10^3 / uL", "flag": "Low", "reference_range": "150-400"},
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    page_text = reader.pages[0].extract_text()
    assert "HAEMATOLOGY CBC REPORT" in page_text
    assert "3.7" in page_text
    assert "4.56" in page_text
    assert "12.1" in page_text
    assert "85" in page_text


def test_mixed_order_cbc_on_dedicated_page():
    """Mixed order with routine chemistry + dedicated CBC should produce exactly 2 pages."""
    order_data = {
        "full_name": "KIGOZI RONALD",
        "client_number": "AMH-C26-0100",
        "lab_number": "100",
        "age": "34y",
        "sex": "Male",
        "ordered_date": "2026-08-18",
        "requested_by": "DR. NAKATO",
        "ward_of_origin": "IPD",
        "technician_name": "Tech Alex",
        "verified_by": "Dr. Sarah"
    }
    results_data = [
        {
            "department": "Parasitology",
            "tests": [
                {"test_name": "Malaria BS", "result": "No malaria parasites seen", "unit": "", "flag": "", "reference": "Negative"}
            ]
        },
        {
            "department": "Hematology",
            "tests": [
                {
                    "test_name": "Complete Blood Count (CBC)",
                    "result": "Completed",
                    "parameters": [
                        {"name": "Total WBC Count (White Blood Cells)", "result": "4.1", "unit": "10^3 / uL", "flag": "", "reference_range": "4.0 - 9.0"},
                        {"name": "Hemoglobin (Hb)", "result": "16.9", "unit": "g/dL", "flag": "", "reference_range": "12.0 - 18.0"}
                    ]
                }
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    # Page 1: Malaria BS, Page 2: Dedicated CBC page
    assert len(reader.pages) == 2
    page2_text = reader.pages[1].extract_text()
    assert "HAEMATOLOGY CBC REPORT" in page2_text
    assert "4.1" in page2_text
    assert "16.9" in page2_text


def test_panel_test_grouped_rendering_in_pdf():
    """Verify that biochemistry panels (LFTs, Electrolytes) render panel subheaders and child parameters without repeating parent."""
    order_data = {
        "full_name": "JOHN MUKASA",
        "client_number": "AMH-C26-0246",
        "lab_number": "246",
        "age": "32y",
        "sex": "Male",
        "ordered_date": "2026-08-25",
        "requested_by": "DR. TUGUME",
        "ward_of_origin": "OPD",
        "technician_name": "Tech Alex",
        "verified_by": "Dr. Sarah"
    }
    results_data = [
        {
            "department": "Clinical Biochemistry",
            "tests": [
                {
                    "test_name": "LFTS (Liver Function Tests)",
                    "result": "Completed",
                    "parameters": [
                        {"name": "ALT / SGPT", "result": "25.0", "unit": "U/L", "flag": "", "reference_range": "< 41"},
                        {"name": "AST / SGOT", "result": "22.0", "unit": "U/L", "flag": "", "reference_range": "< 38"},
                        {"name": "Total Bilirubin", "result": "12.0", "unit": "µmol/L", "flag": "", "reference_range": "0 - 17"},
                        {"name": "Direct Bilirubin", "result": "3.2", "unit": "µmol/L", "flag": "", "reference_range": "0 - 4.4"}
                    ]
                }
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    page_text = reader.pages[0].extract_text()
    assert "LFTS (Liver Function Tests)" in page_text
    assert "ALT / SGPT" in page_text
    assert "AST / SGOT" in page_text
    assert "Total Bilirubin" in page_text
    assert "Direct Bilirubin" in page_text
    assert "25.0" in page_text
    assert "12.0" in page_text
    assert "3.2" in page_text
    # Should only appear once as panel header
    assert page_text.count("LFTS (Liver Function Tests)") == 1



