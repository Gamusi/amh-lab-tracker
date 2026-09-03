import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, Paragraph, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from .pdf_generator import _init_fonts, FONT_REGULAR, FONT_BOLD
from .operations_pdf import OperationsNumberedCanvas

_init_fonts()

def _build_surveillance_trend_chart(trends_data: list, condition_names: list) -> Drawing:
    """Builds a compact native ReportLab vector bar chart showing monthly positive case trends."""
    d_width = 523
    d_height = 130
    drawing = Drawing(d_width, d_height)
    
    if not trends_data:
        drawing.add(String(20, 60, "No historical surveillance trend data available.", fontName=FONT_REGULAR, fontSize=9, fillColor=colors.HexColor('#64748B')))
        return drawing

    # Chart background box
    drawing.add(Rect(0, 0, d_width, d_height, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.8, rx=3, ry=3))
    
    max_val = max([t.get("total_positives", 0) for t in trends_data] + [5])
    num_months = len(trends_data)
    
    chart_left = 40
    chart_right = 505
    chart_bottom = 26
    chart_top = 110
    usable_w = chart_right - chart_left
    usable_h = chart_top - chart_bottom
    
    # Grid lines
    for i in range(4):
        y_val = chart_bottom + (usable_h * i / 3.0)
        lbl_val = int(max_val * i / 3.0)
        drawing.add(Line(chart_left, y_val, chart_right, y_val, strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.6))
        drawing.add(String(10, y_val - 3, str(lbl_val), fontName=FONT_REGULAR, fontSize=7.5, fillColor=colors.HexColor('#64748B')))
    
    # Bars
    bar_group_w = usable_w / num_months
    bar_w = min(32, bar_group_w * 0.48)
    
    for idx, t in enumerate(trends_data):
        tot = t.get("total_positives", 0)
        bar_h = (tot / float(max_val)) * usable_h if max_val > 0 else 0
        x = chart_left + (idx * bar_group_w) + ((bar_group_w - bar_w) / 2.0)
        y = chart_bottom
        
        drawing.add(Rect(x, y, bar_w, bar_h, fillColor=colors.HexColor('#B91C1C'), strokeColor=None, rx=2, ry=2))
        
        if tot > 0:
            drawing.add(String(x + (bar_w / 2.0) - (len(str(tot)) * 2.2), y + bar_h + 3, str(tot), fontName=FONT_BOLD, fontSize=7.5, fillColor=colors.HexColor('#B91C1C')))
        
        m_lbl = t.get("month_label", t.get("month_key", ""))
        drawing.add(String(x + (bar_w / 2.0) - (len(m_lbl) * 2.0), 10, m_lbl, fontName=FONT_REGULAR, fontSize=7.5, fillColor=colors.HexColor('#1E293B')))
    
    return drawing

