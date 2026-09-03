import io
from backend.app.pdf_generator import generate_pdf

def test_cd4_pdf_generation_ahd():
    order_data = {
        "client_number": "CD4-PDF-001",
        "full_name": "SARAH NAMUKASA",
        "age": "32y",
        "sex": "F",
        "lab_number": "MLIS-26-09-088",
        "ward_of_origin": "ART CLINIC",
        "specimen": "EDTA Whole Blood",
        "requested_by": "DR. OKELLO",
        "ordered_date": "2026-09-03",
        "technician_name": "NABIRYE GLORIA",
        "verified_by": "KATO PAUL"
    }
    results_data = [
        {
            "department": "Serology & Clinical Immunology",
            "tests": [
                {
                    "test_name": "Absolute CD4 Count (Cytometry)",
                    "result": "142",
                    "unit": "cells/µL",
                    "reference": "500 - 1500",
                    "flag": "L*"
                }
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 2000

def test_cd4_rdt_pdf_column_suppression():
    order_data = {
        "client_number": "CD4-PDF-002",
        "full_name": "MUSA KASOZI",
        "age": "28y",
        "sex": "M",
        "lab_number": "MLIS-26-09-089",
        "ward_of_origin": "OPD",
        "specimen": "Capillary Blood",
        "requested_by": "SELF REQUEST",
        "ordered_date": "2026-09-03",
        "technician_name": "NABIRYE GLORIA",
        "verified_by": "KATO PAUL"
    }
    results_data = [
        {
            "department": "Serology & Clinical Immunology",
            "tests": [
                {
                    "test_name": "CD4 Count (Rapid Test Strip)",
                    "result": "CD4 Count: Below 200 cells/µL",
                    "unit": "",
                    "reference": "",
                    "flag": "L*"
                }
            ]
        }
    ]
    pdf_bytes = generate_pdf(order_data, results_data)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 2000
