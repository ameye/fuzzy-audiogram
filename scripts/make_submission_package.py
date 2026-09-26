"""Assemble the CMPB submission package.

Builds every element a CMPB submission needs into one directory and zips it. The
manuscript DOCX carries no embedded figures, which is what Elsevier wants; the
figures ship as separate 600 dpi files with captions in the manuscript body.

Run:  python3 scripts/make_submission_package.py
"""
import html
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MS = ROOT / "manuscript"
SUB = ROOT / "submission"
SUPP = MS / "supplementary"
FIGDIR = MS / "figures"

TITLE = ("A Mamdani fuzzy inference framework for graded pure-tone audiometric "
         "classification: development, validation and open-source implementation")
AUTHOR = "Sanyaolu Ameye"
ORCID = "0000-0002-5217-7997"
EMAIL = "sanyaameye@hotmail.com"
REPO = "https://github.com/ameye/fuzzy-audiogram"

# no real institution is named anywhere in this package
AFFIL = "[TO CONFIRM]"

CSS = """
@page { size: A4; margin: 22mm 20mm; @bottom-center { content: counter(page); font-size: 9pt; color:#666 } }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 11pt; line-height: 1.5; color: #111 }
h1 { font-size: 16pt; margin: 0 0 4pt 0; line-height: 1.25 }
h2 { font-size: 12.5pt; margin: 16pt 0 6pt 0; border-bottom: .6pt solid #999; padding-bottom: 2pt }
p { margin: 0 0 8pt 0; text-align: justify }
.meta { font-size: 10.5pt; color: #222; margin-bottom: 2pt }
.hl { margin: 0 0 7pt 0 }
.small { font-size: 9.5pt; color: #333 }
"""


def pdf(path, body):
    from weasyprint import HTML
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
           f"<body>{body}</body></html>")
    HTML(string=doc).write_pdf(str(path))
    return path


def cover_letter(path):
    body = f"""
<h1>Cover letter</h1>
<p class="meta"><b>To:</b> The Editors-in-Chief, <i>Computer Methods and Programs in Biomedicine</i></p>
<p class="meta"><b>Manuscript title:</b> {html.escape(TITLE)}</p>
<p class="meta"><b>Article type:</b> Full-length research article</p>
<p class="meta"><b>Corresponding author:</b> {AUTHOR}, {ORCID}, {EMAIL}</p>

<p>Dear Editors,</p>

<p>I am submitting for consideration a research article describing an open-source Mamdani
fuzzy inference system for grading pure-tone audiograms. The work replaces the fixed
severity boundaries that audiometry currently relies on with a graded index built on a
formal Ruspini partition, and validates it on {html.escape("19,623")} adult ears drawn from
three NHANES cycles with a participant-level train and test split.</p>

<p>The contribution I would ask you to weigh is not a new classifier but a demonstrable and
reproducible construction, which is why I have submitted to <i>CMPB</i> rather than to a
clinical audiology journal. Three features make the method auditable rather than merely
reported. The six trapezoidal membership functions are built by a published algorithm in
which adjacent cores never move and the shoulders are proven to sum to one across the whole
universe, so the partition property is a property of the construction and not a numerical
coincidence. Every threshold, table value and figure in the manuscript is produced by
committed code, and the repository holds the verification scripts alongside the pipeline.
And the analysis reports where the method does not win: the reference grade is a
deterministic thresholding of the pure-tone average, which a proportional-odds model
recovers exactly, and a seven-frequency gradient-boosting model outperforms the index on
every metric. The manuscript states both and locates the index's value accordingly, in
interpretability, in a graded output no crisp classifier provides, and in explicit behaviour
at the boundaries where graders disagree.</p>

<p>The evaluation is deliberately adversarial towards the method. Agreement is stratified by
distance from the severity boundary, where the index should help and where a summary statistic
hides the effect. The transition width is swept rather than reported at a single setting. A
second classification schema is run end to end to establish that the results depend on the
method rather than on the choice of reference standard. And the borderline and clear-case
agreement rates are reported with confidence intervals, so the reader can see the range in
which the index is and is not informative.</p>

<p>The system, the analysis pipeline and the verification scripts are available as an
open-source implementation at {html.escape(REPO)}, and a web calculator with a documented
REST API for EHR integration is included for clinical evaluation.</p>

<p>This manuscript is original, has not been published previously, and is not under
consideration elsewhere. The author declares no competing interests and received no specific
funding for this work. A declaration of generative AI use is included in the manuscript.</p>

<p>Thank you for considering this submission.</p>

<p style="margin-top:14pt">Yours sincerely,</p>
<p style="margin:0"><b>{AUTHOR}</b><br/>
ORCID: {ORCID}<br/>
{AFFIL}<br/>
{EMAIL}</p>
"""
    pdf(path, body)


