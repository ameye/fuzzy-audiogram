#!/usr/bin/env python3
"""Append a verified references slide to each ACIC 2026 conference deck.

The decks are built as 16:9 slides on the "Blank" layout, with the header,
page counter, footer and cards drawn as explicit shapes (see
arabcic2026/build_arabcic_deck.py). This script therefore clones the header
shapes of an existing body slide byte-for-byte instead of guessing their
geometry, then lays a single white card with a numbered Vancouver reference
list underneath, in the same palette, fonts and card style.

Every entry below was checked against Crossref, PubMed, the publisher page or
the issuing body's own record on 24 November 2026; the record each one was
checked against is logged in references_verification.md. Nothing is cited
here that was not confirmed to exist, and no volume, issue, page or DOI is
inferred.

Usage:
    python3 add_references.py [--in-place]

Without --in-place the script writes <name>_with_references.pptx next to the
source; with it, the source deck is overwritten after a backup is taken in
./backup/.
"""

import argparse
import os
import shutil
import sys
from copy import deepcopy

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Emu, Inches, Pt
from pptx.oxml.ns import qn
from lxml import etree

# ---------------------------------------------------------------- palette
# Taken from the decks themselves (build_arabcic_deck.py and the slide XML).
NAVY = RGBColor(0x0B, 0x25, 0x45)
TEAL = RGBColor(0x1D, 0x78, 0x74)
LIGHT = RGBColor(0xF6, 0xF8, 0xFA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1B, 0x2A, 0x3A)
MUTED = RGBColor(0x5A, 0x6B, 0x7B)
BORDER = RGBColor(0xD8, 0xE0, 0xE8)
HDR = "Georgia"
BODY = "Calibri"

DELIVER = "/home/hermes/.hermes/deliver"

ACCESSED = "24 Nov 2026"

# ---------------------------------------------------------------- references
# Vancouver style. Verified details only; see references_verification.md.
FUZZY_REFS = [
    "Zadeh LA. Fuzzy sets. Inf Control. 1965;8(3):338\u201353. doi:10.1016/S0019-9958(65)90241-X",
    "Mamdani EH, Assilian S. An experiment in linguistic synthesis with a fuzzy logic "
    "controller. Int J Man-Mach Stud. 1975;7(1):1\u201313. doi:10.1016/S0020-7373(75)80002-2",
    "Ruspini EH. A new approach to clustering. Inf Control. 1969;15(1):22\u201332. "
    "doi:10.1016/S0019-9958(69)90591-9",
    "Olusanya BO, Davis AC, Hoffman HJ. Hearing loss grades and the International "
    "classification of functioning, disability and health. Bull World Health Organ. "
    "2019;97(10):725\u20138. doi:10.2471/BLT.19.230367",
    "World Health Organization. World report on hearing. Geneva: WHO; 2021. "
    "ISBN 978-92-4-002048-1. https://www.who.int/publications/i/item/9789240020481",
    "Clark JG. Uses and abuses of hearing loss classification. ASHA. 1981;23(7):493\u2013500. "
    "PMID 7052898.",
    "National Center for Health Statistics. National Health and Nutrition Examination "
    "Survey: continuous cycles 1999\u20132000, 2011\u20132012 and 2015\u20132016; audiometry "
    "(AUX, AUX_G, AUX_I) and demographics files. Hyattsville, MD: NCHS/CDC. "
    "https://wwwn.cdc.gov/nchs/nhanes/ (accessed " + ACCESSED + ").",
    "Ameye SA. A Mamdani fuzzy inference framework for graded pure-tone audiometric "
    "classification: development, validation, and open-source implementation [preprint]. "
    "SSRN; 2026. doi:10.2139/ssrn.7532157",
    "Chen T, Guestrin C. XGBoost: a scalable tree boosting system. In: Proceedings of the "
    "22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining. "
    "New York: ACM; 2016. p. 785\u201394. doi:10.1145/2939672.2939785",
    "Pedregosa F, Varoquaux G, Gramfort A, et al. Scikit-learn: machine learning in Python. "
    "J Mach Learn Res. 2011;12:2825\u201330.",
]

FUZZY_NOTE = (
    "WHO grades and the PTA-4 reference standard: WHO 2021 and Olusanya 2019 (refs 4\u20135). "
    "Every entry verified against Crossref, PubMed or the issuing body's record, " + ACCESSED + "."
)

