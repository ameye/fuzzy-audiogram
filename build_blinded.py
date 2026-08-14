#!/usr/bin/env python3
"""Build a blinded submission manuscript (Word) from manuscript_eh.qmd.

Blinding rules (Ear and Hearing / Editorial Manager style):
- No title page (no authors, affiliations, email, orcid, running head, date)
- No acknowledgements, no author contributions
- No figures, no tables, no figure-caption section
- Remove identifying info: author name, hospital, city, repo URL (ameye/...)
- Keep: title, abstract, keywords, body text, appendix, references
"""
import re

SRC = "/opt/data/fuzzy-audiogram/manuscript_eh.qmd"
DST = "/opt/data/fuzzy-audiogram/manuscript_eh_blinded.qmd"

raw = open(SRC, encoding="utf-8").read()

# ---- 1. Rebuild YAML frontmatter (strip identifying/metadata fields) ----
m = re.match(r"^---\n(.*?)\n---\n", raw, flags=re.DOTALL)
front = m.group(1)
body = raw[m.end():]

def yaml_field(name):
    mm = re.search(rf"^{name}:\s*(\|?\s*.*?)(?=^\w+:|^---)", front, flags=re.M | re.DOTALL)
    return mm.group(1) if mm else None

title = re.search(r'^title:\s*"([^"]+)"', front, flags=re.M).group(1)
abstract = yaml_field("abstract")
keywords = yaml_field("keywords") or ""

# Normalise the keywords block to a clean YAML list (items may be captured
# without their leading newline, which would glue the first item onto the key).
kw_items = re.findall(r"-\s*(.+)", keywords)
keywords_block = "\n".join(f"  - {k.strip()}" for k in kw_items)

new_front = f"""---
title: "{title}"
format:
  docx:
    toc: false
    number-sections: true
bibliography: references.bib
abstract: {abstract.strip()}
keywords:
{keywords_block}
---
"""
assert "Ameye" not in new_front and "ameye" not in new_front, "identifying text leaked into frontmatter"

# ---- 2. Remove image embeds (standalone figure lines, incl. multiline captions) ----
body, n_img = re.subn(r"!\[.*?\]\(figures/[^)]+\)\{#[^}]*\}\s*\n?", "", body, flags=re.DOTALL)

# ---- 3. Remove pipe tables (contiguous lines starting with |) ----
body, n_tbl = re.subn(r"(?m)^\|.*\n(?:^\|.*\n)*", "", body)

# ---- 4. Remove the accuracy-table footnote that dangles after table removal ----
body = body.replace(
    "*PTA-4 is the reference standard for clear cases by definition; "
    "borderline accuracy reflects discrepancy within \u00b15 dB of thresholds.\n", ""
)

# ---- 5. Remove Acknowledgements section (up to next # heading) ----
body, n_ack = re.subn(r"# Acknowledgements.*?(?=# )", "", body, flags=re.DOTALL)

# ---- 6. Truncate everything after the References div (Tables, Figure Captions, footer) ----
idx = body.find("# References")
assert idx != -1
body = body[:idx + len("# References") + 1]
# drop any trailing "---" separators after the refs div
body = body.rstrip()
body = re.sub(r"\n---\s*$", "", body)

# ---- 7. Anonymize identifying repo URLs ----
body = body.replace(
    "A complete set of EDA visualisations is in the supplementary materials and the "
    "analysis repository (https://github.com/ameye/fuzzy-audiogram).",
    "A complete set of EDA visualisations is in the supplementary materials.")
body = body.replace(
    "Source code is at [https://github.com/ameye/fuzzy-audiogram](https://github.com/ameye/fuzzy-audiogram).",
    "Analysis source code is available from the corresponding author on request.")
body = body.replace(
    "Analysis source code is at https://github.com/ameye/fuzzy-audiogram.",
    "Analysis source code is available from the corresponding author on request.")

# ---- 8. Fix dangling-colon sentences where tables were removed ----
body = body.replace(
    "The optimised parameters from the training set were:",
    "The optimised parameters from the training set are provided in the supplementary material.")
body = body.replace(
    "we looked at classification at the normal/mild boundary:",
    "we looked at classification at the normal/mild boundary.")

out = new_front + "\n" + body.strip() + "\n"

# ---- 9. Blinding audit ----
identifying = ["Ameye", "ameye", "King Fahad", "Tabuk", "sanyaameye",
               "github.com/ameye", "Dr Sanyaolu", "0000-0000-0000-0000"]
leaks = [s for s in identifying if s in out]
print(f"images removed: {n_img}, tables removed: {n_tbl}, ack removed: {n_ack}")
print("identifying leaks:", leaks or "NONE")
print("figure embeds left:", len(re.findall(r"!\[", out)))
print("pipe-table lines left:", len(re.findall(r"(?m)^\|", out)))
print("word count (incl. refs):", len(out.split()))

open(DST, "w", encoding="utf-8").write(out)
print("wrote", DST)
