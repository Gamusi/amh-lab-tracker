import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
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
    lab_no = order_data.get("lab_number") or order_data.get("client_number", "")
    requested_by = order_data.get("requested_by") or order_data.get("ordered_by", "")
    date_val = order_data.get("ordered_date") or order_data.get("date", "")
    ward = order_data.get("ward_of_origin", "")
    
    data = [
        ["Patient Name:", str(order_data.get("full_name") or ""), "Lab No:", str(lab_no)],
        ["Age:", str(order_data.get("age") or ""), "Sex:", str(order_data.get("sex") or "")],
        ["Requested by:", str(requested_by), "Date:", str(date_val)],
        ["Ward / OPD:", str(ward), "", ""]
    ]
    
    t = Table(data, colWidths=[90, 150, 80, 160])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), # Left labels
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'), # Right labels
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    return t

def _build_department_table(dept_name: str, tests: list) -> KeepTogether:
    # 5-column layout: Test (140), Result (80), Unit (60), Flag (60), Reference (140)
    data = []
    
    internal_categories = ["Main", "Referrals", "Out-Reaches"]
    show_dept = dept_name not in internal_categories
    
    if show_dept:
        data.append([dept_name, "", "", "", ""])
        
    data.append(["Test", "Result", "Unit", "Flag", "Reference"])
    
    result_style = ParagraphStyle(name="ResultStyle", fontName="Helvetica", fontSize=10, leading=12)
    
    for t in tests:
        res_text = str(t.get("result") or "")
        res_para = Paragraph(res_text, result_style) if res_text else ""
        data.append([
            t.get("test_name", ""),
            res_para,
            t.get("unit", ""),
            t.get("flag", ""),
            t.get("reference", "")
        ])
        
    t = Table(data, colWidths=[140, 80, 60, 60, 140])
    
    style_cmds = [
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]
    
    header_row_idx = 1 if show_dept else 0
    if show_dept:
        style_cmds.append(('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'))
        style_cmds.append(('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')))
        style_cmds.append(('SPAN', (0,0), (-1,0)))
        
    style_cmds.append(('FONTNAME', (0, header_row_idx), (-1, header_row_idx), 'Helvetica-Bold'))
    style_cmds.append(('LINEBELOW', (0, header_row_idx), (-1, header_row_idx), 1, colors.black))
    
    t.setStyle(TableStyle(style_cmds))
    
    return KeepTogether([t, Spacer(1, 15)])

def _build_signatures_table(order_data: dict) -> KeepTogether:
    tech = str(order_data.get("technician_name") or "").strip()
    verified = str(order_data.get("verified_by") or "").strip()
    
    done_str = f"Done by: {tech} _______________" if tech else "Done by: _______________"
    verified_str = f"Verified by: {verified} _______________" if verified else "Verified by: _______________"
    
    data = [
        [done_str, verified_str]
    ]
    
    t = Table(data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    return KeepTogether([Spacer(1, 15), t])

def _build_urinalysis_table(urinalysis_test: dict) -> KeepTogether:
    data = [["Urinalysis Parameters", "Result"]]
    
    result_str = str(urinalysis_test.get("result") or "")
    
    # Try parsing result_str as a multiline or comma separated if it's plain text
    import json
    params = []
    try:
        parsed = json.loads(result_str)
        if isinstance(parsed, dict):
            for k, v in parsed.items():
                params.append([k, v])
        else:
            params.append(["Result", result_str])
    except Exception:
        # Fallback if not JSON
        if "\n" in result_str:
            lines = result_str.split("\n")
            for line in lines:
                if ":" in line:
                    k, v = line.split(":", 1)
                    params.append([k.strip(), v.strip()])
                else:
                    params.append(["", line.strip()])
        elif "," in result_str and ":" in result_str:
            parts = result_str.split(",")
            for p in parts:
                if ":" in p:
                    k, v = p.split(":", 1)
                    params.append([k.strip(), v.strip()])
        else:
            params.append(["Result", result_str])
            
    if not params:
        params.append(["Result", result_str])
        
    data.extend(params)
    
    t = Table(data, colWidths=[240, 240]) # Full width = 480
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
    ]))
    return KeepTogether([t, Spacer(1, 15)])