def generate_surveillance_pdf(data: dict, current_user: dict) -> bytes:
    """
    Generates a publication-grade ReportLab PDF for Laboratory Epidemiological Surveillance.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45,
        title="Epidemiological Surveillance Report",
        author="M-LIS"
    )
    
    styles = {
        "Title": ParagraphStyle("DocTitle", fontName=FONT_BOLD, fontSize=13, leading=16, alignment=TA_LEFT, textColor=colors.HexColor('#0B5FA5'), keepWithNext=True),
        "SectionHeader": ParagraphStyle("SecHead", fontName=FONT_BOLD, fontSize=10, leading=13, alignment=TA_LEFT, textColor=colors.HexColor('#0B5FA5'), spaceBefore=10, spaceAfter=4, keepWithNext=True),
        "Normal": ParagraphStyle("Normal", fontName=FONT_REGULAR, fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B')),
        "NormalBold": ParagraphStyle("NormalB", fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B')),
        "TableHead": ParagraphStyle("TblHead", fontName=FONT_BOLD, fontSize=8, leading=10, textColor=colors.HexColor('#0F172A')),
        "TableHeadRight": ParagraphStyle("TblHeadR", fontName=FONT_BOLD, fontSize=8, leading=10, alignment=TA_RIGHT, textColor=colors.HexColor('#0F172A')),
        "TableCell": ParagraphStyle("TblCell", fontName=FONT_REGULAR, fontSize=8, leading=10, textColor=colors.HexColor('#1E293B')),
        "TableCellBold": ParagraphStyle("TblCellB", fontName=FONT_BOLD, fontSize=8, leading=10, textColor=colors.HexColor('#1E293B')),
        "TableCellRight": ParagraphStyle("TblCellR", fontName=FONT_REGULAR, fontSize=8, leading=10, alignment=TA_RIGHT, textColor=colors.HexColor('#1E293B')),
        "KpiLabel": ParagraphStyle("KpiLbl", fontName=FONT_BOLD, fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.HexColor('#64748B')),
        "KpiVal": ParagraphStyle("KpiVal", fontName=FONT_BOLD, fontSize=16, leading=19, alignment=TA_CENTER, textColor=colors.HexColor('#0B5FA5')),
        "KpiValAlert": ParagraphStyle("KpiValA", fontName=FONT_BOLD, fontSize=16, leading=19, alignment=TA_CENTER, textColor=colors.HexColor('#B91C1C')),
    }
    
    story = []
    
    period = data.get("period", {})
    summary = data.get("summary", {})
    sections = data.get("sections_breakdown", [])
    ledger = data.get("surveillance_ledger", [])
    wards = data.get("wards_breakdown", [])
    trends_obj = data.get("monthly_trends", {})
    
    prep_by_name = current_user.get("full_name") or current_user.get("username") or "Laboratory Staff"
    now_str = datetime.datetime.now().strftime("%d-%b-%Y %H:%M")
    formatted_period = period.get("formatted_period", period.get("period_type", ""))

    # =========================================================================
    # PAGE 1: Spacer to clear letterhead header banner (97pt)
    # =========================================================================
    story.append(Spacer(1, 97))
    
    # Title & Metadata Block
    header_block = []
    header_block.append(Paragraph("LABORATORY EPIDEMIOLOGICAL SURVEILLANCE REPORT", styles["Title"]))
    header_block.append(Spacer(1, 4))
    
    meta_data = [
        [
            Paragraph(f"<b>Reporting Period:</b> {formatted_period}", styles["NormalBold"]),
            Paragraph(f"<b>Generated on:</b> {now_str}", styles["Normal"])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[300, 223])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    header_block.append(meta_table)
    header_block.append(Spacer(1, 8))

    # 3 Clean KPI Cards
    tot_eval = summary.get("total_evaluated", 0)
    tot_inc = summary.get("total_incident_cases", 0)
    inc_rate = summary.get("overall_incidence_rate", 0.0)
    
    kpi_card_1 = [
        [Paragraph("TOTAL EVALUATED", styles["KpiLabel"])],
        [Paragraph(str(tot_eval), styles["KpiVal"])]
    ]
    kpi_card_2 = [
        [Paragraph("POSITIVE / INCIDENT CASES", styles["KpiLabel"])],
        [Paragraph(str(tot_inc), styles["KpiValAlert"])]
    ]
    kpi_card_3 = [
        [Paragraph("INCIDENCE / POSITIVITY RATE", styles["KpiLabel"])],
        [Paragraph(f"{inc_rate}%", styles["KpiVal"])]
    ]

    t1 = Table(kpi_card_1, colWidths=[166])
    t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 6)]))
    t2 = Table(kpi_card_2, colWidths=[166])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FECACA')), ('PADDING', (0,0), (-1,-1), 6)]))
    t3 = Table(kpi_card_3, colWidths=[166])
    t3.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 6)]))

    kpi_wrapper = Table([[t1, t2, t3]], colWidths=[174, 174, 175])
    kpi_wrapper.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    header_block.append(kpi_wrapper)
    header_block.append(Spacer(1, 10))

    story.append(KeepTogether(header_block))

    # =========================================================================
    # 1. Monthly Incidence & Positivity Trends (On Page 1 Dashboard)
    # =========================================================================
    trend_list = trends_obj.get("trends", [])
    month_headers = trends_obj.get("month_headers", ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"])
    matrix_rows = trends_obj.get("matrix_rows", [])
    monthly_totals = trends_obj.get("monthly_totals", [0]*12)
    grand_total = trends_obj.get("grand_total", 0)

    chart_drawing = _build_surveillance_trend_chart(trend_list, [r["condition_name"] for r in matrix_rows])

    # Transposed Trends Data Table: Condition / Assay in rows, 12 Months in columns + Sum
    t_head = [Paragraph("Condition / Assay", styles["TableHead"])]
    for mh in month_headers:
        t_head.append(Paragraph(mh, styles["TableHeadRight"]))
    t_head.append(Paragraph("Sum", styles["TableHeadRight"]))

    trend_table_rows = [t_head]
    col_w_name = 133
    col_w_m = 30
    widths = [col_w_name] + [col_w_m] * (len(month_headers) + 1)

    for m_row in matrix_rows:
        r_cols = [Paragraph(m_row["condition_name"], styles["TableCellBold"])]
        for cnt in m_row["counts"]:
            r_cols.append(Paragraph(str(cnt), styles["TableCellRight"]))
        r_cols.append(Paragraph(str(m_row["total"]), styles["TableCellRight"]))
        trend_table_rows.append(r_cols)

    if not matrix_rows:
        trend_table_rows.append([Paragraph("No positive surveillance cases recorded", styles["TableCell"])] + [Paragraph("0", styles["TableCellRight"])] * (len(month_headers) + 1))

    # Grand total bottom row
    total_cols = [Paragraph("Total Positives", styles["TableCellBold"])]
    for mt in monthly_totals:
        total_cols.append(Paragraph(str(mt), styles["TableCellRight"]))
    total_cols.append(Paragraph(str(grand_total), styles["TableCellRight"]))
    trend_table_rows.append(total_cols)

    trends_table = Table(trend_table_rows, colWidths=widths, repeatRows=1)
    trends_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(KeepTogether([Paragraph("1. Monthly Incidence & Positivity Trends", styles["SectionHeader"]), chart_drawing, Spacer(1, 4), trends_table]))
    story.append(Spacer(1, 8))

    # =========================================================================
    # 2. Positive Cases by Ward of Origin (On Page 1 Dashboard)
    # =========================================================================
    ward_rows = [
        [
            Paragraph("Ward of Origin", styles["TableHead"]),
            Paragraph("Evaluated Tests", styles["TableHeadRight"]),
            Paragraph("Positive Cases", styles["TableHeadRight"]),
            Paragraph("Positivity Rate (%)", styles["TableHeadRight"])
        ]
    ]
    if wards:
        for w in wards[:6]:
            ward_rows.append([
                Paragraph(w.get("ward", ""), styles["TableCellBold"]),
                Paragraph(str(w.get("evaluated", 0)), styles["TableCellRight"]),
                Paragraph(str(w.get("positive_cases", 0)), styles["TableCellRight"]),
                Paragraph(f"{w.get('incidence_rate', 0.0)}%", styles["TableCellRight"])
            ])
    else:
        ward_rows.append([Paragraph("No ward records in this period", styles["TableCell"]), Paragraph("0", styles["TableCellRight"]), Paragraph("0", styles["TableCellRight"]), Paragraph("0.0%", styles["TableCellRight"])])

    ward_table = Table(ward_rows, colWidths=[203, 110, 110, 100], repeatRows=1)
    ward_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(KeepTogether([Paragraph("2. Positive Cases by Ward of Origin", styles["SectionHeader"]), ward_table]))

    # =========================================================================
    # 3. Disease & Syndrome Surveillance Ledger (Page 2)
    # =========================================================================
    story.append(PageBreak())
    
    ledger_rows = [
        [
            Paragraph("Disease / Condition / Assay", styles["TableHead"]),
            Paragraph("Section", styles["TableHead"]),
            Paragraph("Evaluated", styles["TableHeadRight"]),
            Paragraph("Positive", styles["TableHeadRight"]),
            Paragraph("Negative", styles["TableHeadRight"]),
            Paragraph("Incidence Rate", styles["TableHeadRight"]),
        ]
    ]
    for item in ledger:
        ledger_rows.append([
            Paragraph(item.get("test_name", ""), styles["TableCellBold"]),
            Paragraph(item.get("section_name", ""), styles["TableCell"]),
            Paragraph(str(item.get("evaluated", 0)), styles["TableCellRight"]),
            Paragraph(str(item.get("positive", 0)), styles["TableCellRight"]),
            Paragraph(str(item.get("negative", 0)), styles["TableCellRight"]),
            Paragraph(f"{item.get('incidence_rate', 0.0)}%", styles["TableCellRight"]),
        ])
    if not ledger:
        ledger_rows.append([Paragraph("No tracked surveillance tests recorded", styles["TableCell"]), Paragraph("-", styles["TableCell"]), Paragraph("0", styles["TableCellRight"]), Paragraph("0", styles["TableCellRight"]), Paragraph("0", styles["TableCellRight"]), Paragraph("0.0%", styles["TableCellRight"])])

    ledger_table = Table(ledger_rows, colWidths=[163, 130, 60, 55, 55, 60], repeatRows=1)
    ledger_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(Paragraph("3. Disease & Syndrome Surveillance Ledger", styles["SectionHeader"]))
    story.append(ledger_table)

    # =========================================================================
    # 4. Comments & Sign-Off Block
    # =========================================================================
    story.append(PageBreak())
    
    comments_page = []
    comments_page.append(Paragraph("4. Comments & Sign-Off", styles["SectionHeader"]))
    comments_page.append(Spacer(1, 6))
    
    notes_rows = [[Paragraph("", styles["Normal"])] for _ in range(16)]
    notes_table = Table(notes_rows, colWidths=[523], rowHeights=[26]*16)
    notes_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFAFA')),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    comments_page.append(notes_table)
    comments_page.append(Spacer(1, 24))

    # Sign-Off Block
    sign_data = [
        [
            Paragraph(f"<b>Prepared by:</b> {prep_by_name}", styles["NormalBold"]),
            Paragraph(f"<b>Date:</b> {now_str[:11]}", styles["NormalBold"])
        ],
        [
            Paragraph("Signature: _____________________________________", styles["Normal"]),
            Paragraph("", styles["Normal"])
        ]
    ]
    sign_table = Table(sign_data, colWidths=[320, 203], rowHeights=[18, 24])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    comments_page.append(sign_table)

    story.append(KeepTogether(comments_page))

    # Build PDF with OperationsNumberedCanvas
    doc.build(story, canvasmaker=OperationsNumberedCanvas)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
