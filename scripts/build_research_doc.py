"""
Builds a beautifully styled Word Document (.docx) of the Research & Engineering Findings.
Produces:
  - docs/RESEARCH.docx
  - RESEARCH.docx (in project root)
"""

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Palette
COLOR_PRIMARY = RGBColor(17, 24, 39)     # #111827
COLOR_MUTED = RGBColor(75, 85, 99)       # #4B5563
COLOR_BORDER = "D1D5DB"                  # #D1D5DB
COLOR_BG_ALT = "FAFAFA"                  # #FAFAFA
COLOR_BG_HEADER = "F3F4F6"               # #F3F4F6
COLOR_BG_BOX = "F9FAFB"                  # #F9FAFB
COLOR_ACCENT = "111827"                  # #111827


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding for a table cell (in dxa: 20 dxa = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_cell_shading(cell, color_hex):
    """Set cell background fill color."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_cell_borders(cell, top="none", bottom="none", left="none", right="none",
                     color="D1D5DB", sz="4"):
    """Set custom borders on a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    
    def border_tag(side, val):
        if val == "none":
            return f'<w:{side} w:val="none"/>'
        return f'<w:{side} w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'

    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'{border_tag("top", top)}'
        f'{border_tag("left", left)}'
        f'{border_tag("bottom", bottom)}'
        f'{border_tag("right", right)}'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)


def format_table_header(row, col_widths, titles):
    """Style the header row of a table."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
    
    for i, cell in enumerate(row.cells):
        cell.width = col_widths[i]
        set_cell_shading(cell, COLOR_BG_HEADER)
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        set_cell_borders(cell, top="single", bottom="single", left="single", right="single",
                         color=COLOR_BORDER, sz="6")
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(titles[i])
        run.bold = True
        run.font.name = "Segoe UI"
        run.font.size = Pt(9.5)
        run.font.color.rgb = COLOR_PRIMARY


def add_styled_row(table, col_widths, values, is_alt=False):
    """Add a data row with borders, padding, and optional alternating background."""
    row = table.add_row()
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
    
    fill = COLOR_BG_ALT if is_alt else "FFFFFF"
    for i, cell in enumerate(row.cells):
        cell.width = col_widths[i]
        set_cell_shading(cell, fill)
        set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
        set_cell_borders(cell, top="single", bottom="single", left="single", right="single",
                         color=COLOR_BORDER, sz="4")
        cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        
        # Render markdown bolding/code in cell text
        parts = values[i]
        if isinstance(parts, str):
            render_inline_markup(p, parts, font_size=9)
        elif isinstance(parts, list):
            for idx, item in enumerate(parts):
                if idx > 0:
                    p = cell.add_paragraph()
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.line_spacing = 1.15
                render_inline_markup(p, item, font_size=9)
    return row


def render_inline_markup(paragraph, text, font_size=10, default_color=COLOR_PRIMARY):
    """Parses basic inline **bold**, *italic*, and `code` formatting."""
    import re
    # Tokens: `code`, **bold**, *italic*, plain text
    pattern = re.compile(r'(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|[^\`*]+)')
    tokens = pattern.findall(text)
    
    for token in tokens:
        if token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(font_size - 0.5)
            run.font.color.rgb = COLOR_PRIMARY
        elif token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
            run.font.name = "Segoe UI"
            run.font.size = Pt(font_size)
            run.font.color.rgb = default_color
        elif token.startswith("*") and token.endswith("*"):
            run = paragraph.add_run(token[1:-1])
            run.italic = True
            run.font.name = "Segoe UI"
            run.font.size = Pt(font_size)
            run.font.color.rgb = default_color
        else:
            run = paragraph.add_run(token)
            run.font.name = "Segoe UI"
            run.font.size = Pt(font_size)
            run.font.color.rgb = default_color


def add_callout_box(doc, text, title=None):
    """Adds a callout block with a thick left accent border and shaded background."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(7.0)
    set_cell_shading(cell, COLOR_BG_BOX)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=160)
    
    # Left thick accent border, light outer borders
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{COLOR_ACCENT}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    
    if title:
        r_title = p.add_run(title)
        r_title.bold = True
        r_title.font.name = "Segoe UI"
        r_title.font.size = Pt(9.5)
        r_title.font.color.rgb = COLOR_PRIMARY
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        
    render_inline_markup(p, text, font_size=9.5)
    
    # Add an empty spacing paragraph after table
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)


