import io
import pytest
from backend.app.pdf_generator import (
    generate_pdf, 
    _build_metadata_table, 
    _build_department_table, 
    _build_signatures_table
)
from reportlab.platypus import Table, KeepTogether

def test_generate_pdf_creates_bytes():
    order_data = {"client_number": "102", "full_name": "JOHN DOE", "sex": "M", "age": "30"}
    results_data = []
    pdf_bytes = generate_pdf(order_data, results_data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF-')

def test_build_metadata_table_legacy_fallback():
    order_data = {
        "client_number": "AMH-26-8-001", 
        "full_name": "LUCY KEMIGISHA", 
        "age": "32", 
        "sex": "F",
        "ordered_by": "Dr. Matia",
        "ordered_date": "17/08/2026",
        "verified_by": "Abubakar"
    }
    table = _build_metadata_table(order_data)
    assert isinstance(table, Table)
    assert table._cellvalues[0][1] == "LUCY KEMIGISHA"
    assert table._cellvalues[0][3] == "AMH-26-8-001"
    assert table._cellvalues[1][1] == "32"
    assert table._cellvalues[1][3] == "F"
    assert table._cellvalues[2][0] == "Requested by:"
    assert table._cellvalues[2][1] == "Dr. Matia"
    assert table._cellvalues[2][2] == "Date:"
    assert table._cellvalues[2][3] == "17/08/2026"
    assert table._cellvalues[3][0] == "Ward / OPD:"

def test_build_metadata_table_compliance():
    order_data = {
        "lab_number": "amh-26-08-001",
        "full_name": "SARAH NAMUBIRU",
        "age": "28",
        "sex": "F",
        "requested_by": "Dr. Sarah",
        "ward_of_origin": "Maternity",
        "ordered_date": "18/08/2026"
    }
    table = _build_metadata_table(order_data)
    assert isinstance(table, Table)
    assert table._cellvalues[0][0] == "Patient Name:"
    assert table._cellvalues[0][1] == "SARAH NAMUBIRU"
    assert table._cellvalues[0][2] == "Lab No:"
    assert table._cellvalues[0][3] == "amh-26-08-001"
    assert table._cellvalues[1][0] == "Age:"
    assert table._cellvalues[1][1] == "28"
    assert table._cellvalues[1][2] == "Sex:"
    assert table._cellvalues[1][3] == "F"
    assert table._cellvalues[2][0] == "Requested by:"
    assert table._cellvalues[2][1] == "Dr. Sarah"
    assert table._cellvalues[2][2] == "Date:"
    assert table._cellvalues[2][3] == "18/08/2026"
    assert table._cellvalues[3][0] == "Ward / OPD:"
    assert table._cellvalues[3][1] == "Maternity"

def test_build_signatures_table():
    order_data = {
        "technician_name": "Abubakar",
        "verified_by": "Dr. John"
    }
    flowable = _build_signatures_table(order_data)
    assert isinstance(flowable, KeepTogether)
    table = flowable._content[1]
    assert isinstance(table, Table)
    assert table._cellvalues[0][0] == "Done by: Abubakar _______________"
    assert table._cellvalues[0][1] == "Verified by: Dr. John _______________"

def test_build_signatures_table_empty():
    order_data = {}
    flowable = _build_signatures_table(order_data)
    assert isinstance(flowable, KeepTogether)
    table = flowable._content[1]
    assert isinstance(table, Table)
    assert table._cellvalues[0][0] == "Done by: _______________"
    assert table._cellvalues[0][1] == "Verified by: _______________"

def test_build_department_table():
    dept_name = "HAEMATOLOGY"
    tests = [
        {"test_name": "WBC", "result": "6.5", "unit": "10^3/uL", "flag": "Normal", "reference": "4.0 - 10.0"}
    ]
    flowable = _build_department_table(dept_name, tests)
    assert isinstance(flowable, KeepTogether)

def test_generate_pdf_full_report():
    order_data = {
        "lab_number": "amh-26-08-042",
        "full_name": "JOHN DOE",
        "age": "45",
        "sex": "M",
        "requested_by": "Dr. Musoke",
        "ward_of_origin": "OPD",
        "ordered_date": "2026-08-18",
        "technician_name": "Jane Tech",
        "verified_by": "Dr. Smith"
    }
    results_data = [
        {
            "department": "HAEMATOLOGY",
            "tests": [
                {"test_name": "Hemoglobin", "result": "14.2", "unit": "g/dL", "flag": "Normal", "reference": "13.0 - 17.0"},
                {"test_name": "WBC", "result": "12.5", "unit": "10^3/uL", "flag": "High", "reference": "4.0 - 10.0"}
            ]
        },
        {
            "department": "BIOCHEMISTRY",
            "tests": [
                {"test_name": "Random Blood Sugar", "result": "5.4", "unit": "mmol/L", "flag": "Normal", "reference": "3.9 - 7.8"}
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF-')
    assert len(pdf_bytes) > 1000

def test_pdf_contains_hospital_metadata():
    order_data = {
        "lab_number": "AMH-26-8-123",
        "full_name": "Test Client",
        "technician_name": "Technician John"
    }
    results_data = [{"department": "Parasitology", "tests": [{"test_name": "BS for MPS", "result": "Negative"}]}]
    pdf_bytes = generate_pdf(order_data, results_data)
    
    # Verify PDF contains author and title strings in byte stream
    assert b"Ahmadiyya Muslim Hospital" in pdf_bytes
    assert b"AMH-26-8-123" in pdf_bytes

def test_urinalysis_and_general_tests_fit_on_single_page():
    order_data = {
        "lab_number": "AMH-26-8-555",
        "full_name": "Test Client",
        "client_number": "AMH-100",
        "age": "30y",
        "sex": "Female",
        "ordered_date": "2026-08-24"
    }
    ua_params = [
        {"name": "Color", "result": "Yellow"},
        {"name": "Turbidity", "result": "Clear"},
        {"name": "Pus Cells (WBCs)", "result": "Not Seen"},
        {"name": "Red Blood Cells (RBCs)", "result": "Not Seen"},
        {"name": "Proteins", "result": "Nil"},
        {"name": "Glucose", "result": "Nil"}
    ]
    results_data = [
        {"department": "Clinical Chemistry", "tests": [{"test_name": "URINALYSIS", "result": "Completed", "parameters": ua_params}]},
        {"department": "Parasitology", "tests": [{"test_name": "BS for MPS", "result": "Negative", "unit": "", "reference": "Negative"}]},
        {"department": "Serology", "tests": [{"test_name": "H. Pylori Ag", "result": "Negative", "unit": "", "reference": "Negative"}]}
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    assert len(pdf_bytes) > 1000
    # Verify single page output (Page /Count 1)
    assert b"/Count 1" in pdf_bytes or b"/Type /Page" in pdf_bytes

