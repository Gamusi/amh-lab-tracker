import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from . import evaluator

PAGE_WIDTH, PAGE_HEIGHT = A4
SAFE_MARGIN_X = 56.69
SAFE_WINDOW_Y = 600.95

FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_SYMBOL = 'Helvetica'

def _init_fonts():
    global FONT_REGULAR, FONT_BOLD, FONT_SYMBOL
    fonts_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts")
    )
    segoe_path = os.path.join(fonts_dir, "segoeui.ttf")
    segoe_bold_path = os.path.join(fonts_dir, "segoeuib.ttf")
    symbol_path = os.path.join(fonts_dir, "seguisym.ttf")
    
    if not os.path.exists(symbol_path) and os.path.exists(r"C:\Windows\Fonts\seguisym.ttf"):
        symbol_path = r"C:\Windows\Fonts\seguisym.ttf"
    if not os.path.exists(segoe_path) and os.path.exists(r"C:\Windows\Fonts\segoeui.ttf"):
        segoe_path = r"C:\Windows\Fonts\segoeui.ttf"
    if not os.path.exists(segoe_bold_path) and os.path.exists(r"C:\Windows\Fonts\segoeuib.ttf"):
        segoe_bold_path = r"C:\Windows\Fonts\segoeuib.ttf"
        
    try:
        if os.path.exists(symbol_path):
            pdfmetrics.registerFont(TTFont('SegoeUISymbol', symbol_path))
            FONT_SYMBOL = 'SegoeUISymbol'
        if os.path.exists(segoe_path):
            pdfmetrics.registerFont(TTFont('SegoeUI', segoe_path))
            FONT_REGULAR = 'SegoeUI'
        if os.path.exists(segoe_bold_path):
            pdfmetrics.registerFont(TTFont('SegoeUIBold', segoe_bold_path))
            FONT_BOLD = 'SegoeUIBold'
    except Exception:
        pass

_init_fonts()

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
        ('FONTNAME', (0,0), (-1,-1), FONT_REGULAR),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), FONT_BOLD), # Left labels
        ('FONTNAME', (2,0), (2,-1), FONT_BOLD), # Right labels
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
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
    
    result_style = ParagraphStyle(name="ResultStyle", fontName=FONT_REGULAR, fontSize=9, leading=11)
    flag_center_style = ParagraphStyle(name="FlagCenterStyle", fontName=FONT_BOLD, fontSize=9, leading=11, alignment=TA_CENTER)
    
    for t in tests:
        res_text = str(t.get("result") or "")
        res_para = Paragraph(res_text, result_style) if res_text else ""
        flag_text = str(t.get("flag") or "")
        t_name = str(t.get("test_name") or "")
        if not flag_text and evaluator.is_qualitative_abnormal(res_text, str(t.get("reference") or ""), param_name=t_name):
            flag_text = "\u26A0"
        if flag_text == "[!]":
            flag_text = "\u26A0"

        if flag_text == "\u26A0":
            if FONT_SYMBOL != 'Helvetica':
                flag_cell = Paragraph(f'<font name="{FONT_SYMBOL}" color="#dc2626">\u26A0</font>', flag_center_style)
            else:
                flag_cell = Paragraph('<font color="#dc2626"><b>\u26A0</b></font>', flag_center_style)
        else:
            flag_cell = flag_text

        data.append([
            t_name,
            res_para,
            t.get("unit", ""),
            flag_cell,
            t.get("reference", "")
        ])
        
    t = Table(data, colWidths=[140, 80, 60, 60, 140])
    
    style_cmds = [
        ('FONTNAME', (0,0), (-1,-1), FONT_REGULAR),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (3,0), (3,-1), 'CENTER'),
        ('TEXTCOLOR', (3,0), (3,-1), colors.HexColor('#dc2626')),
        ('FONTNAME', (3,0), (3,-1), FONT_BOLD),
    ]
    
    for i, test in enumerate(tests):
        flag = test.get("flag", "")
        res_t = str(test.get("result") or "")
        t_name = str(test.get("test_name") or "")
        if flag in ["High", "Low", "Abnormal", "Reactive", "Positive", "H", "L", "H*", "L*", "*", "\u26A0", "[!]"] or evaluator.is_qualitative_abnormal(res_t, str(test.get("reference") or ""), param_name=t_name):
            row_idx = i + (2 if show_dept else 1)
            style_cmds.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), colors.HexColor('#dc2626')))
            style_cmds.append(('FONTNAME', (1, row_idx), (1, row_idx), FONT_BOLD))
    
    header_row_idx = 1 if show_dept else 0
    if show_dept:
        style_cmds.append(('FONTNAME', (0,0), (-1,0), FONT_BOLD))
        style_cmds.append(('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')))
        style_cmds.append(('SPAN', (0,0), (-1,0)))
        
    style_cmds.append(('FONTNAME', (0, header_row_idx), (-1, header_row_idx), FONT_BOLD))
    style_cmds.append(('LINEBELOW', (0, header_row_idx), (-1, header_row_idx), 1, colors.black))
    
    t.setStyle(TableStyle(style_cmds))
    
    return KeepTogether([t, Spacer(1, 10)])

