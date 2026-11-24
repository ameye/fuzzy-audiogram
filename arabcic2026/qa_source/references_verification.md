# References verification log — ACIC 2026 decks

Two conference decks for the 4th Arab Cochlear Implant Conference (Jeddah, 26–28 November 2026),
`ACIC2026_Fuzzy_SNHL_Classification.pptx` and `ACIC2026_HearingLoss_GBD2023_Saudi.pptx`, carried no
references at all. Each now ends with one numbered Vancouver reference slide (slide 16 and slide 15).

Checked 24 November 2026. Every entry below was confirmed against a record that was actually retrieved;
nothing on either slide was inferred, and a source that could not be confirmed was left off (see
"Considered and not used").

## Method

1. **Identification.** Crossref bibliographic queries (`api.crossref.org/works?query.bibliographic=…`)
   to find candidate DOIs, then a direct record lookup (`api.crossref.org/works/{doi}`) for the DOI
   that the slide actually prints.
2. **Second, independent check.** PubMed E-utilities by DOI (`esearch.fcgi?term={doi}[DOI]` +
   `esummary.fcgi`) for author string, journal, year, volume, issue and pages. Where the two
   disagreed, the record that resolved the DOI itself (Crossref) governed, and the discrepancy is
   noted below.
3. **Organisational resources** (WHO, CDC/NCHS, IHME, UN DESA) were fetched directly and the page
   title, ISBN or release date read off the live page, not from a search snippet.
4. **Fields printed** are the returned fields. Journal titles use the NLM abbreviation; page ranges
   use Vancouver elision (`1873–1922` → `1873–922`), which removes repeated leading digits without
   changing any number. No volume, issue, page or DOI appears on a slide that a record did not return.
5. **Access date** for the four database/tool entries is `24 Nov 2026`, the date of this check.

## Fuzzy deck — 10 references (slide 16)

| # | Printed entry | Record checked | Returned by the record | Result |
|---|---|---|---|---|
| 1 | Zadeh LA. Fuzzy sets. Inf Control. 1965;8(3):338–53. | Crossref `10.1016/S0019-9958(65)90241-X` | "Fuzzy sets"; Information and Control; 1965-06; vol 8, issue 3, pp 338-353; Zadeh L.A. | Verified |
| 2 | Mamdani EH, Assilian S. An experiment in linguistic synthesis with a fuzzy logic controller. Int J Man-Mach Stud. 1975;7(1):1–13. | Crossref `10.1016/S0020-7373(75)80002-2` | Same title; International Journal of Man-Machine Studies; 1975-01; vol 7, issue 1, pp 1-13; Mamdani E.H., Assilian S. | Verified |
| 3 | Ruspini EH. A new approach to clustering. Inf Control. 1969;15(1):22–32. | Crossref `10.1016/S0019-9958(69)90591-9` | Same title; Information and Control; 1969-07; vol 15, issue 1, pp 22-32; Ruspini Enrique H. | Verified |
| 4 | Olusanya BO, Davis AC, Hoffman HJ. Hearing loss grades and the International classification of functioning, disability and health. Bull World Health Organ. 2019;97(10):725–8. | Crossref `10.2471/BLT.19.230367` + PubMed `31656340` | Bull World Health Organ 2019 Oct 1;97(10):725-728; doi 10.2471/BLT.19.230367; Epub 2019 Sep 3; PMC6796665. Full text (PMC) Table 1 footnote: grades computed on the "Average of 500, 1000, 2000 and 4000 Hz" | Verified |
| 5 | World Health Organization. World report on hearing. Geneva: WHO; 2021. ISBN 978-92-4-002048-1. https://www.who.int/publications/i/item/9789240020481 | WHO publication page (HTTP 200) | Title "World report on hearing"; published 3 March 2021; 252 pages; "ISBN: 978-92-4-002048-1"; publisher World Health Organization | Verified |
| 6 | Clark JG. Uses and abuses of hearing loss classification. ASHA. 1981;23(7):493–500. PMID 7052898. | PubMed `7052898` | ASHA 1981 Jul;23(7):493-500; Clark JG; no DOI registered | Verified |
| 7 | National Center for Health Statistics. National Health and Nutrition Examination Survey, continuous cycles 1999–2000, 2011–2012, 2015–2016; audiometry (AUX, AUX_G, AUX_I) and demographics files. Hyattsville, MD: NCHS/CDC. https://wwwn.cdc.gov/nchs/nhanes/ (accessed 24 Nov 2026). | CDC/NCHS: NHANES documentation index (HTTP 200); component pages `…/Nchs/Data/Nhanes/Public/2015/DataFiles/AUX_I.htm` and `…/2011/DataFiles/AUX_G.htm` (HTTP 200) | Survey index titled "NHANES Questionnaires, Datasets, and Related Documentation"; audiometry component pages exist for AUX_I (2015–16) and AUX_G (2011–12). The three cycles used by the analysis are the ones held in the repository (`AUX_9900`, `AUX_G_1112`, `AUX_I_1516`) | Verified (resource) |
| 8 | Ameye SA. A Mamdani fuzzy inference framework for graded pure-tone audiometric classification: development, validation, and open-source implementation [preprint]. SSRN; 2026. doi:10.2139/ssrn.7532157 | Crossref `10.2139/ssrn.7532157` (type `posted-content`) | Same title; author "Ameye Sanyaolu", ORCID 0000-0002-5217-7997, authenticated; publisher Elsevier BV; created 2026-09-30; DOI 10.2139/ssrn.7532157 | Verified |
| 9 | Chen T, Guestrin C. XGBoost: a scalable tree boosting system. In: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining. New York: ACM; 2016. p. 785–94. | Crossref `10.1145/2939672.2939785` | "XGBoost"; Proceedings of the 22nd ACM SIGKDD International Conference on KDD; 2016-08-13; pp 785-794; Chen Tianqi, Guestrin Carlos; type proceedings-article | Verified |
| 10 | Pedregosa F, Varoquaux G, Gramfort A, et al. Scikit-learn: machine learning in Python. J Mach Learn Res. 2011;12:2825–30. | JMLR article page `jmlr.org/papers/v12/pedregosa11a.html` (HTTP 200) | "Scikit-learn: Machine Learning in Python"; authors Fabian Pedregosa, Gaël Varoquaux, Alexandre Gramfort, … Édouard Duchesnay; **12(85):2825–2830, 2011** | Verified |