SAUDI_REFS = [
    "Institute for Health Metrics and Evaluation. GBD Results: Global Burden of Disease "
    "Study 2023 [data tool]. Seattle, WA: IHME; 2025 (updated 12 October 2025). "
    "https://vizhub.healthdata.org/gbd-results/ (accessed " + ACCESSED + ").",
    "GBD 2023 Disease and Injury and Risk Factor Collaborators. Burden of 375 diseases and "
    "injuries, risk-attributable burden of 88 risk factors, and healthy life expectancy in "
    "204 countries and territories, including 660 subnational locations, 1990\u20132023: a "
    "systematic analysis for the Global Burden of Disease Study 2023. Lancet. "
    "2025;406(10513):1873\u2013922. doi:10.1016/S0140-6736(25)01637-X",
    "GBD 2019 Hearing Loss Collaborators. Hearing loss prevalence and years lived with "
    "disability, 1990\u20132019: findings from the Global Burden of Disease Study 2019. "
    "Lancet. 2021;397(10278):996\u20131009. doi:10.1016/S0140-6736(21)00516-X",
    "World Health Organization. World report on hearing. Geneva: WHO; 2021. "
    "ISBN 978-92-4-002048-1. https://www.who.int/publications/i/item/9789240020481",
    "United Nations, Department of Economic and Social Affairs, Population Division. "
    "World Population Prospects 2024: summary of results. New York: UN; 2024. "
    "https://population.un.org/wpp/ (accessed " + ACCESSED + ").",
    "NCD Risk Factor Collaboration (NCD-RisC). Worldwide trends in underweight and obesity "
    "from 1990 to 2022: a pooled analysis of 3663 population-representative studies with "
    "222 million children, adolescents, and adults. Lancet. 2024;403(10431):1027\u201350. "
    "doi:10.1016/S0140-6736(23)02750-2",
    "NCD Risk Factor Collaboration (NCD-RisC). Worldwide trends in diabetes prevalence and "
    "treatment from 1990 to 2022: a pooled analysis of 1108 population-representative "
    "studies with 141 million participants. Lancet. 2024;404(10467):2077\u201393. "
    "doi:10.1016/S0140-6736(24)02317-1",
    "World Health Organization. Global Health Observatory: concentrations of fine "
    "particulate matter (PM2.5), SDG indicator 11.6.2 [database]. Geneva: WHO. "
    "https://www.who.int/data/gho/data/indicators/indicator-details/GHO/"
    "concentrations-of-fine-particulate-matter-(pm2-5) (accessed " + ACCESSED + ").",
    "Chen T, Guestrin C. XGBoost: a scalable tree boosting system. In: Proceedings of the "
    "22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining. "
    "New York: ACM; 2016. p. 785\u201394. doi:10.1145/2939672.2939785",
    "Murray CJL, Ezzati M, Lopez AD, Rodgers A, Vander Hoorn S. Comparative quantification "
    "of health risks: conceptual framework and methodological issues. Popul Health Metr. "
    "2003;1:1. doi:10.1186/1478-7954-1-1",
]

SAUDI_NOTE = (
    "GBD 2023 values are IHME modelled estimates with uncertainty intervals, not measured "
    "counts; the 2024\u20132040 series is the author's projection, not a GBD release. "
    "Every entry verified against Crossref, PubMed or the issuing body's record, " + ACCESSED + "."
)

DECKS = [
    {
        "path": os.path.join(DELIVER, "ACIC2026_Fuzzy_SNHL_Classification.pptx"),
        "template_slide": 12,          # "Limitations and next steps": a full-card body slide
        "refs": FUZZY_REFS,
        "note": FUZZY_NOTE,
        "size": 10.0,
        # measured from the LibreOffice render of the fitted slide (see QA log)
        "list_h": 3.90,
        "note_y": 5.60,
        "card_h": 4.82,
        "gap": 11,
    },
    {
        "path": os.path.join(DELIVER, "ACIC2026_HearingLoss_GBD2023_Saudi.pptx"),
        "template_slide": 11,          # "Limitations": a full-card body slide
        "refs": SAUDI_REFS,
        "note": SAUDI_NOTE,
        "size": 10.0,
        "list_h": 4.36,
        "note_y": 6.05,
        "card_h": 5.42,
        "gap": 6,
    },
]


# ---------------------------------------------------------------- helpers
def find_shapes(slide):
    return {sh.name: sh for sh in slide.shapes}


def clone_header(new_slide, template_slide, title, counter):
    """Copy the background, title, counter and footer shapes verbatim, then
    retitle and renumber them. Copying the XML keeps fonts, insets and the
    auto-fit behaviour identical to every other slide in the deck."""
    src = find_shapes(template_slide)
    for name in ("Rectangle 1", "TextBox 2", "TextBox 3", "TextBox 4"):
        el = deepcopy(src[name]._element)
        new_slide.shapes._spTree.append(el)
    dst = find_shapes(new_slide)
    for name, text in (("TextBox 2", title), ("TextBox 3", counter)):
        tf = dst[name].text_frame
        para = tf.paragraphs[0]
        para.runs[0].text = text
        # drop any extra runs/paragraphs left over from the template
        for extra in list(para.runs)[1:]:
            extra._r.getparent().remove(extra._r)


