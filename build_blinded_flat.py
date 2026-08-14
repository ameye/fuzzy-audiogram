#!/usr/bin/env python3
"""Flatten the blinded qmd for the reference-format renderer:
- keep YAML title only; move abstract + keywords into the body
- convert [@key] citations to Vancouver [n] + reference list (handles ';' groups)
- flatten LaTeX math to Unicode; strip {#sec-...}; replace @sec-app-math cross-ref
"""
import re, sys
from pathlib import Path

sys.path.insert(0, "/home/hermes/.hermes/skills/research/manuscript-submission/scripts")
import qmd_preprocess as qp

SRC = Path("/opt/data/fuzzy-audiogram/manuscript_eh_blinded.qmd")
BIB = Path("/opt/data/fuzzy-audiogram/references.bib")
DST = Path("/opt/data/fuzzy-audiogram/manuscript_eh_blinded_flat.qmd")

raw = SRC.read_text(encoding="utf-8")

# ---- split YAML ----
m = re.match(r"^---\n(.*?)\n---\n", raw, flags=re.DOTALL)
front, body = m.group(1), raw[m.end():]

title = re.search(r'^title:\s*"([^"]+)"', front, flags=re.M).group(1)

# abstract block: all lines after 'abstract: |' until next top-level key (column-0 word:)
am = re.search(r"^abstract: \|\n(.*?)(?=^\w+:)", front, flags=re.M | re.DOTALL)
abstract_paras = []
if am:
    for line in am.group(1).splitlines():
        line = line.strip()
        if line:
            abstract_paras.append(line)

km = re.search(r"^keywords:\n((?:  - .*\n?)+)", front, flags=re.M)
keywords = []
if km:
    keywords = [re.sub(r"^  - ", "", ln).strip() for ln in km.group(1).splitlines() if ln.strip()]

# ---- flatten body ----
body = qp.flatten_math(body)

# repair nested-brace fractions the flatten pass left behind (backslash already stripped)
def repair_fracs(text):
    def frac(m):
        return f"({m.group(1)})/({m.group(2)})"
    return re.sub(r"\\?frac\{([^{}]*)\}\{([^{}]*)\}", frac, text)

body = repair_fracs(body)
body = re.sub(r"\s*\{#sec-[^}]+}\s*", "\n", body)
body = body.replace("@sec-app-math", "the appendix")
body = re.sub(r":::\s*\{#refs\}\s*:::", "", body)

# ---- citations -> Harvard author-date (Ear and Hearing house style) ----
refs = qp.parse_bib(str(BIB))

def _institutional(author_str):
    a = author_str.strip()
    return a.startswith("{") and a.endswith("}")

def _fix(author_str):
    return qp._fix_latex_chars(author_str)

def _surnames(author_str):
    a = author_str.strip()
    if _institutional(a):
        return [_fix(a[1:-1].strip())]
    names = [n.strip() for n in a.split(" and ") if n.strip() and n.strip().lower() != "others"]
    surs = []
    for n in names:
        if "," in n:
            surs.append(_fix(n.split(",")[0].strip()))
        else:
            surs.append(_fix(n.split()[-1].strip()))
    return surs

def _intext_author(author_str):
    a = author_str.strip()
    if _institutional(a):
        return _fix(a[1:-1].strip())
    surs = _surnames(a)
    if len(surs) == 1:
        return surs[0]
    if len(surs) == 2:
        return f"{surs[0]} and {surs[1]}"
    return f"{surs[0]} et al."

def _list_author(author_str):
    a = author_str.strip()
    if _institutional(a):
        return _fix(a[1:-1].strip())
    names = [n.strip() for n in a.split(" and ") if n.strip() and n.strip().lower() != "others"]
    out = []
    for n in names:
        if "," in n:
            last, rest = n.split(",", 1)
            clean = rest.replace(".", " ")
            toks = [t for t in clean.split() if t]
            if len(toks) == 1 and toks[0].isupper() and toks[0].isalpha():
                initials = toks[0]  # e.g. JY
            else:
                initials = "".join(t[0] for t in toks)
            out.append(f"{_fix(last.strip())}, {initials}")
        else:
            parts = n.split()
            out.append(f"{_fix(parts[-1])}, {''.join(p[0] for p in parts[:-1])}")
    return ", ".join(out)