def _build_cbc_table(order_data: dict, cbc_test: dict) -> list:
    # Build distinct sections exactly matching the clinical reporting standard:
    # 1. Main Indices (WBC, RBC, Hb, HCT, MCV, MCH, MCHC, PLT)
    # 2. Differential Relative (%)
    # 3. Differential Absolute (10^9 / uL)
    # 4. RBC / Platelet Indices (RDW, PCT, MPV, PDW)
    flowables = []
    
    title_style = ParagraphStyle(
        name='CBCTitle',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    # Title box with border
    header_table = Table([[Paragraph("HAEMATOLOGY CBC REPORT", title_style)]], colWidths=[480])
    header_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    flowables.append(header_table)
    flowables.append(Spacer(1, 8))
    
    params = cbc_test.get("parameters", [])
    params_map = {p.get("name", "").strip().lower(): p for p in params}

    def get_row(name, display_name, def_unit, def_ref):
        match = None
        for k, v in params_map.items():
            if name.lower() in k:
                match = v
                break
        res_val = match.get("result", "") if match else ""
        unit_val = match.get("unit", def_unit) if match else def_unit
        flag_val = match.get("flag", "") if match else ""
        ref_val = match.get("reference", def_ref) if match else def_ref
        
        # Format flag: Low, High, *, etc.
        flag_display = ""
        if flag_val:
            if flag_val == "L": flag_display = "Low"
            elif flag_val == "H": flag_display = "High"
            elif flag_val == "*": flag_display = "Panic *"
            else: flag_display = str(flag_val)

        return [display_name, str(res_val), str(unit_val or ""), flag_display, f"[ {ref_val} ]" if ref_val else ""]

    # Section 1: Main Indices
    sec1 = [
        get_row("Total WBC Count", "Total WBC Count", "(10^3 / uL)", "6.0-14.0"),
        get_row("Red Blood Cells", "Red Blood Cells (RBC)", "(10^6 / uL)", "4.00 -5.20"),
        get_row("Hemoglobin", "Hemoglobin (Hb)", "g/dL", "11.5-15.5"),
        get_row("Hematocrit", "Hematocrit (HCT)", "%", "35.0-45.0"),
        get_row("Mean Cell Volume", "Mean Cell Volume (MCV)", "fL", "77.0-95.0"),
        get_row("Mean Cell Hb (MCH)", "Mean Cell Hb (MCH)", "pg", "23.0-31.0"),
        get_row("Mean Cell Hb Conc", "Mean Cell Hb Conc.(MCHC)", "g/dL", "28.0-33.0"),
        get_row("Platelets Count", "Platelets Count", "(10^3 / uL)", "150-400"),
    ]

    # Section 2: Differential Relative (%)
    sec2 = [
        get_row("Neutrophils (%)", "Neutrophils", "%", "40.0-65.0"),
        get_row("Lymphocytes (%)", "Lymphocytes", "%", "19.2-49.5"),
        get_row("Monocytes (%)", "Monocytes", "%", "4.5-12.1"),
        get_row("Eosinophils (%)", "Eosinophils", "%", "1.0-12.0"),
        get_row("Basophils (%)", "Basophils", "%", "0.0-1.0"),
    ]

    # Section 3: Differential Absolute
    sec3 = [
        get_row("Neutrophils (Absolute", "Neutrophils Count", "(10^9 / uL)", "2.00-6.00"),
        get_row("Lymphocytes (Absolute", "Lymphocytes Count", "(10^9 / uL)", "5.00-8.50"),
        get_row("Monocytes (Absolute", "Monocytes Count", "(10^9 / uL)", "0.70-1.50"),
        get_row("Eosinophils (Absolute", "Eosinophils Count", "(10^9 / uL)", "0.30-0.80"),
        get_row("Basophils (Absolute", "Basophils Count", "(10^9 / uL)", "0.0-0.5"),
    ]

    # Section 4: RBC / Platelet Indices
    sec4 = [
        get_row("RBC Distribution Width", "RBC Distribution Width", "%", "11.0-16.0"),
        get_row("Thrombocrit", "Thrombocrit (PCT)", "%", "0.16-0.33"),
        get_row("Mean Platelet Volume", "Mean Platelet Volume (MPV)", "fL", "6.0 - 10.0"),
        get_row("PLT Distribution Width", "Plt Distribution Width", "%", "12.0 - 18.0"),
    ]

    table_data = [
        ["Test", "Result", "Units", "Flag", "Ref. Ranges"]
    ]
    
    divider = ["-", "", "", "", ""]

    table_data.extend(sec1)
    table_data.append(divider)
    table_data.extend(sec2)
    table_data.append(divider)
    table_data.extend(sec3)
    table_data.append(divider)
    table_data.extend(sec4)

    t = Table(table_data, colWidths=[150, 65, 85, 60, 120])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,1), (1,-1), 'RIGHT'),
        ('ALIGN', (3,1), (3,-1), 'CENTER'),
        ('ALIGN', (4,1), (4,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('FONTNAME', (1,1), (1,-1), 'Helvetica-Bold'),
    ]))
    
    flowables.append(t)
    flowables.append(Spacer(1, 10))
    return flowables