def title_page(path):
    body = f"""
<h1>{html.escape(TITLE)}</h1>
<p class="meta" style="margin-top:10pt"><b>{AUTHOR}</b></p>
<p class="meta">ORCID: {ORCID}</p>
<p class="meta">Affiliation: {html.escape(AFFIL)}</p>
<p class="meta"><b>Corresponding author:</b> {AUTHOR}, {EMAIL}</p>

<h2>Article type</h2>
<p>Full-length research article</p>

<h2>Keywords</h2>
<p>audiometry, hearing loss classification, fuzzy inference, Ruspini partition,
reproducibility, clinical decision support</p>

<h2>Highlights</h2>
<p class="hl">Mamdani fuzzy inference provides graded classification of pure-tone audiograms.</p>
<p class="hl">Ruspini partition ensures memberships sum to unity across 0 to 120 dB HL.</p>
<p class="hl">Validated on 19,623 NHANES adult ears with participant-level splitting.</p>
<p class="hl">Reference label shown to be a deterministic thresholding of its input.</p>
<p class="hl">Open-source implementation with a REST API for EHR integration.</p>

<h2>Author contributions (CRediT)</h2>
<p><b>{AUTHOR}:</b> Conceptualization, Methodology, Software, Validation, Formal analysis,
Investigation, Data curation, Writing - original draft, Writing - review and editing,
Visualization.</p>

<h2>Funding</h2>
<p>This research received no specific grant from any funding agency in the public, commercial
or not-for-profit sectors.</p>

<h2>Declaration of competing interest</h2>
<p>The author reports no competing interests to declare.</p>

<h2>Data availability</h2>
<p>The NHANES data analysed here are publicly available from the U.S. Centers for Disease
Control and Prevention. The fuzzy inference system, the Ruspini membership function
construction, the analysis pipeline and the verification scripts are available at
{html.escape(REPO)}.</p>

<h2>Declaration of generative AI use</h2>
<p>During the preparation of this work the author used a large language model assistant to
support drafting, language editing and code documentation. No AI or machine-learning tool
generated the underlying data, selected the cohort, or computed any reported statistic; the
fuzzy inference system is a transparent, rule-based model with no learned parameters. The
author reviewed and verified all content and takes full responsibility for the work.</p>

<h2>Counts</h2>
<p class="small">Main text 3,497 words (CMPB limit 3,500 excluding abstract, references and
figure captions). Abstract 277 words (limit 350). 18 references. 4 figures, 4 tables,
1 supplementary file.</p>
"""
    pdf(path, body)


def highlights(path):
    body = f"""<h1>Highlights</h1>
<p class="meta"><b>{html.escape(TITLE)}</b></p>
<p class="meta">{AUTHOR}</p>
<p class="small">Each highlight is under 85 characters including spaces, as required.</p>
<h2>Highlights</h2>
<p class="hl">Mamdani fuzzy inference provides graded classification of pure-tone audiograms.</p>
<p class="hl">Ruspini partition ensures memberships sum to unity across 0 to 120 dB HL.</p>
<p class="hl">Validated on 19,623 NHANES adult ears with participant-level splitting.</p>
<p class="hl">Reference label shown to be a deterministic thresholding of its input.</p>
<p class="hl">Open-source implementation with a REST API for EHR integration.</p>
"""
    pdf(path, body)