def _harvard_entry(key, ref):
    authors = _list_author(ref.get("author", ""))
    title = _fix(ref.get("title", ""))
    year = ref.get("year", "")
    if ref["kind"] == "book":
        pub = ref.get("publisher", "")
        addr = ref.get("address", "")
        loc = f"{addr}: " if addr else ""
        return f"{authors} ({year}) {title}. {loc}{pub}."
    journal = _fix(ref.get("journal") or ref.get("booktitle") or "")
    title = title.replace("\\&", "&").replace("\\_", "_").replace("\\%", "%")
    journal = journal.replace("\\&", "&").replace("\\_", "_").replace("\\%", "%")
    vol = ref.get("volume", "")
    num = ref.get("number", "")
    pages = ref.get("pages", "").replace("--", "\u2013")
    volpart = f"{vol}({num})" if num else vol
    parts = [p for p in [journal, volpart, f"pp. {pages}" if pages else ""] if p]
    entry = f"{authors} ({year}) {title}. " + ", ".join(parts) + "."
    if ref.get("doi"):
        entry += f" doi: {ref['doi']}"
    return entry

def _is_narrative(before, key):
    """True if the citation reads as narrative (author surname already in the sentence)."""
    if key not in refs:
        return False
    surs = _surnames(refs[key].get("author", ""))
    window = before[-80:]
    tokens = [t for t in (t.strip("*").strip(".,;:()[]") for t in
                          re.findall(r"[\w\u00c0-\u024f.-]+|et|al\.", window)) if t]
    last3 = [t.lower() for t in tokens[-3:]]
    for s in surs[:2]:
        if s.lower() in last3:
            return True
    return "et" in last3 and "al" in last3

out_parts_body, pos, keys = [], 0, []
for cm in re.finditer(r"\[@([^\]]+)\]", body):
    out_parts_body.append(body[pos:cm.start()])
    ks = [x.strip().lstrip("@") for x in re.split(r"[;,]", cm.group(1)) if x.strip()]
    for k in ks:
        if k not in keys:
            keys.append(k)
    before = body[cm.start() - 80:cm.start()]
    if len(ks) == 1:
        k = ks[0]
        ref = refs.get(k)
        if not ref:
            out_parts_body.append(f"[{k}?]")
        elif _is_narrative(before, k):
            out_parts_body.append(f"({ref.get('year', '')})")
        else:
            out_parts_body.append(f"({_intext_author(ref.get('author', ''))}, {ref.get('year', '')})")
    else:
        bits = []
        for k in ks:
            ref = refs.get(k, {})
            bits.append(f"{_intext_author(ref.get('author', ''))}, {ref.get('year', '')}")
        out_parts_body.append("(" + "; ".join(bits) + ")")
    pos = cm.end()
out_parts_body.append(body[pos:])
body = "".join(out_parts_body)

order = sorted(
    keys,
    key=lambda k: (_surnames(refs[k].get("author", ""))[0].lower() if k in refs else k,
                   refs[k].get("year", "") if k in refs else ""),
)
ref_lines = ["# References", ""]
for k in order:
    if k in refs:
        ref_lines.append(_harvard_entry(k, refs[k]))
    else:
        ref_lines.append(f"{k} (reference not found in references.bib)")
body = re.sub(r"# References\n.*?(?=\n# |\Z)", lambda m: "\n".join(ref_lines) + "\n", body, flags=re.DOTALL)

# ---- assemble: YAML title + abstract + keywords + body ----
out_parts = [f'---\ntitle: "{title}"\n---\n\n']
for p in abstract_paras:
    out_parts.append(p + "\n\n")
if keywords:
    out_parts.append("**Keywords:** " + "; ".join(keywords) + "\n\n")
out_parts.append(body.strip() + "\n")
out = "".join(out_parts)

# ---- audit ----
print("title:", title[:70])
print("abstract paras:", len(abstract_paras))
print("keywords:", len(keywords))
print("citation keys:", len(keys), keys)
leftover = re.findall(r"\[@[^\]]+\]|@sec-|\$\$|\$[^$\n]+?\$|\\frac|\\mu|\\begin", out)
print("residue (citations/math):", leftover or "NONE")
print("identifying leaks:", [s for s in ["Ameye", "ameye", "Tabuk", "King Fahad", "sanyaameye", "github.com"] if s in out] or "NONE")

DST.write_text(out, encoding="utf-8")
print("wrote", DST)
