"""Build the print PDF of EDA_VISUAL_REPORT.md: markdown -> HTML -> LibreOffice.

The HTML is written next to the report and converted with the LibreOffice
binary at /opt/data/lo/soffice.sh. This build's Writer/Web import cannot read
``file:`` URLs or paths relative to the HTML when run headless, and silently
drops such an image, so every figure is embedded as a base64 data URI before
conversion. The image check at the end parses each page's content stream and
counts the ``Do`` operators that invoke an image XObject, rather than trusting
the HTML that went in.

Usage:  python build_visual_pdf.py
"""
from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE / "EDA_VISUAL_REPORT.md"
HTML = HERE / "EDA_VISUAL_REPORT.html"
PDF = HERE / "EDA_VISUAL_REPORT.pdf"
SOFFICE = Path("/opt/data/lo/soffice.sh")

CSS = """
@page { size: A4; margin: 17mm 16mm 17mm 16mm; }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 9.7pt; line-height: 1.44;
       color: #17171B; }
h1 { font-family: "DejaVu Sans", sans-serif; font-size: 23pt; line-height: 1.12;
     margin: 0 0 6pt 0; color: #17171B; }
h2 { font-family: "DejaVu Sans", sans-serif; font-size: 14.5pt; color: #1F6F6B;
     margin: 0 0 10pt 0; padding-bottom: 4pt; border-bottom: 1.2pt solid #1F6F6B;
     page-break-before: always; page-break-after: avoid; }
h3 { font-family: "DejaVu Sans", sans-serif; font-size: 11.4pt; color: #17171B;
     margin: 16pt 0 5pt 0; page-break-after: avoid; }
p { margin: 0 0 6.5pt 0; text-align: justify; }
strong { color: #101014; }
em { color: #2E2E36; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.2pt;
       background: #F2F1EC; padding: 0 2pt; }
hr { border: none; border-top: 1pt solid #D3D3DB; margin: 12pt 0; }
ul, ol { margin: 0 0 8pt 0; padding-left: 14pt; }
li { margin-bottom: 3pt; }
img { width: 17.2cm; height: auto; display: block; margin: 8pt auto 3pt auto;
      page-break-inside: avoid; }
p > img { page-break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 7pt 0 10pt 0; font-size: 7.7pt;
        page-break-inside: auto; }
table.data tr { page-break-inside: avoid; }
table.data th { background: #EDF0F3; border: 0.5pt solid #B9BCC4; padding: 3pt 4pt;
                text-align: left; font-family: "DejaVu Sans", sans-serif; font-size: 7.8pt; }
table.data td { border: 0.5pt solid #C9CCD3; padding: 2.4pt 4pt; vertical-align: top; }
table.band td { padding: 0; margin: 0; border: none; page-break-inside: avoid; }
table.band tr { page-break-inside: avoid; }
table.band { margin: 5pt 0 9pt 0; page-break-inside: avoid; }
"""


CELL = re.compile(r"<(td|th)([^>]*)>(.*?)</\1>", re.S)


def _style_cell(m):
    tag, attrs, inner = m.group(1), m.group(2), m.group(3)
    if tag == "th" and "bgcolor" not in attrs:
        attrs += ' bgcolor="#EDF0F3"'
    if "valign" not in attrs:
        attrs += ' valign="top"'
    return (f'<{tag}{attrs}><p style="font-size:7.6pt;line-height:1.15;'
            f'margin:1pt 0 1pt 0">{inner}</p></{tag}>')


def class_tables(html: str) -> str:
    """Rewrite data tables for LibreOffice's Writer/Web import.

    That importer ignores CSS on tables entirely, so the grid has to be asked
    for with HTML attributes (border, cellpadding) and the type size has to be
    set on a paragraph inside each cell. Band tables already carry bgcolor and
    are left alone.
    """
    out, i = [], 0
    for m in re.finditer(r"<table.*?</table>", html, re.S):
        block = m.group(0)
        if "bgcolor" in block:
            block = block.replace("<table", '<table class="band"', 1)
        elif "<th" in block:
            block = block.replace("<table", '<table class="data" border="1" '
                                           'cellpadding="2" cellspacing="0"', 1)
            block = CELL.sub(_style_cell, block)
        out.append(html[i:m.start()])
        out.append(block)
        i = m.end()
    out.append(html[i:])
    return "".join(out)


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    body = class_tables(body)

    # Embed every figure as a data URI at 650 px wide (17.2 cm at 96 dpi).
    def _inline(m):
        rel = m.group(1)
        path = HERE / rel
        if not path.exists():
            raise SystemExit(f"missing figure: {rel}")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'width="650" src="data:image/png;base64,{data}"'

    body, n = re.subn(r'src="((?:figures|visual)/[^"]+\.png)"', _inline, body)
    print(f"inlined {n} images")

    html = (f'<!DOCTYPE html>\n<html lang="en-GB"><head><meta charset="utf-8">\n'
            f"<title>OAUTHC FAI validation: a visual analysis</title>\n"
            f"<style>{CSS}</style></head>\n<body>\n{body}\n</body></html>")
    HTML.write_text(html, encoding="utf-8")
    print(f"wrote {HTML.name} ({len(html) / 1024 / 1024:.1f} MB)")

    if PDF.exists():
        PDF.unlink()
    res = subprocess.run([str(SOFFICE), "--convert-to", "pdf", "--outdir",
                          str(HERE), str(HTML)],
                         capture_output=True, text=True, timeout=900)
    print((res.stdout or res.stderr).strip())
    if not PDF.exists():
        print("PDF was not produced", file=sys.stderr)
        return 1

    # ---- verify: parse content streams, do not trust the HTML -------------
    from pypdf import PdfReader
    from pypdf.generic import ContentStream

    r = PdfReader(str(PDF))
    total_do = 0
    pages_with = 0
    per_page = []
    for pno, page in enumerate(r.pages, 1):
        res_d = page.get("/Resources") or {}
        xo = res_d.get("/XObject")
        images = set()
        if xo:
            xo = xo.get_object()
            for name in xo:
                if xo[name].get_object().get("/Subtype") == "/Image":
                    images.add(name)
        do = 0
        if images:
            try:
                cs = ContentStream(page.get_contents(), r)
                for operands, op in cs.operations:
                    if op == b"Do" and operands:
                        if str(operands[0]) in images:
                            do += 1
            except Exception:
                do = 0
        total_do += do
        pages_with += 1 if do else 0
        per_page.append((pno, do))

    print(f"{PDF.name}: {len(r.pages)} pages, {total_do} image draws "
          f"on {pages_with} pages")
    blank = [p for p, d in per_page if d == 0]
    print(f"pages without an image: {blank}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
