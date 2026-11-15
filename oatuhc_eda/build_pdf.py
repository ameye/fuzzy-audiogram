"""Build the print PDF of EDA_REPORT.md: markdown -> HTML -> LibreOffice.

The HTML is written next to the report and the PDF is produced with the
LibreOffice binary provided at /opt/data/lo/soffice.sh, which is the only
document engine available on this host (no pandoc, no Chromium).

Usage:  python build_pdf.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE / "EDA_REPORT.md"
HTML = HERE / "EDA_REPORT.html"
PDF = HERE / "EDA_REPORT.pdf"
SOFFICE = Path("/opt/data/lo/soffice.sh")

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 9.6pt; line-height: 1.42;
       color: #1b1b1f; }
h1 { font-family: "DejaVu Sans", sans-serif; font-size: 18pt; line-height: 1.2;
     margin: 0 0 10pt 0; color: #1b1b1f; }
h2 { font-family: "DejaVu Sans", sans-serif; font-size: 13pt; margin: 20pt 0 6pt 0;
     border-bottom: 1px solid #c9c9d0; padding-bottom: 3pt; page-break-after: avoid; }
h3 { font-family: "DejaVu Sans", sans-serif; font-size: 10.8pt; margin: 14pt 0 4pt 0;
     page-break-after: avoid; }
p { margin: 0 0 6pt 0; text-align: justify; }
strong { color: #101014; }
hr { border: none; border-top: 1px solid #d9d9de; margin: 14pt 0; }
ul, ol { margin: 0 0 8pt 0; padding-left: 16pt; }
li { margin-bottom: 3pt; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt;
       background: #f2f2f5; padding: 0 2pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 12pt 0; font-size: 8.2pt;
        page-break-inside: avoid; }
th { background: #eef1f5; border: 0.5pt solid #b9bcc4; padding: 3pt 4pt; text-align: left;
     font-family: "DejaVu Sans", sans-serif; font-size: 8pt; }
td { border: 0.5pt solid #c9ccd3; padding: 2.5pt 4pt; vertical-align: top; }
tr:nth-child(even) td { background: #fafafb; }
img { max-width: 100%; height: auto; display: block; margin: 8pt auto 2pt auto;
      page-break-inside: avoid; }
p > img { page-break-inside: avoid; }
"""


def main() -> int:
    text = SRC.read_text()
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    # This LibreOffice build's Writer/Web import cannot read file: URLs or
    # paths relative to the HTML when run headless (it silently drops the
    # image), but it does accept inline base64 data URIs. Every figure is
    # therefore embedded in the HTML before conversion.
    import base64

    def _inline(m):
        rel = m.group(1)
        data = base64.b64encode((HERE / rel).read_bytes()).decode("ascii")
        return f'src="data:image/png;base64,{data}"'

    body, n = re.subn(r'src="(figures/[^"]+\.png)"', _inline, body)
    print(f"inlined {n} images")

    html = f"""<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8">
<title>OAUTHC FAI validation: exploratory data analysis</title>
<style>{CSS}</style></head>
<body>
{body}
</body></html>"""
    HTML.write_text(html, encoding="utf-8")
    print(f"wrote {HTML.name} ({len(html)/1024:.0f} kB)")

    if PDF.exists():
        PDF.unlink()
    cmd = [str(SOFFICE), "--convert-to", "pdf", "--outdir", str(HERE), str(HTML)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    print(res.stdout.strip() or res.stderr.strip())
    if not PDF.exists():
        print("PDF was not produced", file=sys.stderr)
        return 1

    from pypdf import PdfReader
    r = PdfReader(str(PDF))
    n_img = 0
    pages_with = 0
    for page in r.pages:
        res = page.get("/Resources") or {}
        xo = res.get("/XObject")
        if not xo:
            continue
        xo = xo.get_object()
        k = sum(1 for name in xo if xo[name].get_object().get("/Subtype") == "/Image")
        n_img += k
        pages_with += 1 if k else 0
    print(f"{PDF.name}: {len(r.pages)} pages, {n_img} embedded images on {pages_with} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
