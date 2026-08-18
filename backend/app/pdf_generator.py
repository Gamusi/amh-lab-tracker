import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether
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

def _build_department_table(dept_name: str, tests: list) -> KeepTogether:
    # 5-column layout: Test (140), Result (80), Unit (60), Flag (60), Reference (140)
    data = [
        [dept_name, "", "", "", ""],
        ["Test", "Result", "Unit", "Flag", "Reference"]
    ]
    
    for t in tests:
        data.append([
            t.get("test_name", ""),
            t.get("result", ""),
            t.get("unit", ""),
            t.get("flag", ""),
            t.get("reference", "")
        ])
        
    t = Table(data, colWidths=[140, 80, 60, 60, 140])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'), 
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')), 
        ('SPAN', (0,0), (-1,0)), 
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,1), (-1,1), 1, colors.black), 
    ]))
    
    return KeepTogether([t, Spacer(1, 15)])

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
    
    for dept_data in results_data:
        dept_name = dept_data.get("department", "UNKNOWN")
        tests = dept_data.get("tests", [])
        flowables.append(_build_department_table(dept_name, tests))
    
    doc.build(flowables, onFirstPage=_draw_background_hook, onLaterPages=_draw_background_hook)
    
    return buffer.getvalue()
