import io
import pytest
from backend.app.pdf_generator import generate_pdf, _draw_background_hook, PAGE_WIDTH, PAGE_HEIGHT, SAFE_MARGIN_X, SAFE_WINDOW_Y

def test_generate_pdf_creates_bytes():
    order_data = {"client_number": "102", "full_name": "JOHN DOE", "sex": "M", "age": "30"}
    results_data = []
    pdf_bytes = generate_pdf(order_data, results_data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF-')
