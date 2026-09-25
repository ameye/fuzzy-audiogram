#!/usr/bin/env python3
"""Build the CMPB manuscript DOCX."""
import pypandoc, os
# Build in this file's own directory. It previously pointed at cmbp_v2/, the
# superseded scratch dir, so builds landed there and this tree's DOCX silently
# went stale.
os.chdir(os.path.dirname(os.path.abspath(__file__)))
pypandoc.convert_file("manuscript_v4.qmd", "docx",
    format="markdown+pipe_tables+raw_attribute",
    outputfile="Manuscript_CMPB_v4.docx",
    extra_args=["--reference-doc=cmbp_reference.docx", "--citeproc",
                "--bibliography=references_v2.bib", "--csl=elsevier-vancouver.csl",
                "--number-sections"])
print("  built Manuscript_CMPB_v4.docx")