def _build_signatures_table(order_data: dict, compact: bool = False) -> KeepTogether:
    tech = str(order_data.get("technician_name") or "").strip()
    verified = str(order_data.get("verified_by") or "").strip()
    
    done_str = f"Done by: {tech} _______________" if tech else "Done by: _______________"
    verified_str = f"Verified by: {verified} _______________" if verified else "Verified by: _______________"
    
    data = [
        [done_str, verified_str]
    ]
    
    t = Table(data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), FONT_BOLD),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    spacer_h = 6 if compact else 12
    return KeepTogether([Spacer(1, spacer_h), t])


def _clean_urinalysis_name(name: str) -> str:
    name_str = str(name).strip()
    if "(" in name_str and ")" in name_str:
        base = name_str.split("(")[0].strip()
        if base.lower() in ["proteins", "glucose", "bilirubin", "ketones", "blood", "nitrates", "nitrate", "leukocytes", "leukocyte esterase"]:
            if base.lower() in ["nitrates", "nitrate"]:
                return "Nitrate"
            if base.lower() in ["leukocytes", "leukocyte esterase"]:
                return "Leukocyte Esterase"
            return base
    return name_str


def _build_urinalysis_table(urinalysis_test: dict) -> KeepTogether:
    items = []
    ua_p_style = ParagraphStyle(name="UaParaStyle", fontName=FONT_REGULAR, fontSize=7.5, leading=9)
    
    if urinalysis_test.get("parameters"):
        for p in urinalysis_test["parameters"]:
            pname = _clean_urinalysis_name(p.get("name") or p.get("parameter_name") or "")
            pres = p.get("result") if p.get("result") is not None else p.get("result_value", "")
            
            pflag = p.get("flag") or ("\u26A0" if p.get("is_positive") else "")
            if not pflag and evaluator.is_qualitative_abnormal(str(pres), param_name=pname):
                pflag = "\u26A0"
            if pflag == "[!]":
                pflag = "\u26A0"

            if pflag == "\u26A0":
                if FONT_SYMBOL != 'Helvetica':
                    pres_cell = Paragraph(f'{pres} <font name="{FONT_SYMBOL}" color="#dc2626">\u26A0</font>', ua_p_style)
                else:
                    pres_cell = Paragraph(f'{pres} <font color="#dc2626"><b>\u26A0</b></font>', ua_p_style)
            else:
                pres_cell = str(pres)

            items.append((str(pname), pres_cell))
    else:
        result_str = str(urinalysis_test.get("result") or "")
        import json
        raw_items = []
        try:
            parsed = json.loads(result_str)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    raw_items.append((str(k), str(v)))
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        raw_items.append((str(item.get("name", "")), str(item.get("result", ""))))
            else:
                raw_items.append(("Result", result_str))
        except Exception:
            if "\n" in result_str:
                lines = result_str.split("\n")
                for line in lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        raw_items.append((k.strip(), v.strip()))
                    else:
                        raw_items.append(("", line.strip()))
            elif "," in result_str and ":" in result_str:
                parts = result_str.split(",")
                for p in parts:
                    if ":" in p:
                        k, v = p.split(":", 1)
                        raw_items.append((k.strip(), v.strip()))
            else:
                raw_items.append(("Result", result_str))

        for k, v in raw_items:
            clean_k = _clean_urinalysis_name(k)
            flag = "\u26A0" if evaluator.is_qualitative_abnormal(str(v), param_name=clean_k) else ""
            if flag == "\u26A0":
                if FONT_SYMBOL != 'Helvetica':
                    v_cell = Paragraph(f'{v} <font name="{FONT_SYMBOL}" color="#dc2626">\u26A0</font>', ua_p_style)
                else:
                    v_cell = Paragraph(f'{v} <font color="#dc2626"><b>\u26A0</b></font>', ua_p_style)
            else:
                v_cell = str(v)
            items.append((str(clean_k), v_cell))

    if not items:
        items = [("Result", str(urinalysis_test.get("result") or ""))]

    n = len(items)
    half = (n + 1) // 2
    col1 = items[:half]
    col2 = items[half:]

    data = [
        ["Urinalysis", "", "", ""],
        ["Parameter", "Result", "Parameter", "Result"]
    ]

    for i in range(half):
        p1, r1 = col1[i]
        p2, r2 = col2[i] if i < len(col2) else ("", "")
        data.append([p1, r1, p2, r2])

    t = Table(data, colWidths=[145, 95, 145, 95])
    t.setStyle(TableStyle([
        ('SPAN', (0,0), (3,0)),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 8),
        ('LINEBELOW', (0,1), (-1,1), 0.8, colors.black),
        ('FONTNAME', (0,2), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,2), (-1,-1), 7.5),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('GRID', (0,1), (-1,-1), 0.3, colors.HexColor('#d0d0d0')),
    ]))
    return KeepTogether([t, Spacer(1, 10)])