## Saudi deck — 10 references (slide 15)

| # | Printed entry | Record checked | Returned by the record | Result |
|---|---|---|---|---|
| 1 | Institute for Health Metrics and Evaluation. GBD Results: Global Burden of Disease Study 2023 [data tool]. Seattle, WA: IHME; 2025 (updated 12 October 2025). https://vizhub.healthdata.org/gbd-results/ (accessed 24 Nov 2026). | IHME GBD Results tool page (HTTP 200); IHME GHDx "Global Burden of Disease Study 2023 (GBD 2023) Data Resources" (HTTP 200) | Tool page titled "GBD Results", "Updated October 12, 2025"; GHDx confirms GBD 2023 as "the most recent update" and links the GBD Results tool | Verified (resource) |
| 2 | GBD 2023 Disease and Injury and Risk Factor Collaborators. Burden of 375 diseases and injuries, risk-attributable burden of 88 risk factors, … 1990–2023 … Lancet. 2025;406(10513):1873–922. | Crossref `10.1016/S0140-6736(25)01637-X` + PubMed `41092926` | Lancet 2025 Oct 18;406(10513):1873-1922; collective author "GBD 2023 Disease and Injury and Risk Factor Collaborators" | Verified |
| 3 | GBD 2019 Hearing Loss Collaborators. Hearing loss prevalence and years lived with disability, 1990–2019: findings from the Global Burden of Disease Study 2019. Lancet. 2021;397(10278):996–1009. | Crossref `10.1016/S0140-6736(21)00516-X` + PubMed `33714390` | Lancet 2021 Mar 13;397(10278):996-1009; collective author "GBD 2019 Hearing Loss Collaborators" | Verified |
| 4 | World Health Organization. World report on hearing. Geneva: WHO; 2021. ISBN 978-92-4-002048-1. | WHO publication page (HTTP 200) | As above: 3 March 2021, 252 pages, ISBN 978-92-4-002048-1 | Verified |
| 5 | United Nations, Department of Economic and Social Affairs, Population Division. World Population Prospects 2024: summary of results. New York: UN; 2024. https://population.un.org/wpp/ (accessed 24 Nov 2026). | UN DESA page `un.org/development/desa/pd/world-population-prospects-2024` (HTTP 200); `population.un.org/wpp/` (HTTP 200) | "World Population Prospects 2024"; methodology report UN DESA/POP/2024/DC/NO.10 (July 2024); summary of results UN DESA/POP/2024/TR/NO.9 | Verified (resource) |
| 6 | NCD Risk Factor Collaboration (NCD-RisC). Worldwide trends in underweight and obesity from 1990 to 2022: … Lancet. 2024;403(10431):1027–50. | Crossref `10.1016/S0140-6736(23)02750-2` + PubMed `38432237` | Lancet 2024 Mar 16;403(10431):1027-1050; collective author "NCD Risk Factor Collaboration (NCD-RisC)" | Verified |
| 7 | NCD Risk Factor Collaboration (NCD-RisC). Worldwide trends in diabetes prevalence and treatment from 1990 to 2022: … Lancet. 2024;404(10467):2077–93. | Crossref `10.1016/S0140-6736(24)02317-1` + PubMed `39549716` | Lancet 2024 Nov 23;404(10467):2077-2093; collective author "NCD Risk Factor Collaboration (NCD-RisC)" | Verified |
| 8 | World Health Organization. Global Health Observatory: concentrations of fine particulate matter (PM2.5), SDG indicator 11.6.2 [database]. Geneva: WHO. https://www.who.int/data/gho/…(pm2-5) (accessed 24 Nov 2026). | WHO GHO indicator page (HTTP 200) | Page title "Air pollution: concentrations of fine particulate matter (PM2.5), SDG 11.6.2" | Verified (resource) |
| 9 | Chen T, Guestrin C. XGBoost: a scalable tree boosting system. KDD '16. p. 785–94. | Crossref `10.1145/2939672.2939785` | As entry 9 of the fuzzy deck | Verified |
| 10 | Murray CJL, Ezzati M, Lopez AD, Rodgers A, Vander Hoorn S. Comparative quantification of health risks: conceptual framework and methodological issues. Popul Health Metr. 2003;1:1. | Crossref `10.1186/1478-7954-1-1` + PubMed `12780936` | Popul Health Metr 2003 Apr 14;1(1):1; PMC156894; authors Murray, Ezzati, Lopez, Rodgers, Vander Hoorn (Crossref lists four; PubMed adds Vander Hoorn) | Verified |

