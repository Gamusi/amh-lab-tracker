import os
import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, Paragraph, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from .pdf_generator import _init_fonts, FONT_REGULAR, FONT_BOLD

_init_fonts()

PAGE_WIDTH, PAGE_HEIGHT = A4

def find_branding_assets(branding_dir: str, override: str = None) -> dict:
    """
    Finds matching letterhead image files in branding_dir, supporting exact names
    and fuzzy keyword matching (*header*, *footer*, *watermark*, *letterhead*).
    """
    assets = {"full": None, "header": None, "watermark": None, "footer": None}
    if override and os.path.exists(override):
        assets["full"] = override
        return assets
    if not os.path.isdir(branding_dir):
        return assets

    files = [f for f in os.listdir(branding_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    for f in files:
        f_lower = f.lower()
        full_p = os.path.join(branding_dir, f)
        if f_lower == "letterhead.png":
            assets["full"] = full_p
        elif "header" in f_lower and "watermark" in f_lower:
            assets["header"] = full_p
        elif "footer" in f_lower and "watermark" in f_lower:
            assets["footer"] = full_p
        elif "watermark" in f_lower and "header" not in f_lower and "footer" not in f_lower:
            assets["watermark"] = full_p

    for f in files:
        f_lower = f.lower()
        full_p = os.path.join(branding_dir, f)
        if not assets["full"] and ("letterhead" in f_lower or "background" in f_lower):
            assets["full"] = full_p
        if not assets["header"] and "header" in f_lower:
            assets["header"] = full_p
        if not assets["footer"] and "footer" in f_lower:
            assets["footer"] = full_p
        if not assets["watermark"] and "watermark" in f_lower:
            assets["watermark"] = full_p

    if not assets["full"]:
        assets["full"] = assets["header"] or assets["watermark"]
    return assets

class OperationsNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas applying page-specific letterhead background images:
    - Single Page (1 of 1): Full letterhead (letterhead.png)
    - Page 1 (of N > 1): letterhead-header+watermark_only.png
    - Middle Pages (2 to N-1): letterhead-watermark_only.png
    - Last Page (N of N > 1): letterhead-footer+watermark_only.png
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        branding_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "branding")
        )
        b_assets = find_branding_assets(branding_dir)
        full_path = b_assets["full"]
        header_path = b_assets["header"]
        watermark_path = b_assets["watermark"]
        footer_path = b_assets["footer"]

        for state in self._saved_page_states:
            self.__dict__.update(state)
            page_num = self._pageNumber
            
            # 1. Background image per page
            if num_pages == 1:
                bg_img = full_path or header_path
            elif page_num == 1:
                bg_img = header_path or full_path
            elif page_num == num_pages:
                bg_img = footer_path or watermark_path or full_path
            else:
                bg_img = watermark_path or full_path

            if bg_img and os.path.exists(bg_img):
                self.saveState()
                self.drawImage(bg_img, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT, mask='auto')
                self.restoreState()
            
            # 2. Clean Page numbering in bottom-right margin (safely above footer graphics)
            self.saveState()
            self.setFont(FONT_REGULAR, 8)
            self.setFillColor(colors.HexColor('#64748B'))
            self.drawRightString(PAGE_WIDTH - 36, 52, f"Page {page_num} of {num_pages}")
            self.restoreState()
            
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def _build_trend_chart(trends_data: list, sections: list) -> Drawing:
    """Builds a compact native ReportLab vector bar chart showing monthly volume trends."""
    d_width = 523
    d_height = 130
    drawing = Drawing(d_width, d_height)
    
    if not trends_data:
        drawing.add(String(20, 60, "No historical trend data available.", fontName=FONT_REGULAR, fontSize=9, fillColor=colors.HexColor('#64748B')))
        return drawing

    # Chart background box
    drawing.add(Rect(0, 0, d_width, d_height, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.8, rx=3, ry=3))
    
    max_val = max([t.get("total", 0) for t in trends_data] + [10])
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
        tot = t.get("total", 0)
        bar_h = (tot / float(max_val)) * usable_h if max_val > 0 else 0
        x = chart_left + (idx * bar_group_w) + ((bar_group_w - bar_w) / 2.0)
        y = chart_bottom
        
        drawing.add(Rect(x, y, bar_w, bar_h, fillColor=colors.HexColor('#0B5FA5'), strokeColor=None, rx=2, ry=2))
        
        if tot > 0:
            drawing.add(String(x + (bar_w / 2.0) - (len(str(tot)) * 2.2), y + bar_h + 3, str(tot), fontName=FONT_BOLD, fontSize=7.5, fillColor=colors.HexColor('#0B5FA5')))
        
        m_lbl = t.get("month_short", t.get("month_label", "")[:3])
        drawing.add(String(x + (bar_w / 2.0) - (len(m_lbl) * 2.0), 10, m_lbl, fontName=FONT_REGULAR, fontSize=7.5, fillColor=colors.HexColor('#1E293B')))
    
    return drawing