def add_highlight_list_box(doc, title, items):
    """Adds a callout box containing a bulleted list."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(7.0)
    set_cell_shading(cell, COLOR_BG_BOX)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=160)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{COLOR_ACCENT}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(title)
    r.bold = True
    r.font.name = "Segoe UI"
    r.font.size = Pt(9.5)
    r.font.color.rgb = COLOR_PRIMARY
    
    for item in items:
        p_item = cell.add_paragraph()
        p_item.paragraph_format.space_before = Pt(1)
        p_item.paragraph_format.space_after = Pt(2)
        p_item.paragraph_format.left_indent = Inches(0.2)
        p_item.paragraph_format.line_spacing = 1.15
        
        bullet_run = p_item.add_run("•  ")
        bullet_run.bold = True
        bullet_run.font.name = "Segoe UI"
        bullet_run.font.size = Pt(9.5)
        bullet_run.font.color.rgb = COLOR_PRIMARY
        
        render_inline_markup(p_item, item, font_size=9.5)
        
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)


def add_section_heading(doc, text):
    """Section Heading (H2 equivalent in PDF) with bottom divider bar."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Segoe UI"
    run.font.size = Pt(12)
    run.font.color.rgb = COLOR_PRIMARY
    
    # Add bottom border under heading for clean visual hierarchy
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'<w:bottom w:val="single" w:sz="12" w:space="4" w:color="{COLOR_ACCENT}"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)


def add_subheading(doc, text):
    """Subsection heading (H3 equivalent in PDF)."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Segoe UI"
    run.font.size = Pt(10.5)
    run.font.color.rgb = COLOR_PRIMARY


def add_paragraph_text(doc, text):
    """Adds a standard body paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    render_inline_markup(p, text, font_size=10)
    return p


def add_bullet_point(doc, text):
    """Adds a clean bullet point."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.line_spacing = 1.15
    
    bullet_run = p.add_run("•  ")
    bullet_run.bold = True
    bullet_run.font.name = "Segoe UI"
    bullet_run.font.size = Pt(10)
    bullet_run.font.color.rgb = COLOR_PRIMARY
    
    render_inline_markup(p, text, font_size=10)


def add_numbered_item(doc, number, text):
    """Adds a numbered list item."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.line_spacing = 1.15
    
    num_run = p.add_run(f"{number}.  ")
    num_run.bold = True
    num_run.font.name = "Segoe UI"
    num_run.font.size = Pt(10)
    num_run.font.color.rgb = COLOR_PRIMARY
    
    render_inline_markup(p, text, font_size=10)


