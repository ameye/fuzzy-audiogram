#!/bin/bash
# Render pptx -> pdf -> jpgs for visual QA (user-space LibreOffice bootstrap)
export HOME=/tmp/lo-home
mkdir -p "$HOME"
export LD_LIBRARY_PATH=/tmp/lo-libs/root/usr/lib/x86_64-linux-gnu:/tmp/lo-extract/opt/libreoffice25.8/program:$LD_LIBRARY_PATH
cd /opt/data/fuzzy-audiogram/arabcic2026
rm -rf qa && mkdir -p qa
/tmp/lo-extract/opt/libreoffice25.8/program/soffice --headless --convert-to pdf --outdir qa arabcic2026_fuzzy_audiogram.pptx 2>&1 | tail -1
python3 - << 'PYEOF'
import sys
sys.path.insert(0, '/home/hermes/.hermes/home/.local/lib/python3.13/site-packages')
import fitz
doc = fitz.open("qa/arabcic2026_fuzzy_audiogram.pdf")
print("pages:", len(doc))
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=110)
    pix.save(f"qa/slide-{i+1:02d}.jpg")
print("saved", len(doc), "jpgs")
PYEOF
ls qa/slide-*.jpg | wc -l