def main():
    if SUB.exists():
        shutil.rmtree(SUB)
    SUB.mkdir(parents=True)
    (SUB / "figures").mkdir()

    made = []
    cover_letter(SUB / "01_Cover_Letter.pdf"); made.append("01_Cover_Letter.pdf")
    title_page(SUB / "02_Title_Page.pdf"); made.append("02_Title_Page.pdf")

    shutil.copy2(MS / "Manuscript_CMPB_v4.docx", SUB / "03_Manuscript.docx")
    made.append("03_Manuscript.docx")
    shutil.copy2(MS / "Manuscript_CMPB_v4_reading.pdf", SUB / "03_Manuscript.pdf")
    made.append("03_Manuscript.pdf")

    highlights(SUB / "04_Highlights.pdf"); made.append("04_Highlights.pdf")

    for f in sorted(FIGDIR.glob("*.png")):
        shutil.copy2(f, SUB / "figures" / f.name)
    made.append(f"figures/ ({len(list((SUB/'figures').glob('*.png')))} files)")

    shutil.copy2(SUPP / "Supplementary_Material.pdf", SUB / "05_Supplementary_Material.pdf")
    made.append("05_Supplementary_Material.pdf")
    shutil.copy2(MS / "Rule_Base.pdf", SUB / "06_Rule_Base.pdf")
    made.append("06_Rule_Base.pdf")

    # checklist
    chk = f"""CMPB SUBMISSION PACKAGE
{TITLE}
{AUTHOR} | ORCID {ORCID} | {EMAIL}

FILES
  01_Cover_Letter.pdf            cover letter to the Editors-in-Chief
  02_Title_Page.pdf              title page, keywords, highlights, CRediT, declarations
  03_Manuscript.docx             manuscript for submission (no embedded figures)
  03_Manuscript.pdf              the same text as a readable PDF, figures inlined
  04_Highlights.pdf              highlights, for the separate highlights field
  05_Supplementary_Material.pdf  Table S1 and Figure S1
  06_Rule_Base.pdf               the 42 rules, for reviewers
  figures/                       four 600 dpi PNGs, separate as Elsevier requires

BEFORE YOU UPLOAD - TWO OUTSTANDING ITEMS
  1. AFFILIATION IS UNFILLED. The title page and cover letter read
     "Affiliation: [TO CONFIRM]". Give me the affiliation and I will rebuild.
  2. The shipped classifier has a rule-base hole. Two slope/notch combinations have no
     configuration rule (steeply_sloping + shallow_notch, precipitous + deep_notch).
     When none fires, the FIS returns no audiogram_shape and core.py:379 raises
     KeyError. A textbook noise notch (slope 35 dB, notch 17.5 dB) hits it, and the
     deployed web calculator returns an error for that ear. Fixing it adds rules,
     which changes the count of 42 and ripples into the Abstract and Section 3.6.

EDITORIAL CHECKS - ALL SATISFIED
  Main text          3,497 words   (CMPB limit 3,500 excluding abstract)
  Abstract             277 words   (limit 350)
  Highlights        5, all <85 characters
  References        18, all verified against CrossRef or PubMed
  Figures           4, all 600 dpi and above the 3,543 px minimum
  Tables            4, numbered in citation order
  Supplementary     Table S1 and Figure S1, both cited in the text
  Reproducibility   every number and figure produced by committed code
  Figure naming     no real institution named in any figure
"""
    (SUB / "README.txt").write_text(chk)
    made.append("README.txt")

    zp = ROOT / "CMPB_Submission_Package.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SUB.rglob("*")):
            if f.is_file():
                z.write(f, Path("CMPB_submission") / f.relative_to(SUB))
    print("  package contents:")
    for m in made:
        print(f"    {m}")
    print(f"\n  -> {zp}  ({zp.stat().st_size/1048576:.1f} MB)")
    with zipfile.ZipFile(zp) as z:
        print("  zip integrity:", z.testzip() or "OK", "| entries:", len(z.namelist()))


if __name__ == "__main__":
    main()
