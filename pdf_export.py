"""Turns the agents' markdown-style text into clean PDF files (uses reportlab)."""
import io
import os
import re
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _setup_fonts():
    """Use DejaVu (supports many symbols) if installed, else built-in Helvetica."""
    for folder in (
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
        "/usr/share/fonts/TTF",
    ):
        regular = os.path.join(folder, "DejaVuSans.ttf")
        bold = os.path.join(folder, "DejaVuSans-Bold.ttf")
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont("DJ", regular))
                pdfmetrics.registerFont(TTFont("DJ-B", bold))
                pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-B", italic="DJ", boldItalic="DJ-B")
                return "DJ", "DJ-B", True
            except Exception:
                pass
    return "Helvetica", "Helvetica-Bold", False


_BASE, _BOLD, _UNICODE = _setup_fonts()

_REPLACEMENTS = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2022": "-", "\u2026": "...", "\u00a0": " ",
}


def _clean(text) -> str:
    text = str(text or "").replace("\r", "")
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff\ufe0f]", "", text)  # invisible marks
    text = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF]", "", text)  # emoji (no glyphs in the font)
    if not _UNICODE:
        for a, b in _REPLACEMENTS.items():
            text = text.replace(a, b)
        text = text.encode("latin-1", "replace").decode("latin-1")
    return text


def _styles():
    navy = colors.HexColor("#1F3A5F")
    return {
        "title": ParagraphStyle("title", fontName=_BOLD, fontSize=18, leading=22, textColor=navy, spaceAfter=4),
        "sub": ParagraphStyle("sub", fontName=_BASE, fontSize=9, leading=12, textColor=colors.grey),
        "h1": ParagraphStyle("h1", fontName=_BOLD, fontSize=14, leading=18, textColor=navy, spaceBefore=8, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName=_BOLD, fontSize=12, leading=16, textColor=navy, spaceBefore=6, spaceAfter=3),
        "h3": ParagraphStyle("h3", fontName=_BOLD, fontSize=10.5, leading=14, spaceBefore=4, spaceAfter=2),
        "body": ParagraphStyle("body", fontName=_BASE, fontSize=10, leading=14, spaceAfter=2),
        "bullet": ParagraphStyle("bullet", fontName=_BASE, fontSize=10, leading=14, leftIndent=14, bulletIndent=4),
        "cell": ParagraphStyle("cell", fontName=_BASE, fontSize=8.5, leading=11),
        "cellb": ParagraphStyle("cellb", fontName=_BOLD, fontSize=8.5, leading=11),
    }


def _inline(text: str) -> str:
    t = escape(text)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"__(.+?)__", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    return t


def _para(text, style, **kw):
    try:
        return Paragraph(_inline(text), style, **kw)
    except Exception:
        return Paragraph(escape(text), style, **kw)


def _table(rows, styles, width):
    ncols = max(len(r) for r in rows)
    data = []
    for idx, row in enumerate(rows):
        row = row + [""] * (ncols - len(row))
        style = styles["cellb"] if idx == 0 else styles["cell"]
        data.append([_para(c, style) for c in row])
    tbl = Table(data, colWidths=[width / ncols] * ncols, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tbl


def _md_to_flowables(md: str, styles, width):
    out = []
    lines = _clean(md).split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if not s:
            out.append(Spacer(1, 4))
            i += 1
            continue
        if re.match(r"^[-*_]{3,}$", s):
            out.append(HRFlowable(width="100%", color=colors.lightgrey, spaceBefore=4, spaceAfter=4))
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            level = min(len(m.group(1)) + 1, 3)  # section titles already use h1
            out.append(_para(m.group(2), styles[f"h{level}"]))
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if not re.match(r"^\|?[\s:\-|]+\|?$", row):
                    rows.append([c.strip() for c in row.strip("|").split("|")])
                i += 1
            if rows:
                out.append(_table(rows, styles, width))
                out.append(Spacer(1, 4))
            continue
        m = re.match(r"^(\s*)[-*+\u2022]\s+(.*)", line)
        if m:
            level = len(m.group(1)) // 2
            st = ParagraphStyle("b", parent=styles["bullet"], leftIndent=14 + 10 * level, bulletIndent=4 + 10 * level)
            out.append(_para(m.group(2), st, bulletText="\u2022" if _UNICODE else "-"))
            i += 1
            continue
        m = re.match(r"^(\s*)(\d+[\.\)])\s+(.*)", line)
        if m:
            st = ParagraphStyle("n", parent=styles["body"], leftIndent=16, firstLineIndent=-16)
            out.append(_para(f"{m.group(2)} {m.group(3)}", st))
            i += 1
            continue
        out.append(_para(s, styles["body"]))
        i += 1
    return out


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(_BASE, 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _build(title, subtitle, sections, page_break_between=False) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm, title=_clean(title),
    )
    width = A4[0] - 36 * mm
    styles = _styles()
    story = [Paragraph(escape(_clean(title)), styles["title"]), Paragraph(escape(_clean(subtitle)), styles["sub"]), Spacer(1, 8)]
    for n, (heading, md) in enumerate(sections):
        if page_break_between and n > 0:
            story.append(PageBreak())
        story.append(_para(heading, styles["h1"]))
        story += _md_to_flowables(md, styles, width)
        story.append(Spacer(1, 10))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _stamp() -> str:
    return datetime.now().strftime("Created %Y-%m-%d %H:%M")


def package_pdf(subject: str, pkg: dict) -> bytes:
    sections = [
        ("Topics", pkg.get("topics", "")),
        ("Past paper analysis", pkg.get("past_papers", "")),
        ("Notes", pkg.get("notes", "")),
        ("Practice questions", pkg.get("questions", "")),
    ]
    return _build(f"CSS {subject} - Preparation Package", _stamp(), sections)


def reports_pdf(history: list) -> bytes:
    sections = []
    for h in history:
        md = f"**Question:** {h.get('question', '')}\n\n"
        if h.get("answer"):
            md += f"**Your answer:**\n{h['answer']}\n\n---\n\n"
        md += h.get("report", "")
        sections.append((f"{h.get('time', '')} - {h.get('subject', '')}", md))
    return _build("CSS Answer Assessment Reports", _stamp(), sections, page_break_between=True)


def document_pdf(title: str, sections: list) -> bytes:
    """Generic PDF: sections is a list of (heading, markdown_text)."""
    return _build(title, _stamp(), sections)
