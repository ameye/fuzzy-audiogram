"""Build a readable PDF of the manuscript for author review.

The DOCX that pandoc produces is the submission artefact; this renders the same
document to a single PDF with the four figures inlined at their captions, which is
easier to read end to end than a DOCX with separately shipped artwork.

Document order is preserved by walking the body's block-level elements rather than
reading paragraphs and tables as two separate lists, which would put every table in
the wrong place.

Run:  python3 scripts/make_reading_pdf.py
Writes: manuscript/Manuscript_CMPB_v4_reading.pdf
"""
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MS = ROOT / "manuscript"
DOCX = MS / "Manuscript_CMPB_v4.docx"
OUT = MS / "Manuscript_CMPB_v4_reading.pdf"
FIGDIR = MS / "figures"

# figure number -> file, matched to the "**Figure N.**" captions
FIGURES = {
    "1": "fig1_membership_partition.png",
    "2": "fig2_agreement.png",
    "3": "fig3_decision_curve.png",
    "4": "fig4_cases.png",
}

CSS = """
@page { size: A4; margin: 20mm 18mm; @bottom-center { content: counter(page); font-size: 9pt; color: #666; } }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 10.5pt; line-height: 1.45; color: #111; }
h1 { font-size: 16pt; margin: 0 0 10pt 0; line-height: 1.25; }
h2 { font-size: 12.5pt; margin: 16pt 0 6pt 0; border-bottom: 0.6pt solid #999; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 12pt 0 4pt 0; }
p { margin: 0 0 6pt 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt 0; font-size: 9pt; }
th, td { border: 0.5pt solid #bbb; padding: 3pt 4pt; text-align: left; vertical-align: top; }
th { background: #eee; }
.figure { margin: 8pt 0 12pt 0; page-break-inside: avoid; }
.figure img { width: 100%; }
.caption { font-size: 9.5pt; color: #222; text-align: justify; }
.note { font-size: 9pt; color: #333; }
figure { page-break-inside: avoid; }
"""


def blocks(doc):
    """Yield ('p', paragraph) and ('t', table) in true document order."""
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield "p", Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield "t", Table(child, doc)


def para_html(p):
    style = (p.style.name or "").lower()
    text = p.text.strip()
    if not text:
        return "", None
    esc = html.escape(text)
    if style.startswith("heading 1") or style == "title":
        return f"<h1>{esc}</h1>", text
    if style.startswith("heading 2"):
        return f"<h2>{esc}</h2>", text
    if style.startswith("heading 3"):
        return f"<h3>{esc}</h3>", text
    if text.startswith("**Table"):
        return f'<p class="caption">{esc}</p>', text
    if text.startswith("Note."):
        return f'<p class="note">{esc}</p>', text
    return f"<p>{esc}</p>", text


def table_html(t):
    rows = []
    for i, r in enumerate(t.rows):
        cells = [html.escape(c.text.strip()) for c in r.cells]
        tag = "th" if i == 0 else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


def main():
    try:
        from docx import Document
    except ImportError:
        sys.exit("  python-docx is required")
    try:
        from weasyprint import HTML
    except ImportError:
        sys.exit("  weasyprint is required")

    doc = Document(str(DOCX))
    parts, pending = [], None
    for kind, blk in blocks(doc):
        if kind == "t":
            parts.append(table_html(blk))
            continue
        frag, text = para_html(blk)
        if not frag:
            continue
        # a figure caption means the artwork belongs immediately before it
        if text and text.startswith("**Figure ") and text[10:11].isdigit():
            n = text[10:11]
            f = FIGDIR / FIGURES.get(n, "")
            if f.exists():
                parts.append(f'<div class="figure"><img src="{f.as_uri()}"/></div>')
        parts.append(frag)

    doc_html = ("<!doctype html><html><head><meta charset='utf-8'>"
                f"<style>{CSS}</style></head><body>" + "".join(parts) + "</body></html>")
    HTML(string=doc_html, base_url=str(ROOT)).write_pdf(str(OUT))
    size = OUT.stat().st_size
    print(f"  wrote {OUT.relative_to(ROOT)}  ({size/1024:.0f} KB)")
    print(f"  figures inlined: {sum(1 for f in FIGURES.values() if (FIGDIR/f).exists())}")


if __name__ == "__main__":
    main()