def _build_cbc_patient_header(order_data: dict) -> Table:
    client_no = str(order_data.get("client_number") or order_data.get("client_id") or "")
    date_val = str(order_data.get("ordered_date") or order_data.get("date") or "")
    if "-" in date_val:
        parts = date_val.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            date_val = f"{parts[1]}/{parts[2]}/{parts[0]}"
            
    ref_by = str(order_data.get("requested_by") or order_data.get("ordered_by") or "")
    name = str(order_data.get("full_name") or "")
    age = str(order_data.get("age") or "")
    sex = str(order_data.get("sex") or "")
    if sex.lower().startswith("m"):
        sex = "M"
    elif sex.lower().startswith("f"):
        sex = "F"
    lab_no = str(order_data.get("lab_number") or "")
    ward = str(order_data.get("ward_of_origin") or "OPD")
    
    data = [
        ["Client No :", client_no, "Name :", name, "Lab No :", lab_no],
        ["Dated     :", date_val, "Age  :", age, "Ward/OPD :", ward],
        ["Ref. By   :", ref_by, "Sex  :", sex, "Specimen :", "Blood"]
    ]
    
    t = Table(data, colWidths=[70, 95, 45, 135, 70, 65])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), 'Courier-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Courier-Bold'),
        ('FONTNAME', (4,0), (4,-1), 'Courier-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    return t

def _normalize_unit(unit_str: str) -> str:
    if not unit_str:
        return ""
    u = unit_str.strip()
    u = u.replace("10³", "10^3").replace("10⁶", "10^6").replace("10⁹", "10^9")
    u = u.replace("µL", "uL").replace("μL", "uL")
    if "10^3" in u and "(" not in u:
        return "(10^3 / uL)"
    if "10^6" in u and "(" not in u:
        return "(10^6 / uL)"
    if "10^9" in u and "(" not in u:
        return "(10^9 / uL)"
    return u

def _build_cbc_footer(order_data: dict, cbc_test: dict) -> Table:
    time_str = ""
    date_str = str(order_data.get("ordered_date") or order_data.get("date") or "")
    if "-" in date_str:
        parts = date_str.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            date_str = f"{parts[1]}/{parts[2]}/{parts[0]}"
            
    timestamp = cbc_test.get("timestamp") or order_data.get("analyzer_timestamp") or ""
    if timestamp and " " in timestamp:
        t_parts = timestamp.split(" ")
        time_str = t_parts[1]
    elif timestamp:
        time_str = timestamp
    else:
        time_str = "12:00:00"
        
    tech = str(order_data.get("technician_name") or "").strip()
    if tech and tech.lower() not in ["technologist signature", "technologist", "signature"]:
        sig_label = f"Technologist Signature ({tech})"
    else:
        sig_label = "Technologist Signature"
    
    data = [
        [time_str, date_str, sig_label]
    ]
    t = Table(data, colWidths=[100, 140, 240])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    return t

def _build_cbc_table(order_data: dict, cbc_test: dict) -> list:
    flowables = []
    
    # Title box with border
    header_table = Table([[Paragraph("HAEMATOLOGY CBC REPORT", ParagraphStyle(
        name='CBCTitle',
        fontName='Courier-Bold',
        fontSize=10.5,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.black
    ))]], colWidths=[480])
    header_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    flowables.append(header_table)
    flowables.append(Spacer(1, 4))
    
    params = cbc_test.get("parameters", [])
    params_map = {}
    for p in params:
        p_name = (p.get("name") or p.get("test_name") or "").strip().lower()
        if p_name:
            params_map[p_name] = p

    # Determine demographic category (Child vs Adult)
    age_str = str(order_data.get("age") or "").lower()
    is_child = False
    if "m" in age_str or "d" in age_str:
        is_child = True
    else:
        digits = "".join([c for c in age_str if c.isdigit()])
        if digits and int(digits) < 18:
            is_child = True
    demo_category = "Child" if is_child else "Adult"

    def get_row(name_matcher, display_name, def_unit, def_ref):
        match = None
        for k, v in params_map.items():
            if name_matcher.lower() in k:
                match = v
                break
        res_val = match.get("result", match.get("value", "")) if match else ""
        raw_unit = match.get("unit", def_unit) if match else def_unit
        unit_val = _normalize_unit(raw_unit)
        flag_val = match.get("flag", "") if match else ""
        ref_val = match.get("reference_range") or match.get("reference") or def_ref if match else def_ref
        
        # Format flag: Low, High, \u26A0, L*, H*
        flag_display = ""
        if flag_val:
            if flag_val in ("\u26A0", "[!]", "*"):
                if FONT_SYMBOL != 'Helvetica':
                    flag_display = Paragraph(f'<font name="{FONT_SYMBOL}" color="#dc2626">\u26A0</font>', ParagraphStyle(name="CbcFlagSym", fontName=FONT_BOLD, fontSize=8, alignment=TA_CENTER))
                else:
                    flag_display = Paragraph('<font color="#dc2626"><b>\u26A0</b></font>', ParagraphStyle(name="CbcFlagSym", fontName=FONT_BOLD, fontSize=8, alignment=TA_CENTER))
            elif flag_val in ("L*", "Low*"): flag_display = "L*"
            elif flag_val in ("H*", "High*"): flag_display = "H*"
            elif flag_val in ("L", "Low", "l"): flag_display = "Low"
            elif flag_val in ("H", "High", "h"): flag_display = "High"
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
        ["", "", "", "", demo_category],
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

    t = Table(table_data, colWidths=[160, 55, 75, 50, 140])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,1), (-1,1), 'Courier-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 8.5),
        ('FONTNAME', (4,0), (4,0), 'Courier-Bold'),
        ('ALIGN', (4,0), (4,0), 'CENTER'),
        ('LINEBELOW', (0,1), (-1,1), 1, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,2), (1,-1), 'RIGHT'),
        ('ALIGN', (2,2), (2,-1), 'CENTER'),
        ('ALIGN', (3,2), (3,-1), 'CENTER'),
        ('ALIGN', (4,2), (4,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.6),
        ('TOPPADDING', (0,0), (-1,-1), 1.6),
        ('FONTNAME', (1,2), (1,-1), 'Courier-Bold'),
    ]))
    
    flowables.append(t)
    flowables.append(Spacer(1, 8))
    return flowables


