#!/usr/bin/env python3
"""Render access_schema_spec.md → PDF via reportlab (same pattern as other docs)."""
import re, os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Preformatted,
                                Table, TableStyle, HRFlowable, PageBreak)
from reportlab.lib import colors

SRC = Path("/workspace/fuzzy-audiogram/oatuhc_protocol/access_schema_spec.md")
OUT = Path("/workspace/fuzzy-audiogram/oatuhc_protocol/access_schema_spec.pdf")

NAVY = HexColor("#1a3a5c")
TEAL = HexColor("#2a7a6f")

doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                        topMargin=18*mm, bottomMargin=16*mm,
                        leftMargin=18*mm, rightMargin=18*mm)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('PTitle', parent=styles['Normal'], fontName='Helvetica-Bold',
                          fontSize=15, leading=19, textColor=NAVY, spaceAfter=4))
styles.add(ParagraphStyle('PSub', parent=styles['Normal'], fontName='Helvetica-Oblique',
                          fontSize=10, leading=13, textColor=TEAL, spaceAfter=10))
styles.add(ParagraphStyle('H1', parent=styles['Normal'], fontName='Helvetica-Bold',
                          fontSize=12.5, leading=16, textColor=NAVY, spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle('H2', parent=styles['Normal'], fontName='Helvetica-Bold',
                          fontSize=11, leading=14, textColor=TEAL, spaceBefore=8, spaceAfter=3))
styles.add(ParagraphStyle('BodyTxt', parent=styles['Normal'], fontName='Helvetica',
                          fontSize=9, leading=12, spaceAfter=4))
styles.add(ParagraphStyle('BulletItem', parent=styles['Normal'], fontName='Helvetica',
                          fontSize=9, leading=12, leftIndent=10, spaceAfter=2))
styles.add(ParagraphStyle('CodeBlock', parent=styles['Normal'], fontName='Courier',
                          fontSize=7.5, leading=9.5, textColor=HexColor('#333333'),
                          backColor=HexColor('#f4f4f4'), leftIndent=8, spaceBefore=3, spaceAfter=6))
styles.add(ParagraphStyle('CaptionT', parent=styles['Normal'], fontName='Helvetica-Oblique',
                          fontSize=8, leading=10, textColor=HexColor('#666666')))

story = []
lines = SRC.read_text().splitlines()
i = 0
code_buf = []
in_code = False

def flush_code():
    global code_buf
    if code_buf:
        story.append(Preformatted("\n".join(code_buf), styles['CodeBlock']))
        code_buf = []

while i < len(lines):
    ln = lines[i]
    s = ln.rstrip()
    if s.startswith("```"):
        if in_code:
            flush_code()
            in_code = False
        else:
            flush_code()
            in_code = True
        i += 1
        continue
    if in_code:
        code_buf.append(s)
        i += 1
        continue
    if s.startswith("# "):
        flush_code()
        story.append(Paragraph(s[2:], styles['PTitle']))
    elif s.startswith("## "):
        flush_code()
        story.append(Paragraph(s[3:], styles['H1']))
    elif s.startswith("### "):
        flush_code()
        story.append(Paragraph(s[4:], styles['H2']))
    elif s.startswith("|") and i+1 < len(lines) and lines[i+1].strip().startswith("|---"):
        # markdown table
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if not all(set(c) <= {"-", ":"} for c in cells):
                rows.append(cells)
            i += 1
        if rows:
            t = Table(rows, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), NAVY),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTSIZE', (0,0), (-1,-1), 7.5),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 0.4, HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, HexColor('#eef2f7')]),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(t)
            story.append(Spacer(1, 4))
        continue
    elif s.startswith("- "):
        story.append(Paragraph("• " + s[2:], styles['BulletItem']))
    elif s.startswith("---"):
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#bbbbbb')))
    elif s.strip() == "":
        pass
    else:
        text = s
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', text)
        text = text.replace("&", "&amp;")
        story.append(Paragraph(text, styles['BodyTxt']))
    i += 1
flush_code()

doc.build(story)
print(f"✅ PDF generated: {OUT}")
print(f"   Size: {OUT.stat().st_size:,} bytes")
