#!/usr/bin/env python3
"""Build the CMPB v3 manuscript DOCX."""
import pypandoc, os
os.chdir("/opt/data/fuzzy-audiogram/cmbp_v2")
pypandoc.convert_file("manuscript_v4.qmd", "docx",
    format="markdown+pipe_tables+raw_attribute",
    outputfile="Manuscript_CMPB_v4.docx",
    extra_args=["--reference-doc=cmbp_reference.docx", "--citeproc",
                "--bibliography=references_v2.bib", "--csl=elsevier-vancouver.csl",
                "--number-sections"])
print("  built Manuscript_CMPB_v4.docx")