def add_card(slide, x, y, w, h, radius=0.045):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                  Inches(w), Inches(h))
    try:
        card.adjustments[0] = radius
    except Exception:
        pass
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = BORDER
    card.line.width = Pt(0.75)
    card.shadow.inherit = False
    card.text_frame.text = ""
    # teal accent bar down the left edge, as on every card in the deck
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                 Inches(0.09), Inches(h))
    bar.fill.solid()
    bar.fill.fore_color.rgb = TEAL
    bar.line.fill.background()
    bar.shadow.inherit = False
    return card


def add_ref_list(slide, x, y, w, h, refs, size, gap=7):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE   # never shrink: layout must fit, QA measures it
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Pt(4)
    tf.margin_top = Pt(2)
    tf.margin_bottom = Pt(2)

    hanging = Inches(0.34)
    for i, ref in enumerate(refs):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = PP_ALIGN.LEFT
        para.line_spacing = 1.12
        para.space_after = Pt(gap)
        pPr = para._p.get_or_add_pPr()
        pPr.set("marL", str(int(hanging)))
        pPr.set("indent", str(-int(hanging)))
        # tab stop at the hanging indent so the citation aligns under itself
        tabLst = etree.SubElement(pPr, qn("a:tabLst"))
        tab = etree.SubElement(tabLst, qn("a:tab"))
        tab.set("pos", str(int(hanging)))
        tab.set("algn", "l")

        num = para.add_run()
        num.text = f"{i + 1}.\t"
        num.font.size = Pt(size)
        num.font.bold = False
        num.font.name = BODY
        num.font.color.rgb = TEAL

        # split the DOI/URL tail out so it reads as a link in the deck's teal
        cut = min([p for p in (ref.find("doi:"), ref.find("http")) if p >= 0] or [len(ref)])
        head, tail = ref[:cut], ref[cut:]
        r1 = para.add_run()
        r1.text = head
        r1.font.size = Pt(size)
        r1.font.name = BODY
        r1.font.color.rgb = INK
        if tail:
            r2 = para.add_run()
            r2.text = tail
            r2.font.size = Pt(size)
            r2.font.name = BODY
            r2.font.color.rgb = TEAL
    return box


def add_note(slide, x, y, w, h, text, size=8.5):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = Pt(4)
    tf.margin_top = tf.margin_bottom = Pt(2)
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.LEFT
    para.line_spacing = 1.05
    r = para.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.italic = True
    r.font.name = BODY
    r.font.color.rgb = MUTED
    return box


def build(deck, out_path):
    prs = Presentation(deck["path"])
    n_before = len(prs.slides)

    # idempotency: drop a previously added references slide so re-runs do not stack
    if n_before and any(sh.has_text_frame and sh.text_frame.text.strip() == "References"
                        for sh in prs.slides[-1].shapes):
        # Drop the relationship as well as the id, or the orphaned slide part
        # is written twice and the archive ends up with duplicate part names.
        xml_slides = prs.slides._sldIdLst
        sldId = xml_slides[-1]
        prs.part.drop_rel(sldId.rId)
        xml_slides.remove(sldId)
        n_before -= 1

    template = prs.slides[deck["template_slide"]]
    layout_idx = 6  # "Blank", the layout every slide in both decks uses
    slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
    for shp in list(slide.shapes):          # the layout contributes no shapes, but be safe
        shp._element.getparent().remove(shp._element)

    n_after = n_before + 1
    clone_header(slide, template, "References", f"{n_after} / {n_after}")

    add_card(slide, 0.55, 1.30, 12.25, deck["card_h"])
    add_ref_list(slide, 0.80, 1.46, 11.85, deck["list_h"], deck["refs"],
                 deck["size"], deck.get("gap", 7))
    add_note(slide, 0.80, deck["note_y"], 11.85, 0.45, deck["note"])

    prs.save(out_path)
    return n_before, n_after


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-place", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    backup = os.path.join(here, "backup")
    os.makedirs(backup, exist_ok=True)

    for deck in DECKS:
        src = deck["path"]
        name = os.path.basename(src)
        dst = src if args.in_place else os.path.join(
            os.path.dirname(src), name.replace(".pptx", "_with_references.pptx"))
        if args.in_place:
            shutil.copy2(src, os.path.join(backup, name))
        before, after = build(deck, dst)
        print(f"{name}: slides {before} -> {after}; wrote {dst}")


if __name__ == "__main__":
    sys.exit(main())