**Caveat printed on the Saudi slide** (below the list): "GBD 2023 values are IHME modelled estimates
with uncertainty intervals, not measured counts; the 2024–2040 series is the author's projection, not
a GBD release." This mirrors the limitations already stated on slides 2 and 12 of that deck.

## Considered and not used

| Candidate | Why it is not on the slide |
|---|---|
| WHO/PDH/97.3, *Future programme developments for the prevention of deafness and hearing impairment* (1997 grades document) | No live, retrievable record of the document itself could be found; the grades are instead anchored to the WHO 2021 report and to Olusanya 2019, whose Table 1 defines them on the 500/1000/2000/4000 Hz average |
| scikit-fuzzy v0.5.0 (implementation library named on slide 4) | Software package with no citable paper or DOI; the implementation is covered by the SSRN preprint |
| Shen Y, Zhou T, Zou W. Global burden of hearing loss 1990–2021 (Ann Med 2025;57:2527367, PMID 40605509) | Real and retrievable, but an independent GBD 2021 *re-analysis*, not a collaborator analysis; the GBD hearing-loss collaborator paper is Haile 2021 (entry 3) |
| Hyndman RJ, Athanasopoulos G. *Forecasting: Principles and Practice* (3rd ed., OTexts) | Exists (otexts.com/fpp3, HTTP 200), but the forecast here is XGBoost with an expanding-window split, not an FPP3 method; the counterfactual framework is carried by Murray 2003 |
| WHO GHO indicators for obesity/diabetes | Superseded for these two exposures by the primary NCD-RisC pooled analyses (entries 6 and 7) |
| Clark (1981) in the Saudi deck | The Saudi deck does not make the classification-history claim, so the reference would be filler |

## Discrepancy found in existing deck text (left unaltered)

Slide 4 of the Saudi deck states: "The series is the released GBD 2023 results (IHME 2024)".
The GBD 2023 results were released in **October 2025** — the IHME GBD Results tool page is stamped
"Updated October 12, 2025", the GBD 2023 findings booklet is dated October 2025, and the GBD 2023
collaborator paper is Lancet 2025;406(10513). The reference slide therefore cites 2025. The existing
slide text was **not** edited, because the brief was to append one slide and alter no existing slide;
the author may wish to change "IHME 2024" to "IHME 2025".

## Layout and render QA

Built by `add_references.py`, which clones the background, title, page counter and footer shapes from
an existing body slide (XML copy), then lays a white card with a teal left bar, numbered references at
10 pt Calibri with a 0.34 in hanging indent, DOIs and URLs in the deck's teal, and a muted italic note.

| Check | Fuzzy deck | Saudi deck |
|---|---|---|
| Slide count | 15 → 16 | 14 → 15 |
| Final slide title | "References" | "References" |
| Pre-existing slides byte-identical to the pre-notes deck | yes (15 of 15) | yes (14 of 14) |
| Speaker notes unchanged | yes (9,982 chars; slide 1 has "Also a Data Scientist") | yes (8,365 chars; slide 1 has "surgeon working in Tabuk") |
| Package integrity | 108 parts, no duplicate names, `testzip` clean | 103 parts, no duplicate names, `testzip` clean |

Rendered with `/opt/data/lo/soffice.sh --convert-to pdf` (LibreOffice 26.8) and measured from the PDF
text layer (page 960 × 540 pt):

| Measure | Fuzzy | Saudi |
|---|---|---|
| References text block | y 109–381 pt | y 109–417 pt |
| Note | y 406–417 pt | y 439–460 pt |
| Card | y 94–441 pt | y 94–484 pt |
| Footer | y 512–523 pt | y 512–523 pt |
| Horizontal extent | x 43.6–917.6 pt of 960 | x 43.6–917.6 pt of 960 |

No text overflows the card, no reference overlaps the note or the footer, and every numbered entry
appears complete in the extracted text (10 entries per deck). Renders: `qa/fuzzy_ref.png`,
`qa/saudi_ref.png`; PDFs: `qa/*.pdf`.

## Reproduce

```
python3 add_references.py --in-place     # rebuild both decks, backing up to ./backup/
python3 add_references.py                # or write *_with_references.pptx next to the source
```