def build_research_document():
    doc = Document()
    
    # Page Setup (A4 with 15mm margins, matching PDF)
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.63)
        section.right_margin = Inches(0.63)
        
        # Header / Footer
        footer = section.footer
        p_ft = footer.paragraphs[0]
        p_ft.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_ft.paragraph_format.space_before = Pt(0)
        p_ft.paragraph_format.space_after = Pt(0)
        r_ft = p_ft.add_run("Podcast Companion — Research & Engineering Findings  |  AI Engineering Project")
        r_ft.font.name = "Segoe UI"
        r_ft.font.size = Pt(8.5)
        r_ft.font.color.rgb = COLOR_MUTED

    # Header / Title Block
    # 1. Badge
    p_badge = doc.add_paragraph()
    p_badge.paragraph_format.space_before = Pt(0)
    p_badge.paragraph_format.space_after = Pt(4)
    r_badge = p_badge.add_run("AI ENGINEERING PROJECT")
    r_badge.bold = True
    r_badge.font.name = "Segoe UI"
    r_badge.font.size = Pt(8.5)
    r_badge.font.color.rgb = COLOR_MUTED

    # 2. Document Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(2)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run("Podcast Companion: Research & Engineering Findings")
    r_title.bold = True
    r_title.font.name = "Segoe UI"
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = COLOR_PRIMARY

    # 3. Subtitle
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(6)
    r_sub = p_sub.add_run("A clear, practical review of technical choices, reliability mechanisms, and real-world benchmarks")
    r_sub.font.name = "Segoe UI"
    r_sub.font.size = Pt(10.5)
    r_sub.font.color.rgb = COLOR_MUTED

    # 4. Meta Grid Table
    meta_table = doc.add_table(rows=1, cols=4)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_widths = [Inches(1.8), Inches(1.2), Inches(2.2), Inches(1.8)]
    meta_data = [
        ("Author:", " Moazzem Hossain Majumder"),
        ("Date:", " October 2026"),
        ("Live App:", " podcast-companion.onrender.com"),
        ("Code:", " GitHub Public Repository")
    ]
    for i, cell in enumerate(meta_table.rows[0].cells):
        cell.width = meta_widths[i]
        set_cell_shading(cell, COLOR_BG_HEADER)
        set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
        set_cell_borders(cell, top="single", bottom="single", left="none", right="none",
                         color=COLOR_BORDER, sz="6")
        p_m = cell.paragraphs[0]
        p_m.paragraph_format.space_before = Pt(0)
        p_m.paragraph_format.space_after = Pt(0)
        
        lbl, val = meta_data[i]
        r_lbl = p_m.add_run(lbl)
        r_lbl.bold = True
        r_lbl.font.name = "Segoe UI"
        r_lbl.font.size = Pt(8.5)
        r_lbl.font.color.rgb = COLOR_PRIMARY
        
        r_val = p_m.add_run(val)
        r_val.font.name = "Segoe UI"
        r_val.font.size = Pt(8.5)
        r_val.font.color.rgb = COLOR_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # -------------------------------------------------------------
    # SECTION 1
    # -------------------------------------------------------------
    add_section_heading(doc, "1. Why We Built This (User Value)")
    add_paragraph_text(
        doc,
        "Long podcasts are packed with valuable information, but remembering and finding "
        "specific points later is frustrating. Standard AI chatbots usually produce generic "
        "summaries that you cannot verify."
    )
    
    add_highlight_list_box(
        doc,
        "Who benefits most:",
        [
            "**Students & Learners:** Want to quickly review core ideas and test what they learned.",
            "**Busy Listeners:** Need to know in 2 minutes whether an 80-minute episode is worth hearing.",
            "**Readers & Accessibility:** People who retain information better through text than audio.",
            "**Podcast Creators:** Need chapter markers and quiz questions to engage their listeners."
        ]
    )

    add_paragraph_text(
        doc,
        "**The Core Problem Solved:** Instead of guessing, we answer: "
        "*\"Where did the speaker actually say that, and can I trust it?\"* "
        "Every takeaway, chapter, and quiz answer links directly to the exact words in the podcast transcript."
    )

    # -------------------------------------------------------------
    # SECTION 2
    # -------------------------------------------------------------
    add_section_heading(doc, "2. Technical Tools Compared")
    add_paragraph_text(
        doc,
        "We tested multiple free tools to find the best combination for speed, reliability, and cost."
    )

    # 2.A AI Text Models
    add_subheading(doc, "A. AI Text Models (Summaries, Chapters, Quiz)")
    tbl_models = doc.add_table(rows=1, cols=4)
    tbl_models.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths_models = [Inches(1.8), Inches(2.5), Inches(1.6), Inches(1.1)]
    format_table_header(tbl_models.rows[0], widths_models, ["Model", "Key Strengths", "Limitations", "Our Verdict"])

    models_data = [
        (
            "**Google Gemini Flash**",
            "**Huge context window:** Reads 10+ hours in one call. Native JSON support. Generous free tier.",
            "Free tier can experience queue delays during peak traffic hours.",
            "**Primary Choice** (handles long episodes)."
        ),
        (
            "**Groq (GPT-OSS-120B)**",
            "**Super fast:** Answers in 1 to 2 seconds. Reliable JSON mode.",
            "Free tier has an 8,000 token per minute ceiling; cannot fit huge files.",
            "**Fast Backup** & comparison model."
        ),
        (
            "**Hugging Face Router**",
            "Provides access to diverse open-source models with one API key.",
            "Free tier gives small monthly credits that can run out quickly.",
            "**Secondary Fallback**."
        ),
        (
            "**Local Models (Ollama)**",
            "100% private with zero API rate limits.",
            "Needs a powerful computer/GPU. Cannot run on free cloud servers (512MB RAM).",
            "**Rejected** for free cloud hosting."
        ),
    ]
    for idx, row in enumerate(models_data):
        add_styled_row(tbl_models, widths_models, row, is_alt=(idx % 2 == 1))

    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    add_callout_box(
        doc,
        "**Real-World Finding:** AI models retire quickly! While developing, Groq retired `llama-3.3-70b-versatile`. "
        "Because our system makes real API calls, we caught this immediately and upgraded to `openai/gpt-oss-120b`."
    )

    # 2.B Speech-to-Text
    add_subheading(doc, "B. Speech-to-Text (Audio Transcribers)")
    tbl_stt = doc.add_table(rows=1, cols=4)
    tbl_stt.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths_stt = [Inches(1.8), Inches(2.5), Inches(1.6), Inches(1.1)]
    format_table_header(tbl_stt.rows[0], widths_stt, ["Transcriber", "Key Strengths", "Limitations", "Our Verdict"])

    stt_data = [
        (
            "**Groq Whisper**",
            "**Real timestamps:** Second-by-second accuracy via `verbose_json`. Over 200x faster than real-time.",
            "25 MB file size limit on free tier.",
            "**Primary Choice** (we compress and split audio into chunks)."
        ),
        (
            "**Gemini Audio**",
            "Handles many spoken languages well natively.",
            "Timestamps are not dependable; inline audio capped at 20 MB.",
            "**Backup Choice** (drops timestamps honestly)."
        ),
        (
            "**OpenAI Whisper API**",
            "High quality reference implementation.",
            "Requires a paid credit card account.",
            "**Rejected** (breaks free-tier rule)."
        ),
    ]
    for idx, row in enumerate(stt_data):
        add_styled_row(tbl_stt, widths_stt, row, is_alt=(idx % 2 == 1))

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # 2.C Cloud Hosting Platforms
    add_subheading(doc, "C. Cloud Hosting Platforms")
    tbl_host = doc.add_table(rows=1, cols=3)
    tbl_host.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths_host = [Inches(2.0), Inches(3.6), Inches(1.4)]
    format_table_header(tbl_host.rows[0], widths_host, ["Platform", "Findings & Evaluation", "Our Verdict"])

    host_data = [
        (
            "**Render (Free Web Service)**",
            "Runs Python and Docker smoothly without credit cards. Allows audio uploads without small file ceilings. Sleeps after 15 min idle.",
            "**Chosen Host** (Live on Render)."
        ),
        (
            "**Vercel**",
            "Has a strict **4.5 MB request body limit**. Real podcast audio files are 20–60 MB, so Vercel blocks them.",
            "**Rejected** (cannot upload audio)."
        ),
        (
            "**Hugging Face Spaces**",
            "Free Docker compute spaces now require paid accounts for new users.",
            "**Rejected** (requires paid plan)."
        ),
    ]
    for idx, row in enumerate(host_data):
        add_styled_row(tbl_host, widths_host, row, is_alt=(idx % 2 == 1))

    # -------------------------------------------------------------
    # SECTION 3
    # -------------------------------------------------------------
    add_section_heading(doc, "3. How We Keep Answers Trustworthy (Reliability)")
    add_paragraph_text(
        doc,
        "Instead of hoping the AI doesn't hallucinate, our Python backend strictly checks everything:"
    )
    add_bullet_point(
        doc,
        "**Numbered Passages:** The transcript is cut into numbered segments (`Passage 1`, `Passage 2`...). The AI must cite these numbers."
    )
    add_bullet_point(
        doc,
        "**Verbatim Quote Checks:** For quizzes and Q&A, the server searches the transcript to confirm the quote is real word-for-word. Ungrounded questions are discarded."
    )
    add_bullet_point(
        doc,
        "**Honest Timestamps:** Timestamps come only from Whisper or subtitle files (`.srt`/`.vtt`). If plain text is uploaded, the app honestly displays *\"No timestamps available\"* instead of making up fake times."
    )
    add_bullet_point(
        doc,
        "**Server-Side Option Shuffling:** AI models often put the right quiz answer as Option B. We randomize answer positions on the server to prevent bias."
    )
    add_bullet_point(
        doc,
        "**Abstaining on Out-of-Domain Questions:** If a user asks something not in the podcast (like *\"Who won the World Cup?\"*), the system politely refuses instead of guessing."
    )

    # -------------------------------------------------------------
    # SECTION 4
    # -------------------------------------------------------------
    add_section_heading(doc, "4. Safety & Security (OWASP Top 10 API Security)")
    add_bullet_point(
        doc,
        "**File Header Checks (Magic Bytes):** We inspect the binary header of uploaded files. Renaming a text or malicious file to `.mp3` is safely caught and rejected before reaching ffmpeg."
    )
    add_bullet_point(
        doc,
        "**Input Guardrails:** Transcripts under 200 characters or over 150,000 characters are safely rejected with clear HTTP error codes."
    )
    add_bullet_point(
        doc,
        "**Privacy Notice:** Users are informed upfront that free AI tiers may process their inputs, advising against submitting private passwords or confidential records."
    )
    add_bullet_point(
        doc,
        "**Secret Hygiene:** Zero credentials are saved in code or GitHub; all API keys load securely from environment variables."
    )

    # -------------------------------------------------------------
    # SECTION 5
    # -------------------------------------------------------------
    add_section_heading(doc, "5. Measured Benchmark: Gemini vs. Groq Inside Our App")
    add_paragraph_text(
        doc,
        "We ran both models head-to-head on the exact same 11-minute podcast transcript (about 10,300 characters). "
        "Both models were pinned with no hidden fallback:"
    )

    tbl_bench = doc.add_table(rows=1, cols=3)
    tbl_bench.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths_bench = [Inches(2.5), Inches(2.2), Inches(2.3)]
    format_table_header(tbl_bench.rows[0], widths_bench, ["Benchmark Metric", "Google Gemini Flash-Lite", "Groq (GPT-OSS-120B)"])

    bench_data = [
        ("Overview Generation Time", "5.2 seconds", "**1.5 seconds** (over 3x faster)"),
        ("Chapters Generation Time", "1.5 seconds", "1.8 seconds"),
        ("Quiz Generation Time", "5.8 seconds", "**3.5 seconds**"),
        ("Verbatim Quote Check", "**100% Verified** (3 of 3 questions)", "**100% Verified** (3 of 3 questions)"),
        ("Off-Topic Question Refusal", "Refused correctly (no guess)", "Refused correctly (no guess)"),
        ("Maximum Episode Length", "**Huge** (handles 10+ hour audio)", "Medium (limited by 8K tokens/min)"),
    ]
    for idx, row in enumerate(bench_data):
        add_styled_row(tbl_bench, widths_bench, row, is_alt=(idx % 2 == 1))

    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    add_paragraph_text(
        doc,
        "**Takeaway:** Groq is unmatched for speed (1.5 seconds), while Gemini is unmatched for episode length. "
        "Our **Auto mode** uses Groq for speed when possible, and smoothly relies on Gemini for long marathons."
    )

    # -------------------------------------------------------------
    # SECTION 6
    # -------------------------------------------------------------
    add_section_heading(doc, "6. Three Future Improvements (Next Steps)")
    add_numbered_item(
        doc,
        1,
        "**Automated Truthfulness Testing (Highest Priority):** An automated benchmark harness that checks if every summary claim strictly matches the podcast audio without any subtle drift."
    )
    add_numbered_item(
        doc,
        2,
        "**Durable Database & Shareable Links:** Storing episode companions in a lightweight database so users can share permanent links with friends."
    )
    add_numbered_item(
        doc,
        3,
        "**Word-by-Word Streaming:** Streaming tokens over Server-Sent Events (SSE) so users see summary sentences appear instantly as they are generated."
    )

    # -------------------------------------------------------------
    # SECTION 7: References & Evidence
    # -------------------------------------------------------------
    add_section_heading(doc, "7. References & Research Sources")
    add_bullet_point(
        doc,
        "**Edison Research — The UK Podcast Consumer 2025:** Official media study documenting podcast consumption behaviors (51% monthly listeners): `https://www.edisonresearch.com/the-uk-podcast-consumer-2025/`"
    )
    add_bullet_point(
        doc,
        "**OpenAI Speech-to-Text Documentation:** Audio transcription guide and best practices for Whisper implementations: `https://platform.openai.com/docs/guides/speech-to-text`"
    )
    add_bullet_point(
        doc,
        "**OWASP API Security Top 10:** Industry-standard API security recommendations for file uploads, auth, and input sanitization: `https://owasp.org/www-project-api-security/`"
    )
    add_bullet_point(
        doc,
        "**Groq Cloud Documentation:** Ultra-fast inference engine API references and rate limit specifications: `https://console.groq.com/docs`"
    )
    add_bullet_point(
        doc,
        "**Google AI Gemini API Documentation:** Context window architectures and multimodal API references: `https://ai.google.dev/docs`"
    )

    return doc


def generate_doc():
    print("Building Research Word document (.docx)...")
    doc = build_research_document()
    
    path_docs = DOCS / "RESEARCH.docx"
    path_root = ROOT / "RESEARCH.docx"
    
    doc.save(str(path_docs))
    print(f"Created: {path_docs}")
    
    doc.save(str(path_root))
    print(f"Created: {path_root}")


if __name__ == "__main__":
    generate_doc()

