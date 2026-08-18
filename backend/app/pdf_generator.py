import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

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

def _build_metadata_table(order_data: dict) -> Table:
    data = [
        ["Patient Name:", order_data.get("full_name", ""), "Lab No:", order_data.get("client_number", "")],
        ["Age:", order_data.get("age", ""), "Sex:", order_data.get("sex", "")],
        ["Referred By:", order_data.get("ordered_by", ""), "Date:", order_data.get("ordered_date", "")],
        ["Verified By:", order_data.get("verified_by", ""), " ", " "]
    ]
    
    t = Table(data, colWidths=[80, 160, 80, 160])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), # Left labels
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'), # Right labels
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    return t

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
    
    flowables = []
    flowables.append(_build_metadata_table(order_data))
    flowables.append(Spacer(1, 20))
    
    doc.build(flowables, onFirstPage=_draw_background_hook, onLaterPages=_draw_background_hook)
    
    return buffer.getvalue()