from reportlab.platypus import PageBreak

def generate_pdf(order_data: dict, results_data: list) -> bytes:
    buffer = io.BytesIO()
    lab_no = order_data.get("lab_number") or order_data.get("client_number") or ""
    client_name = order_data.get("full_name") or ""
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        leftMargin=SAFE_MARGIN_X, 
        rightMargin=SAFE_MARGIN_X, 
        topMargin=145,
        bottomMargin=65,
        title=f"Lab Report - {lab_no}",
        author="Ahmadiyya Muslim Hospital, Mbale",
        creator="AMH Lab Tracker",
        subject=f"Clinical Diagnostic Report: {client_name} ({lab_no})"
    )
    
    title_style = ParagraphStyle(
        name='ReportTitle',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    flowables = []
    
    # Check for CBC
    cbc_test = None
    cbc_params_collected = []
    other_departments = []
    
    cbc_param_keywords = [
        "wbc", "rbc", "hemoglobin", "hb", "hematocrit", "hct", "mcv", "mch", "mchc", "rdw",
        "platelet", "plt", "pct", "mpv", "pdw", "neutrophil", "lymphocyte", "monocyte", "eosinophil", "basophil"
    ]
    
    for dept_data in results_data:
        dept_name = dept_data.get("department", "UNKNOWN")
        tests = dept_data.get("tests", [])
        
        filtered_tests = []
        for t in tests:
            t_name = str(t.get("test_name") or "").lower()
            if "cbc" in t_name or "complete blood count" in t_name:
                cbc_test = t
            elif any(k in t_name for k in cbc_param_keywords):
                cbc_params_collected.append(t)
            else:
                filtered_tests.append(t)
                
        if filtered_tests:
            other_departments.append({"department": dept_name, "tests": filtered_tests})

    # If CBC test exists or child params collected, ensure parameters array is complete
    if cbc_test or cbc_params_collected:
        if not cbc_test:
            cbc_test = {"test_name": "Complete Blood Count (CBC)", "parameters": []}
        
        existing_params = cbc_test.get("parameters", [])
        if not existing_params and cbc_params_collected:
            cbc_test["parameters"] = cbc_params_collected

    # If we have other tests, render main report page first
    if other_departments or not cbc_test:
        flowables.append(Paragraph("Laboratory Report", title_style))
        flowables.append(Spacer(1, 8))
        flowables.append(_build_metadata_table(order_data))
        flowables.append(Spacer(1, 10))
        
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
        flowables.append(_build_cbc_patient_header(order_data))
        flowables.append(Spacer(1, 6))
        flowables.extend(_build_cbc_table(order_data, cbc_test))
        flowables.append(_build_cbc_footer(order_data, cbc_test))
    
    doc.build(flowables, onFirstPage=_draw_background_hook, onLaterPages=_draw_background_hook)
    
    return buffer.getvalue()

generate_report_pdf = generate_pdf