from reportlab.platypus import PageBreak

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
    
    title_style = ParagraphStyle(
        name='ReportTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    flowables = []
    
    # Check for CBC
    cbc_test = None
    other_departments = []
    
    for dept_data in results_data:
        dept_name = dept_data.get("department", "UNKNOWN")
        tests = dept_data.get("tests", [])
        
        filtered_tests = []
        for t in tests:
            t_name = str(t.get("test_name") or "").lower()
            if "cbc" in t_name or "complete blood count" in t_name:
                cbc_test = t
            else:
                filtered_tests.append(t)
                
        if filtered_tests:
            other_departments.append({"department": dept_name, "tests": filtered_tests})

    # If we have other tests, render main report page first
    if other_departments or not cbc_test:
        flowables.append(Paragraph("Laboratory Report", title_style))
        flowables.append(Spacer(1, 12))
        flowables.append(_build_metadata_table(order_data))
        flowables.append(Spacer(1, 15))
        
        urinalysis_test = None
        for dept_data in other_departments:
            dept_name = dept_data.get("department", "UNKNOWN")
            tests = dept_data.get("tests", [])
            
            # Group orders by test_name (proxy for test_id)
            grouped_tests = {}
            for t in tests:
                t_name = t.get("test_name", "")
                if t_name not in grouped_tests:
                    grouped_tests[t_name] = []
                grouped_tests[t_name].append(t)
                
            final_tests = []
            for t_name, orders in grouped_tests.items():
                valid_orders = [o for o in orders if str(o.get("result") or "").lower() != "invalid"]
                if valid_orders:
                    final_tests.extend(valid_orders)
                else:
                    first_order = orders[0].copy()
                    first_order["result"] = "Not done"
                    final_tests.append(first_order)
                    
            tests_to_render = []
            for t in final_tests:
                if str(t.get("test_name") or "").lower() == "urinalysis":
                    urinalysis_test = t
                else:
                    tests_to_render.append(t)
                    
            if tests_to_render:
                flowables.append(_build_department_table(dept_name, tests_to_render))
                
        if urinalysis_test:
            flowables.append(_build_urinalysis_table(urinalysis_test))
            
        flowables.append(_build_signatures_table(order_data))
        
        if cbc_test:
            flowables.append(PageBreak())

    # Render dedicated CBC page if present
    if cbc_test:
        flowables.append(_build_metadata_table(order_data))
        flowables.append(Spacer(1, 10))
        flowables.extend(_build_cbc_table(order_data, cbc_test))
        flowables.append(_build_signatures_table(order_data))
    
    doc.build(flowables, onFirstPage=_draw_background_hook, onLaterPages=_draw_background_hook)
    
    return buffer.getvalue()

generate_report_pdf = generate_pdf


