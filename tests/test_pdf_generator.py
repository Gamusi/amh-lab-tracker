import io
import pytest
from backend.app.pdf_generator import generate_pdf, _build_metadata_table, _build_department_table
from reportlab.platypus import Table, KeepTogether

def test_generate_pdf_creates_bytes():
    order_data = {"client_number": "102", "full_name": "JOHN DOE", "sex": "M", "age": "30"}
    results_data = []
    pdf_bytes = generate_pdf(order_data, results_data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF-')

def test_build_metadata_table():
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

def test_build_department_table():
    dept_name = "HAEMATOLOGY"
    tests = [
        {"test_name": "WBC", "result": "6.5", "unit": "10^3/uL", "flag": "Normal", "reference": "4.0 - 10.0"}
    ]
    flowable = _build_department_table(dept_name, tests)
    assert isinstance(flowable, KeepTogether)
