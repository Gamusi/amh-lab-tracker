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

from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = A4
SAFE_MARGIN_X = 56.69
SAFE_WINDOW_Y = 600.95

FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_SYMBOL = 'Helvetica'

class ReportNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for dynamic total page count and professional 'Page X of Y' rendering.
    Draws letterhead background and page numbering dynamically across pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.letterhead_override = None

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        letterhead_path = self.letterhead_override or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "branding", "letterhead.png")
        )
        for state in self._saved_page_states:
            self.__dict__.update(state)
            page_num = self._pageNumber

            # 1. Background image
            if os.path.exists(letterhead_path):
                self.saveState()
                self.drawImage(letterhead_path, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT, mask='auto')
                self.restoreState()

            # 2. Dynamic footer page numbering (bottom right, above letterhead footer margin)
            self.saveState()
            self.setFont(FONT_REGULAR, 7.5)
            self.setFillColor(colors.HexColor('#64748B'))
            self.drawRightString(PAGE_WIDTH - SAFE_MARGIN_X, 18, f"Page {page_num} of {num_pages}")
            self.restoreState()

            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

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

def _draw_background_hook(canvas, doc, letterhead_override=None):
    canvas.saveState()
    letterhead_path = letterhead_override or os.path.abspath(
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
    specimen = order_data.get("specimen", "")
    
    data = [
        ["Client Name:", str(order_data.get("full_name") or ""), "Lab No:", str(lab_no)],
        ["Age:", str(order_data.get("age") or ""), "Sex:", str(order_data.get("sex") or "")],
        ["Requested by:", str(requested_by), "Date:", str(date_val)],
        ["Ward / OPD:", str(ward), "Specimen:", str(specimen)]
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

def _build_department_table(dept_name: str, tests: list, compact: bool = False) -> KeepTogether:
    # 5-column layout: Test (150), Result (75), Unit (60), Flag (55), Reference (140) = 480 pt total
    data = []
    
    internal_categories = ["Main", "Referrals", "Out-Reaches"]
    show_dept = dept_name not in internal_categories
    
    dept_title_style = ParagraphStyle(name="DeptTitleStyle", fontName=FONT_BOLD, fontSize=9, leading=11)
    tbl_header_style = ParagraphStyle(name="TblHeaderStyle", fontName=FONT_BOLD, fontSize=8.5, leading=10.5)
    panel_title_style = ParagraphStyle(name="PanelTitleStyle", fontName=FONT_BOLD, fontSize=8.5, leading=10.5)
    test_title_style = ParagraphStyle(name="TestTitleStyle", fontName=FONT_REGULAR, fontSize=8.5, leading=10.5)
    param_title_style = ParagraphStyle(name="ParamTitleStyle", fontName=FONT_REGULAR, fontSize=8.5, leading=10.5, leftIndent=8)
    unit_style = ParagraphStyle(name="UnitStyle", fontName=FONT_REGULAR, fontSize=8, leading=10)
    ref_style = ParagraphStyle(name="RefStyle", fontName=FONT_REGULAR, fontSize=8, leading=10)
    result_style = ParagraphStyle(name="ResultStyle", fontName=FONT_REGULAR, fontSize=8.5, leading=10.5)
    result_abnormal_style = ParagraphStyle(name="ResultAbnormalStyle", fontName=FONT_BOLD, fontSize=8.5, leading=10.5, textColor=colors.HexColor('#dc2626'))
    flag_center_style = ParagraphStyle(name="FlagCenterStyle", fontName=FONT_BOLD, fontSize=8.5, leading=10.5, alignment=TA_CENTER)
    
    # Determine if this department uses Units and Reference ranges
    has_any_units = False
    has_any_refs = False

    for t in tests:
        params = t.get("parameters")
        if params and len(params) > 0:
            for p in params:
                if str(p.get("unit") or "").strip():
                    has_any_units = True
                if str(p.get("reference_range") or p.get("reference") or "").strip():
                    has_any_refs = True
        else:
            if str(t.get("unit") or "").strip():
                has_any_units = True
            if str(t.get("reference") or t.get("reference_range") or "").strip():
                has_any_refs = True

    # Column configuration:
    # Full (Group I): Test(150), Result(75), Unit(60), Flag(55), Reference(140) = 480 pt
    # No Units, Has Ref (Group III): Test(180), Result(110), Flag(50), Reference(140) = 480 pt
    # No Units, No Ref (Group II): Test(250), Result(180), Flag(50) = 480 pt
    # Has Units, No Ref: Test(200), Result(120), Unit(100), Flag(60) = 480 pt

    if has_any_units and has_any_refs:
        layout_mode = 'FULL' # Group I
        col_widths = [150, 75, 60, 55, 140]
        headers = ["Test", "Result", "Unit", "Flag", "Reference"]
    elif not has_any_units and has_any_refs:
        layout_mode = 'NO_UNIT' # Group III (Semi-quantitative / Titers)
        col_widths = [180, 110, 50, 140]
        headers = ["Test", "Result", "Flag", "Reference / Cutoff"]
    elif not has_any_units and not has_any_refs:
        layout_mode = 'QUALITATIVE' # Group II (Descriptive / Qualitative)
        col_widths = [250, 180, 50]
        headers = ["Test", "Result", "Flag"]
    else:
        layout_mode = 'NO_REF'
        col_widths = [200, 120, 100, 60]
        headers = ["Test", "Result", "Unit", "Flag"]

    num_cols = len(col_widths)

    if show_dept:
        dept_row = [Paragraph(dept_name, dept_title_style)] + [""] * (num_cols - 1)
        data.append(dept_row)
        
    data.append([Paragraph(h, tbl_header_style) for h in headers])
    
    row_pad = 2.0 if compact else 3.5
    flag_col_idx = 3 if layout_mode == 'FULL' else (2 if layout_mode in ('NO_UNIT', 'QUALITATIVE') else 3)
    style_cmds = [
        ('FONTNAME', (0,0), (-1,-1), FONT_REGULAR),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('TOPPADDING', (0,0), (-1,-1), row_pad),
        ('BOTTOMPADDING', (0,0), (-1,-1), row_pad),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (flag_col_idx, 0), (flag_col_idx, -1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]

    for t in tests:
        params = t.get("parameters")
        if params and len(params) > 0:
            # Render Panel Subheader
            panel_name = str(t.get("test_name") or "")
            panel_row = [Paragraph(panel_name, panel_title_style)] + [""] * (num_cols - 1)
            data.append(panel_row)
            panel_row_idx = len(data) - 1
            style_cmds.append(('BACKGROUND', (0, panel_row_idx), (-1, panel_row_idx), colors.HexColor('#f8fafc')))
            style_cmds.append(('SPAN', (0, panel_row_idx), (-1, panel_row_idx)))

            for p in params:
                p_name = str(p.get("name") or p.get("parameter_name") or "")
                p_res = str(p.get("result") if p.get("result") is not None else p.get("result_value", ""))
                p_unit = str(p.get("unit") or "")
                p_ref = str(p.get("reference_range") or p.get("reference") or "")
                p_flag = str(p.get("flag") or "")

                if not p_flag and evaluator.is_qualitative_abnormal(p_res, p_ref, param_name=p_name):
                    p_flag = "\u26A0"
                if p_flag == "[!]":
                    p_flag = "\u26A0"

                if p_flag == "\u26A0":
                    if FONT_SYMBOL != 'Helvetica':
                        flag_cell = Paragraph(f'<font name="{FONT_SYMBOL}" color="#dc2626">\u26A0</font>', flag_center_style)
                    else:
                        flag_cell = Paragraph('<font color="#dc2626"><b>\u26A0</b></font>', flag_center_style)
                elif p_flag:
                    flag_cell = Paragraph(f'<font color="#dc2626">{p_flag}</font>', flag_center_style)
                else:
                    flag_cell = ""

                is_abnormal = p_flag in ["High", "Low", "Abnormal", "Reactive", "Positive", "H", "L", "H*", "L*", "*", "\u26A0", "[!]"] or evaluator.is_qualitative_abnormal(p_res, p_ref, param_name=p_name)
                res_para = Paragraph(p_res, result_abnormal_style if is_abnormal else result_style) if p_res else ""
                
                if layout_mode == 'FULL':
                    data.append([
                        Paragraph(p_name, param_title_style),
                        res_para,
                        Paragraph(p_unit, unit_style) if p_unit else "",
                        flag_cell,
                        Paragraph(p_ref, ref_style) if p_ref else ""
                    ])
                elif layout_mode == 'NO_UNIT':
                    data.append([
                        Paragraph(p_name, param_title_style),
                        res_para,
                        flag_cell,
                        Paragraph(p_ref, ref_style) if p_ref else ""
                    ])
                elif layout_mode == 'QUALITATIVE':
                    data.append([
                        Paragraph(p_name, param_title_style),
                        res_para,
                        flag_cell
                    ])
                else:
                    data.append([
                        Paragraph(p_name, param_title_style),
                        res_para,
                        Paragraph(p_unit, unit_style) if p_unit else "",
                        flag_cell
                    ])

            if "hiv" in panel_name.lower() and params:
                hiv_derived = evaluator.derive_hiv_outcome(params)
                h_flag = hiv_derived.get("clinical_flag")
                if h_flag:
                    if FONT_SYMBOL != 'Helvetica':
                        h_flag_cell = Paragraph(f'<font name="{FONT_SYMBOL}" color="#dc2626">\u26A0</font>', flag_center_style)
                    else:
                        h_flag_cell = Paragraph('<font color="#dc2626"><b>\u26A0</b></font>', flag_center_style)
                else:
                    h_flag_cell = ""

                h_res_para = Paragraph(f"<b>{hiv_derived['display_result']}</b>", result_abnormal_style if h_flag else result_style)
                if layout_mode == 'FULL':
                    data.append([
                        Paragraph("<b>Final HIV Interpretation:</b>", param_title_style),
                        h_res_para,
                        Paragraph("", unit_style),
                        h_flag_cell,
                        Paragraph(hiv_derived.get("reference") or "Non-Reactive", ref_style)
                    ])
                elif layout_mode == 'NO_UNIT':
                    data.append([
                        Paragraph("<b>Final HIV Interpretation:</b>", param_title_style),
                        h_res_para,
                        h_flag_cell,
                        Paragraph(hiv_derived.get("reference") or "Non-Reactive", ref_style)
                    ])
                else:
                    data.append([
                        Paragraph("<b>Final HIV Interpretation:</b>", param_title_style),
                        h_res_para,
                        h_flag_cell
                    ])
                summary_row_idx = len(data) - 1
                style_cmds.append(('BACKGROUND', (0, summary_row_idx), (-1, summary_row_idx), colors.HexColor('#f1f5f9')))

                if hiv_derived.get("advisory"):
                    adv_row_idx = len(data)
                    adv_style = ParagraphStyle(
                        name=f"HivAdv_{adv_row_idx}",
                        fontName=FONT_REGULAR,
                        fontSize=7.5,
                        leading=9.5,
                        textColor=colors.HexColor('#334155'),
                        leftIndent=8
                    )
                    adv_row = [Paragraph(f"<i>Clinical Note: {hiv_derived['advisory']}</i>", adv_style)] + [""] * (num_cols - 1)
                    data.append(adv_row)
                    style_cmds.append(('SPAN', (0, adv_row_idx), (-1, adv_row_idx)))
                    style_cmds.append(('BACKGROUND', (0, adv_row_idx), (-1, adv_row_idx), colors.HexColor('#f8fafc')))

            clin_comm = t.get("clinical_comments")
            if clin_comm and "hiv" not in panel_name.lower():
                comm_row_idx = len(data)
                comm_style = ParagraphStyle(
                    name=f"ClinComm_{comm_row_idx}",
                    fontName=FONT_REGULAR,
                    fontSize=7,
                    leading=8.5,
                    textColor=colors.HexColor('#475569'),
                    leftIndent=8
                )
                comm_row = [Paragraph(f"<i><b>Clinical Note:</b> {clin_comm}</i>", comm_style)] + [""] * (num_cols - 1)
                data.append(comm_row)
                style_cmds.append(('SPAN', (0, comm_row_idx), (-1, comm_row_idx)))
                style_cmds.append(('BACKGROUND', (0, comm_row_idx), (-1, comm_row_idx), colors.HexColor('#f8fafc')))
        else:
            # Standalone single test
            res_text = str(t.get("result") or "")
            flag_text = str(t.get("flag") or "")
            t_name = str(t.get("test_name") or "")
            t_unit = str(t.get("unit") or "")
            t_ref = str(t.get("reference") or t.get("reference_range") or "")

            if not flag_text and evaluator.is_qualitative_abnormal(res_text, t_ref, param_name=t_name):
                flag_text = "\u26A0"
            if flag_text == "[!]":
                flag_text = "\u26A0"

            if flag_text == "\u26A0":
                if FONT_SYMBOL != 'Helvetica':
                    flag_cell = Paragraph(f'<font name="{FONT_SYMBOL}" color="#dc2626">\u26A0</font>', flag_center_style)
                else:
                    flag_cell = Paragraph('<font color="#dc2626"><b>\u26A0</b></font>', flag_center_style)
            elif flag_text:
                flag_cell = Paragraph(f'<font color="#dc2626">{flag_text}</font>', flag_center_style)
            else:
                flag_cell = ""

            is_abnormal = flag_text in ["High", "Low", "Abnormal", "Reactive", "Positive", "H", "L", "H*", "L*", "*", "\u26A0", "[!]"] or evaluator.is_qualitative_abnormal(res_text, t_ref, param_name=t_name)
            res_para = Paragraph(res_text, result_abnormal_style if is_abnormal else result_style) if res_text else ""

            if layout_mode == 'FULL':
                data.append([
                    Paragraph(t_name, test_title_style),
                    res_para,
                    Paragraph(t_unit, unit_style) if t_unit else "",
                    flag_cell,
                    Paragraph(t_ref, ref_style) if t_ref else ""
                ])
            elif layout_mode == 'NO_UNIT':
                data.append([
                    Paragraph(t_name, test_title_style),
                    res_para,
                    flag_cell,
                    Paragraph(t_ref, ref_style) if t_ref else ""
                ])
            elif layout_mode == 'QUALITATIVE':
                data.append([
                    Paragraph(t_name, test_title_style),
                    res_para,
                    flag_cell
                ])
            else:
                data.append([
                    Paragraph(t_name, test_title_style),
                    res_para,
                    Paragraph(t_unit, unit_style) if t_unit else "",
                    flag_cell
                ])
        
    t_elem = Table(data, colWidths=col_widths)
    
    header_row_idx = 1 if show_dept else 0
    if show_dept:
        style_cmds.append(('FONTNAME', (0,0), (-1,0), FONT_BOLD))
        style_cmds.append(('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')))
        style_cmds.append(('SPAN', (0,0), (-1,0)))
        
    style_cmds.append(('FONTNAME', (0, header_row_idx), (-1, header_row_idx), FONT_BOLD))
    style_cmds.append(('LINEBELOW', (0, header_row_idx), (-1, header_row_idx), 1, colors.black))
    
    t_elem.setStyle(TableStyle(style_cmds))
    
    return KeepTogether([t_elem, Spacer(1, 4 if compact else 10)])

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


def _build_urinalysis_table(urinalysis_test: dict, compact: bool = False) -> KeepTogether:
    items = []
    ua_p_style = ParagraphStyle(name="UaParaStyle", fontName=FONT_REGULAR, fontSize=7.5, leading=9)
    
    if urinalysis_test.get("parameters"):
        sorted_params = sorted(
            urinalysis_test["parameters"],
            key=lambda p: (p.get("sort_order") if p.get("sort_order") is not None else 999)
        )
        for p in sorted_params:
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
    row_pad = 1.5 if compact else 2.0
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
        ('BOTTOMPADDING', (0,0), (-1,-1), row_pad),
        ('TOPPADDING', (0,0), (-1,-1), row_pad),
        ('GRID', (0,1), (-1,-1), 0.3, colors.HexColor('#d0d0d0')),
    ]))
    return KeepTogether([t, Spacer(1, 4 if compact else 10)])

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
    specimen = str(order_data.get("specimen") or "Blood")
    
    data = [
        ["Client No :", client_no, "Name :", name, "Lab No :", lab_no],
        ["Dated     :", date_val, "Age  :", age, "Ward/OPD :", ward],
        ["Ref. By   :", ref_by, "Sex  :", sex, "Specimen :", specimen]
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
    sex = str(order_data.get("sex") or "").strip().upper()[:1]

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
    if is_child:
        sec1 = [
            get_row("Total WBC Count", "Total WBC Count", "(10^3 / uL)", "6.0-14.0"),
            get_row("Red Blood Cells", "Red Blood Cells (RBC)", "(10^6 / uL)", "4.00 -5.20"),
            get_row("Hemoglobin", "Hemoglobin (Hb)", "g/dL", "11.5-15.5"),
            get_row("Hematocrit", "Hematocrit (HCT)", "%", "35.0-45.0"),
            get_row("Mean Cell Volume", "Mean Cell Volume (MCV)", "fL", "77.0-95.0"),
            get_row("Mean Cell Hb (MCH)", "Mean Cell Hb (MCH)", "pg", "23.0-31.0"),
            get_row("Mean Cell Hb Conc", "Mean Cell Hb Conc.(MCHC)", "g/dL", "28.0-33.0"),
            get_row("Platelets Count", "Platelets Count", "(10^3 / uL)", "150-450"),
        ]
        sec2 = [
            get_row("Neutrophils (%)", "Neutrophils", "%", "28.0-78.0"),
            get_row("Lymphocytes (%)", "Lymphocytes", "%", "19.0-60.0"),
            get_row("Monocytes (%)", "Monocytes", "%", "2.0-12.0"),
            get_row("Eosinophils (%)", "Eosinophils", "%", "1.0-6.0"),
            get_row("Basophils (%)", "Basophils", "%", "0.0-1.0"),
        ]
        sec3 = [
            get_row("Neutrophils (Absolute", "Neutrophils Count", "(10^9 / uL)", "1.50-8.50"),
            get_row("Lymphocytes (Absolute", "Lymphocytes Count", "(10^9 / uL)", "1.50-7.00"),
            get_row("Monocytes (Absolute", "Monocytes Count", "(10^9 / uL)", "0.20-1.00"),
            get_row("Eosinophils (Absolute", "Eosinophils Count", "(10^9 / uL)", "0.05-0.70"),
            get_row("Basophils (Absolute", "Basophils Count", "(10^9 / uL)", "0.0-0.2"),
        ]
    else:
        # Adult
        sec1 = [
            get_row("Total WBC Count", "Total WBC Count", "(10^3 / uL)", "4.0-10.0"),
            get_row("Red Blood Cells", "Red Blood Cells (RBC)", "(10^6 / uL)", "4.50-5.90" if sex == "M" else "4.00-5.20"),
            get_row("Hemoglobin", "Hemoglobin (Hb)", "g/dL", "13.0-17.5" if sex == "M" else "12.0-15.5"),
            get_row("Hematocrit", "Hematocrit (HCT)", "%", "40.0-52.0" if sex == "M" else "36.0-48.0"),
            get_row("Mean Cell Volume", "Mean Cell Volume (MCV)", "fL", "80.0-100.0"),
            get_row("Mean Cell Hb (MCH)", "Mean Cell Hb (MCH)", "pg", "27.0-34.0"),
            get_row("Mean Cell Hb Conc", "Mean Cell Hb Conc.(MCHC)", "g/dL", "32.0-36.0"),
            get_row("Platelets Count", "Platelets Count", "(10^3 / uL)", "150-400"),
        ]
        sec2 = [
            get_row("Neutrophils (%)", "Neutrophils", "%", "40.0-75.0"),
            get_row("Lymphocytes (%)", "Lymphocytes", "%", "20.0-45.0"),
            get_row("Monocytes (%)", "Monocytes", "%", "2.0-10.0"),
            get_row("Eosinophils (%)", "Eosinophils", "%", "1.0-6.0"),
            get_row("Basophils (%)", "Basophils", "%", "0.0-1.0"),
        ]
        sec3 = [
            get_row("Neutrophils (Absolute", "Neutrophils Count", "(10^9 / uL)", "2.00-7.00"),
            get_row("Lymphocytes (Absolute", "Lymphocytes Count", "(10^9 / uL)", "1.00-3.00"),
            get_row("Monocytes (Absolute", "Monocytes Count", "(10^9 / uL)", "0.20-1.00"),
            get_row("Eosinophils (Absolute", "Eosinophils Count", "(10^9 / uL)", "0.02-0.50"),
            get_row("Basophils (Absolute", "Basophils Count", "(10^9 / uL)", "0.0-0.1"),
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
        author=order_data.get("facility_name") or "M-LIS Diagnostic Laboratory",
        creator="M-LIS",
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
        total_tests_count = sum(len(d.get("tests", [])) for d in other_departments)
        is_dense = total_tests_count > 5

        flowables.append(Paragraph("Laboratory Report", title_style))
        flowables.append(Spacer(1, 4 if is_dense else 8))
        flowables.append(_build_metadata_table(order_data))
        flowables.append(Spacer(1, 6 if is_dense else 10))
        
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
                flowables.append(_build_department_table(dept_name, tests_to_render, compact=is_dense))
                
        if urinalysis_test:
            flowables.append(_build_urinalysis_table(urinalysis_test, compact=is_dense))
            
        flowables.append(_build_signatures_table(order_data, compact=is_dense))
        
        if cbc_test:
            flowables.append(PageBreak())

    # Render dedicated CBC page if present
    if cbc_test:
        flowables.append(_build_cbc_patient_header(order_data))
        flowables.append(Spacer(1, 6))
        flowables.extend(_build_cbc_table(order_data, cbc_test))
        flowables.append(_build_cbc_footer(order_data, cbc_test))
    
    custom_letterhead = order_data.get("letterhead_path")
    def make_canvas(*args, **kwargs):
        c = ReportNumberedCanvas(*args, **kwargs)
        c.letterhead_override = custom_letterhead
        return c

    doc.build(flowables, canvasmaker=make_canvas)
    
    return buffer.getvalue()

generate_report_pdf = generate_pdf




