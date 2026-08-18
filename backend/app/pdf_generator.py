import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

PAGE_WIDTH, PAGE_HEIGHT = A4
SAFE_MARGIN_X = 56.69
SAFE_WINDOW_Y = 600.95

def _draw_background_hook(canvas, doc):
    canvas.saveState()
    letterhead_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "branding", "letterhead.png")
    )
    if os.path.exists(letterhead_path):
        canvas.drawImage(letterhead_path, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT, mask='auto')
    canvas.restoreState()

def generate_pdf(order_data: dict, results_data: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        leftMargin=SAFE_MARGIN_X, 
        rightMargin=SAFE_MARGIN_X, 
        topMargin=200,
        bottomMargin=120
    )
    
    styles = getSampleStyleSheet()
    flowables = []
    flowables.append(Paragraph(f"Patient: {order_data.get('full_name', '')}", styles['Normal']))
    
    doc.build(flowables, onFirstPage=_draw_background_hook, onLaterPages=_draw_background_hook)
    
    return buffer.getvalue()