def generate_operations_pdf(data: dict, current_user: dict) -> bytes:
    """
    Generates a clean, deterministic ReportLab PDF for Laboratory Operations & Performance.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45,
        title="Laboratory Operations & Performance Report",
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
    }
    
    story = []
    
    period = data.get("period", {})
    summary = data.get("summary", {})
    categories = data.get("categories_breakdown", [])
    sections = data.get("sections_breakdown", [])
    wards = data.get("wards_breakdown", [])
    demand = data.get("demand_dynamics", {})
    appendix_tests = data.get("appendix_menu_activity", [])
    trends_obj = data.get("monthly_trends", {})
    
    prep_by_name = current_user.get("full_name") or current_user.get("username") or "Laboratory Staff"
    now_str = datetime.datetime.now().strftime("%d-%b-%Y %H:%M")
    formatted_period = period.get("formatted_period", period.get("period_type", ""))

    # =========================================================================
    # PAGE 1: Spacer to clear letterhead header banner moved 12pts down (97pt)
    # =========================================================================
    story.append(Spacer(1, 97))
    
    # Title & Metadata Block
    header_block = []
    header_block.append(Paragraph("LABORATORY OPERATIONS & PERFORMANCE REPORT", styles["Title"]))
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

    # 3 Clean KPI Cards (No subtext)
    tot_done = summary.get("total_done", summary.get("total_tests_completed", 0))
    tot_clients = summary.get("total_clients", summary.get("total_visits", 0))
    menu_cov = summary.get("menu_coverage_percent", summary.get("menu_fulfillment_rate_percent", 0.0))
    
    kpi_card_1 = [
        [Paragraph("TOTAL DONE", styles["KpiLabel"])],
        [Paragraph(str(tot_done), styles["KpiVal"])]
    ]
    kpi_card_2 = [
        [Paragraph("TOTAL CLIENTS", styles["KpiLabel"])],
        [Paragraph(str(tot_clients), styles["KpiVal"])]
    ]
    kpi_card_3 = [
        [Paragraph("TEST MENU COVERAGE", styles["KpiLabel"])],
        [Paragraph(f"{menu_cov}%", styles["KpiVal"])]
    ]

    t1 = Table(kpi_card_1, colWidths=[166])
    t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 6)]))
    t2 = Table(kpi_card_2, colWidths=[166])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 6)]))
    t3 = Table(kpi_card_3, colWidths=[166])
    t3.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 6)]))

    kpi_wrapper = Table([[t1, t2, t3]], colWidths=[174, 174, 175])
    kpi_wrapper.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    header_block.append(kpi_wrapper)
    header_block.append(Spacer(1, 10))

    story.append(KeepTogether(header_block))

    # =========================================================================
    # 1. Section Workload and TAT
    # =========================================================================
    sec_rows = [
        [
            Paragraph("Section Name", styles["TableHead"]),
            Paragraph("Tests Done", styles["TableHeadRight"]),
            Paragraph("Share (%)", styles["TableHeadRight"]),
            Paragraph("Average TAT", styles["TableHeadRight"]),
            Paragraph("TAT Range (Min - Max)", styles["TableHeadRight"]),
        ]
    ]
    for s in sections:
        min_t = s.get("min_tat_mins", 0.0)
        max_t = s.get("max_tat_mins", 0.0)
        range_str = f"{min_t}m - {max_t}m" if s.get("test_count", 0) > 0 else "-"
        sec_rows.append([
            Paragraph(s.get("section_name", ""), styles["TableCellBold"]),
            Paragraph(str(s.get("test_count", 0)), styles["TableCellRight"]),
            Paragraph(f"{s.get('volume_percentage', 0.0)}%", styles["TableCellRight"]),
            Paragraph(f"{s.get('avg_tat_mins', 0.0)}m", styles["TableCellRight"]),
            Paragraph(range_str, styles["TableCellRight"]),
        ])
    
    sec_table = Table(sec_rows, colWidths=[163, 85, 85, 95, 95], repeatRows=1)
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(Paragraph("1. Section Workload and TAT", styles["SectionHeader"]))
    story.append(sec_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 2. Monthly Workload Trends
    # =========================================================================
    trend_list = trends_obj.get("trends", [])
    month_headers = trends_obj.get("month_headers", ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"])
    matrix_rows = trends_obj.get("matrix_rows", [])
    monthly_totals = trends_obj.get("monthly_totals", [0]*12)
    grand_total = trends_obj.get("grand_total", 0)
    
    chart_drawing = _build_trend_chart(trend_list, [r["section_name"] for r in matrix_rows])

    # Transposed Trends Data Table: Section Name in rows, 12 Months in columns + Sum
    t_head = [Paragraph("Section Name", styles["TableHead"])]
    for mh in month_headers:
        t_head.append(Paragraph(mh, styles["TableHeadRight"]))
    t_head.append(Paragraph("Sum", styles["TableHeadRight"]))
    
    trend_table_rows = [t_head]
    col_w_name = 133
    col_w_m = 30
    widths = [col_w_name] + [col_w_m] * (len(month_headers) + 1)

    for m_row in matrix_rows:
        r_cols = [Paragraph(m_row["section_name"], styles["TableCellBold"])]
        for cnt in m_row["counts"]:
            r_cols.append(Paragraph(str(cnt), styles["TableCellRight"]))
        r_cols.append(Paragraph(str(m_row["total"]), styles["TableCellRight"]))
        trend_table_rows.append(r_cols)

    # Grand total bottom row
    total_cols = [Paragraph("Total Workload", styles["TableCellBold"])]
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
    
    story.append(Paragraph("2. Monthly Workload Trends", styles["SectionHeader"]))
    story.append(chart_drawing)
    story.append(Spacer(1, 4))
    story.append(trends_table)
    story.append(Spacer(1, 8))

    # =========================================================================
    # 3. Workload by Ward of Origin
    # =========================================================================
    ward_rows = [
        [
            Paragraph("Ward of Origin", styles["TableHead"]),
            Paragraph("Tests Processed", styles["TableHeadRight"]),
            Paragraph("Volume Share (%)", styles["TableHeadRight"])
        ]
    ]
    if wards:
        for w in wards:
            ward_rows.append([
                Paragraph(w.get("ward", ""), styles["TableCellBold"]),
                Paragraph(str(w.get("count", 0)), styles["TableCellRight"]),
                Paragraph(f"{w.get('percentage', 0.0)}%", styles["TableCellRight"])
            ])
    else:
        ward_rows.append([Paragraph("No ward records in this period", styles["TableCell"]), Paragraph("0", styles["TableCellRight"]), Paragraph("0.0%", styles["TableCellRight"])])

    ward_table = Table(ward_rows, colWidths=[263, 130, 130], repeatRows=1)
    ward_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(Paragraph("3. Workload by Ward of Origin", styles["SectionHeader"]))
    story.append(ward_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 4. Test Category Distribution (In-House, Referral, Outreach)
    # =========================================================================
    cat_rows = [
        [
            Paragraph("Category", styles["TableHead"]),
            Paragraph("Tests Done", styles["TableHeadRight"]),
            Paragraph("Volume Share (%)", styles["TableHeadRight"])
        ]
    ]
    for c in categories:
        cat_rows.append([
            Paragraph(c.get("category", ""), styles["TableCellBold"]),
            Paragraph(str(c.get("count", 0)), styles["TableCellRight"]),
            Paragraph(f"{c.get('percentage', 0.0)}%", styles["TableCellRight"])
        ])
    
    cat_table = Table(cat_rows, colWidths=[263, 130, 130], repeatRows=1)
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(Paragraph("4. Test Category Distribution", styles["SectionHeader"]))
    story.append(cat_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 5. Test Demand
    # =========================================================================
    top_5 = demand.get("top_requested_tests", [])
    bottom_5 = demand.get("least_requested_tests", [])
    unrequested = demand.get("unrequested_tests", [])

    top_cells = [
        [Paragraph("Top 5 Most Requested Tests", styles["TableHead"]), Paragraph("Section", styles["TableHead"]), Paragraph("Done", styles["TableHeadRight"])]
    ]
    for t in top_5:
        top_cells.append([
            Paragraph(t.get("test_name", ""), styles["TableCellBold"]),
            Paragraph(t.get("section_name", ""), styles["TableCell"]),
            Paragraph(str(t.get("count", 0)), styles["TableCellRight"])
        ])
    if not top_5:
        top_cells.append([Paragraph("No tests requested", styles["TableCell"]), Paragraph("-", styles["TableCell"]), Paragraph("0", styles["TableCellRight"])])

    bot_cells = [
        [Paragraph("Bottom 5 Least Requested Tests (Ordered >= 1)", styles["TableHead"]), Paragraph("Section", styles["TableHead"]), Paragraph("Done", styles["TableHeadRight"])]
    ]
    for b in bottom_5:
        bot_cells.append([
            Paragraph(b.get("test_name", ""), styles["TableCellBold"]),
            Paragraph(b.get("section_name", ""), styles["TableCell"]),
            Paragraph(str(b.get("count", 0)), styles["TableCellRight"])
        ])
    if not bottom_5:
        bot_cells.append([Paragraph("No tests requested", styles["TableCell"]), Paragraph("-", styles["TableCell"]), Paragraph("0", styles["TableCellRight"])])

    tbl_top = Table(top_cells, colWidths=[120, 95, 40])
    tbl_top.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 3)]))
    tbl_bot = Table(bot_cells, colWidths=[120, 95, 40])
    tbl_bot.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 3)]))

    demand_split = Table([[tbl_top, tbl_bot]], colWidths=[260, 263])
    demand_split.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    
    demand_block = [Paragraph("5. Test Demand", styles["SectionHeader"]), demand_split]
    
    if unrequested:
        unreq_note = Table([[Paragraph(f"<b>Unrequested Catalog Tests:</b> {len(unrequested)} active catalog tests had zero requests in this period. (See Appendix for full listing).", styles["Normal"])]], colWidths=[523])
        unreq_note.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        demand_block.append(Spacer(1, 6))
        demand_block.append(unreq_note)

    story.append(KeepTogether(demand_block))

    # =========================================================================
    # 6. Comments (Dedicated Full Page BEFORE Appendix)
    # =========================================================================
    story.append(PageBreak())
    
    comments_page = []
    comments_page.append(Paragraph("6. Comments", styles["SectionHeader"]))
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

    # =========================================================================
    # Appendix: Complete Diagnostic Menu Activity (THE VERY LAST SECTION)
    # =========================================================================
    story.append(PageBreak())
    
    story.append(Paragraph("Appendix: Complete Diagnostic Menu Activity", styles["SectionHeader"]))
    story.append(Spacer(1, 4))
    
    app_rows = [
        [
            Paragraph("Section", styles["TableHead"]),
            Paragraph("Test Name", styles["TableHead"]),
            Paragraph("Completed Orders", styles["TableHeadRight"]),
        ]
    ]
    for at in appendix_tests:
        app_rows.append([
            Paragraph(at.get("section_name", ""), styles["TableCell"]),
            Paragraph(at.get("test_name", ""), styles["TableCellBold"]),
            Paragraph(str(at.get("completed_count", 0)), styles["TableCellRight"]),
        ])
    
    app_table = Table(app_rows, colWidths=[173, 230, 120], repeatRows=1)
    app_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(app_table)

    # Build PDF with OperationsNumberedCanvas
    doc.build(story, canvasmaker=OperationsNumberedCanvas)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
