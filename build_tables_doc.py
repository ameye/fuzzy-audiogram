#!/usr/bin/env python3
"""Extract all 9 tables from manuscript_eh.qmd and build a tables-only qmd for
the reference-format renderer. Formal Tables 1-4 keep their manuscript captions;
the 5 inline tables become Tables 5-9 with descriptive captions.
"""
import re
from pathlib import Path

SRC = Path("/opt/data/fuzzy-audiogram/manuscript_eh.qmd")
DST = Path("/opt/data/fuzzy-audiogram/eh_submission/tables.qmd")

text = SRC.read_text(encoding="utf-8")

# strip YAML frontmatter
text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)

# collect headings with positions
headings = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^##?\s+(.*)", text, flags=re.M)]
def context(pos):
    cur = ""
    for hpos, htxt in headings:
        if hpos < pos:
            cur = htxt
        else:
            break
    return cur

# find pipe-table blocks in order
blocks = []
for m in re.finditer(r"(?m)^\|.*\n(?:^\|.*\n)*", text):
    rows = m.group(0).strip().split("\n")
    data = [r.strip().strip("|") for r in rows]
    data = [r for r in data if r and not re.fullmatch(r"[\s\-:|]+", r)]
    ctx = context(m.start())
    blocks.append((m.start(), ctx, data))

# footnote lines following a table (non-pipe, starts with *)
footnotes = {}
for m in re.finditer(r"(?m)^\*(.*)$", text):
    # attach to the last table block before it, within 6 lines
    for start, ctx, data in reversed(blocks):
        if m.start() > start and m.start() - start < 500:
            footnotes[start] = m.group(1).strip()
            break

# formal Tables section captions (## Table N. ...)
formal = {}
for m in re.finditer(r"^## Table (\d+)\.\s*(.*)", text, flags=re.M):
    formal[int(m.group(1))] = m.group(2).strip()

INLINE_CAPTIONS = {
    # keyed by first cell of the table (unique headers)
    "Category|a|b|c|d": "Optimised trapezoidal membership function parameters (a, b, c, d) for the six hearing loss severity categories.",
    "Model|Description|Target": "Comparator models evaluated on the held-out test set.",
    "Method|vs. Reference \u03ba|Borderline Accuracy|Clear-case Accuracy": "Classification agreement of the FAI versus comparators, with accuracy stratified by borderline and clear-case status.",
    "PTA-4|Crisp Label|Fuzzy Label|FAI Score|Normal \u03bc|Mild \u03bc": "Classification at the normal/mild boundary: crisp labels versus graded fuzzy output across the 24\u201330 dB HL range.",
    "Case|PTA-4|WHO Grade|FAI|Configuration|Key Finding": "Summary of the four clinical case studies (A\u2013D).",
}

# order: formal Tables 1-4 first (in manuscript Tables section order), then inline in body order
# find blocks belonging to the formal section (after "# Tables")
formal_idx = text.find("# Tables")
formal_blocks = [b for b in blocks if formal_idx >= 0 and b[0] > formal_idx]
body_blocks = [b for b in blocks if formal_idx < 0 or b[0] < formal_idx]

formal_blocks.sort(key=lambda b: b[0])
body_blocks.sort(key=lambda b: b[0])

def first_header(data):
    if not data:
        return ""
    cells = [c.strip() for c in data[0].strip().strip("|").split("|")]
    return "|".join(cells)

def fmt_table(num, caption, data, foot=None):
    lines = [f"**Table {num}. {caption}**", ""]
    for row in data:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        lines.append("| " + " | ".join(cells) + " |")
    if foot:
        lines.append("")
        lines.append(foot)
    lines.append("")
    return "\n".join(lines)

out = ["---", 'title: "Tables"', "---", ""]

# formal tables first
for start, ctx, data in formal_blocks:
    # identify table number from caption context (## Table N.)
    num = None
    for n, cap in formal.items():
        # match by nearest heading above
        pass
    # find the heading "## Table N." directly above this block
    above = [h for h in headings if h[0] < start]
    htxt = above[-1][1] if above else ""
    m = re.match(r"Table (\d+)\.\s*(.*)", htxt)
    if m:
        num = int(m.group(1))
        cap = m.group(2)
    else:
        num = len(formal_blocks)  # fallback
        cap = htxt
    foot = footnotes.get(start)
    out.append(fmt_table(num, cap, data, foot))

# inline tables as 5..9
inline_num = len(formal_blocks) + 1
for start, ctx, data in body_blocks:
    key = first_header(data)
    cap = INLINE_CAPTIONS.get(key, f"Table (context: {ctx})")
    foot = footnotes.get(start)
    out.append(fmt_table(inline_num, cap, data, foot))
    inline_num += 1

DST.write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote", DST)
print("formal tables:", len(formal_blocks), "| inline tables:", len(body_blocks))
