#!/usr/bin/env python3
"""Build the manuscript PDF and DOCX from the .qmd sources.

The project was rendered with Quarto, which is not installed in this
environment. Pandoc plus Tectonic produces the same document from the same
Markdown: a numbered article PDF with embedded figures and a cited bibliography.
Quarto-only shortcodes and cross-reference syntax (``@fig-2``) are not resolved
here, so those degrade to plain text; everything a reader needs is present.

Usage:  python scripts/build_documents.py [manuscript.qmd ...]
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANDOC = "/opt/data/.venv_fuzzy/lib/python3.13/site-packages/pypandoc/files/pandoc"
TECTONIC = "/tmp/tectonic"

PREAMBLE = r"""
\usepackage{fontspec}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{float}
\let\oldincludegraphics\includegraphics
\renewcommand{\includegraphics}[2][]{\oldincludegraphics[width=0.92\linewidth,#1]{#2}}
"""


def strip_quarto_only(text: str) -> str:
    """Remove constructs pandoc cannot render and that carry no content."""
    # ::: {.callout-...} blocks and bare ::: fences
    text = re.sub(r"^:::\s*\{[^}]*\}\s*$", "", text, flags=re.M)
    text = re.sub(r"^:::\s*$", "", text, flags=re.M)
    # {{< ... >}} shortcodes
    text = re.sub(r"\{\{<.*?>\}\}", "", text)
    # Pandoc renders the Quarto author map (name/email/orcid) as the literal
    # string "true" in \author{}. Collapse it to a plain byline, and fold the
    # affiliation marker into the name where it already is.
    def _byline(m):
        name = re.sub(r"\^[0-9,*]+", "", m.group(1)).strip()
        aff = re.search(r"^affiliations:\n\s+- (.+)$", text, re.M)
        where = re.sub(r"\^[0-9,*]+", "", aff.group(1)).strip() if aff else ""
        return f'author: "{name}' + (f" ({where})" if where else "") + '"\n'

    text = re.sub(
        r"^author:\n\s+- name: (.+?)\n(?:\s{4,}.*\n)*",
        _byline, text, flags=re.M)

    # The manual references placeholder: pandoc's citeproc appends its own
    # bibliography, so keeping the empty quarto div would leave an empty
    # "References" heading behind.
    text = re.sub(r"^# References\s*$", "", text, flags=re.M)
    return text


def build(src: Path, to: str) -> Path:
    text = strip_quarto_only(src.read_text(encoding="utf-8"))
    tmp = src.with_suffix(".build.md")
    tmp.write_text(text, encoding="utf-8")
    try:
        out = src.with_suffix(f".{to}")
        cmd = [PANDOC, str(tmp), "-o", str(out),
               "--resource-path", str(ROOT),
               "--citeproc", "--bibliography", str(ROOT / "references.bib"),
               "--metadata", "reference-section-title=References",
               "--number-sections", "--toc=false"]
        if to == "pdf":
            cmd += ["--pdf-engine", TECTONIC,
                    "-V", "geometry:margin=2.5cm",
                    "-V", "fontsize=11pt",
                    "-V", "linestretch=1.35",
                    "--include-in-header", str(ROOT / ".build_preamble.tex")]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            print(r.stdout[-4000:])
            print(r.stderr[-6000:])
            raise SystemExit(f"pandoc failed for {src.name} -> {to}")
        print(f"  built {out.name} ({out.stat().st_size // 1024} KB)")
        return out
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    (ROOT / ".build_preamble.tex").write_text(PREAMBLE, encoding="utf-8")
    srcs = [Path(a) for a in sys.argv[1:]] or [ROOT / "manuscript.qmd",
                                               ROOT / "manuscript_eh.qmd"]
    for s in srcs:
        s = s if s.is_absolute() else ROOT / s
        print(f"Building {s.name}")
        build(s, "pdf")
        build(s, "docx")
    (ROOT / ".build_preamble.tex").unlink(missing_ok=True)
