# ACIC 2026 Q&A preparation sheet

Two A4 pages, one per deck, for the 4th Arab Cochlear Implant Conference (Jeddah, 26 to 28 November 2026).

- `qa_content.py` holds every question, answer and "do not say" note, in rehearsal order.
- `build_qa.py` renders `ACIC2026_QandA_Prep.html`; the page carries a fitting routine that
  picks the largest body size per page, and it prints with zero margins.
- `ACIC2026_QandA_Prep.pdf` is the deliverable, printed from that HTML at A4, one page per deck.

Figures follow the 23 November 2026 decks: 42 rules, weighted kappa 0.946, MAE 4.32 dB,
4.96 million by 2040, 34.0 per cent asymmetry, counterfactual 0.00 per cent. Do not edit a
number here without re-reading the deck: the superseded values (48 rules, kappa 0.93,
MAE 6.1 dB, 4.89 million) are wrong and were removed deliberately.

Rebuild: `python build_qa.py`, then print the HTML with Page.printToPDF
(`preferCSSPageSize`, all margins zero). Check the result is exactly two pages.
