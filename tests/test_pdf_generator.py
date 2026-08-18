import io
import pytest
from backend.app.pdf_generator import generate_pdf, _build_metadata_table
from reportlab.platypus import Table

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
