# ArabCIC 2026 — Speaker notes, trimmed for a 10-minute slot

Two conference decks, 130 words a minute, 1,300 words per slot. Notes only: no slide text,
layout or shape was changed, and the .pptx files were not written by this pass.

## A Fuzzy Logic Framework for SNHL Classification

15 slides. Slot 10 minutes at 130 words a minute, so the ceiling is 1,300 words.

Trimmed from 1,713 words (13.2 min) to 1,295 (10.0 min): 418 words cut, and every concession kept.

| Slide | Title | Words | Time | Running |
|---|---|---|---|---|
| 1 | A Fuzzy Logic Framework for SNHL Classification | 63 | 29 s | 29 s |
| 2 | Crisp thresholds on continuous biology | 86 | 40 s | 1 min 09 s |
| 3 | Fuzzy sets for graded severity | 68 | 31 s | 1 min 40 s |
| 4 | Methods and the Mamdani inference system | 86 | 40 s | 2 min 20 s |
| 5 | Trapezoidal membership functions | 90 | 42 s | 3 min 01 s |
| 6 | 42 audiology-derived rules in four groups | 95 | 44 s | 3 min 45 s |
| 7 | FAI against WHO PTA-4 and ML comparators | 104 | 48 s | 4 min 33 s |
| 8 | The 25/26 dB boundary is graded, not binary | 99 | 46 s | 5 min 19 s |
| 9 | Clinical case studies: four archetypes | 104 | 48 s | 6 min 07 s |
| 10 | Configuration typing and asymmetry | 90 | 42 s | 6 min 48 s |
| 11 | Longitudinal tracking of sub-threshold change | 92 | 42 s | 7 min 31 s |
| 12 | Clinical implications | 94 | 43 s | 8 min 14 s |
| 13 | Limitations and next steps | 100 | 46 s | 9 min 00 s |
| 14 | Take-home | 90 | 42 s | 9 min 42 s |
| 15 | Thank you | 34 | 16 s | 9 min 58 s |
| **Total** | | **1,295** | **9 min 58 s** | **10.0 min** |

**Deck total: 1,295 words, 10.0 minutes at 130 words a minute.**

### Slide 1 — A Fuzzy Logic Framework for SNHL Classification
Good morning. I am Sanyaolu Ameye, an ENT surgeon in Tabuk. Also a Data Scientist. In the next ten minutes I want to show you why a pure-tone average is a blunt way to describe hearing, and what a fuzzy logic framework does differently. The claim is deliberately narrow. The classifier preserves gradation, and it stays transparent enough for a clinician to audit.

### Slide 2 — Crisp thresholds on continuous biology
Here is the problem, and it is clinical rather than abstract. Two patients one decibel apart get different labels, different follow-up and different candidacy decisions. That gap is smaller than audiometry's own test-retest error, so the boundary decides something the measurement cannot support. Nearly a fifth of our ears sit inside that fragile band. An average also discards shape, so a narrow notch and a flat loss can carry the same grade. I am arguing for changing how we grade, not for moving where we cut.

### Slide 3 — Fuzzy sets for graded severity
When a measurement belongs partly to several categories at once, the question stops being whether a patient is normal or mild and becomes how much of each. Memberships overlap at every boundary, and the rule base reasons over those partial memberships. The output is a continuous score, a configuration vector and an asymmetry index. Everything stays inspectable. You can find the rule that fired and argue with it.

### Slide 4 — Methods and the Mamdani inference system
The data are three NHANES cycles of working-age adults. The split is by participant, so both ears of one person stay on the same side and no bilateral leakage can flatter agreement. Memberships and rules were fitted on training data only, and every number that follows comes from the held-out set. Comparators are the WHO rules, XGBoost and a random forest. The framework is open source and the preprint is on SSRN. I analyse both ears, so a unilateral loss is not diluted across the pair.

### Slide 5 — Trapezoidal membership functions
Each band carries six trapezoids, fitted on the training distribution rather than copied from the WHO cutoffs. Their feet are tied to their neighbours' cores, so the six sum to exactly one at every threshold. At the boundary a patient is mostly mild and partly normal at the same time, and by the core of the next band they are fully mild. The transition is a slope, not a cliff. The grey behind the curves is the real distribution, so you can see where the boundaries land against actual ears.

### Slide 6 — 42 audiology-derived rules in four groups
The rule base has forty-two rules in four groups. Twelve map thresholds to severity and blend across transitional zones. Fourteen type the shape from slope and notch, which catches a notch hidden behind a normal average. Twelve turn inter-aural difference into a referral recommendation, so each ear is graded on its own thresholds. Four let the slope qualify the severity the average implies. Inference is standard Mamdani, so the output is an interpretable surface rather than a black box. The rule base is the part of this work I would most like you to audit.

### Slide 7 — FAI against WHO PTA-4 and ML comparators
Against the WHO reference, agreement is substantial, and the index tracks the reference closely on held-out ears. Agreement is not truth. All it means is that the index moves with the labels we already use, so a high value is partly a statement about the reference. In clear cases it matches the crisp grade almost exactly. In the borderline band it departs, and that departure is the point. Note the comparators. XGBoost and random forest look excellent because they are trained to reproduce PTA-4. They are the reference in disguise, not independent benchmarks. The correlation is attenuated because most of this cohort hears normally.

### Slide 8 — The 25/26 dB boundary is graded, not binary
Walk the average up one decibel at a time and nothing jumps. The index rises smoothly through the boundary while the crisp rule steps. At the boundary itself the ear holds more mild membership than normal, and the score sits about a point below the average. Do not read that point as a finding. It is noise. We are not abolishing categories. We are refusing to pretend a threshold has no width, and for a patient followed over years a continuous score beats a label that flips. The step is an artefact of the rule, not of the ear.

### Slide 9 — Clinical case studies: four archetypes
Four cases show what this buys. Case A sits just above the boundary, formally mild, and the score agrees in a graded way rather than by a step. Case B has a normal average but a deep notch at four kilohertz, which the shape rules type as precipitous. The average missed it. Case C is presbycusis, where the sloping shape survives instead of flattening into one number. Case D is asymmetric loss. The grade stays moderate and the asymmetry lifts the referral to expedited. That is the honest reading of the model, and it moves the clinical effort to the ear that needs it.

### Slide 10 — Configuration typing and asymmetry
Configuration typing is exploratory, and I will not oversell it. Most held-out ears come back flat or sloping, which reflects the age range we sampled. The rarer shapes are where the accuracy table does not reproduce across cycles, so I do not claim it. What the fuzzy layer adds is a membership vector per ear, so a mixed shape is not forced into one bucket. Asymmetry drives the referral output rather than the grade. I would treat the shape output as a research tool for now, not a clinical one.

### Slide 11 — Longitudinal tracking of sub-threshold change
These are scenarios, not a cohort. NHANES measures each person once, so there is no serial audiometry here and I will not quote a progression rate. What the panels show is the shape of the response. At a slow annual shift the index climbs for years while the category never moves. At a faster shift at the high frequencies the category steps once, and the index keeps recording the change between steps. A categorical endpoint would have scored those patients as unchanged, and that is the signal a hearing preservation trial wants.

### Slide 12 — Clinical implications
Where does this go in practice. Triage first, so a patient straddling a boundary is monitored rather than relabelled. Then amplification, where a continuous score maps onto gain and the configuration vector guides frequency-specific fitting. Then ototoxicity, where a small shift appears long before a PTA crosses a boundary, which matters for cisplatin. Then noise surveillance, since notch detection finds damage behind a normal average. Then low resource settings, on mobile audiometry. And trials that need a continuous endpoint. None of this needs a new device, only a different summary statistic on the report.

### Slide 13 — Limitations and next steps
The limitations are real. Air conduction only, so mixed loss needs bone conduction. The rule base is expert-derived and has not been through formal Delphi consensus, which is the obvious next methodological step. The cohort is working-age adults, so nothing here speaks to children or to the over seventies. And the reference standard carries the same boundary problem I am criticising, which is a fair objection. Next steps are multi-site validation, mobile integration, a web calculator with an API, and learned rule parameters. The full rule base is published with the preprint, so anyone in this room can audit it.

### Slide 14 — Take-home
Three take-home messages. A continuous, frequency-resolved index preserves gradation that crisp thresholds discard. Agreement with the WHO reference is substantial, with deliberate disagreement in the borderline zone. And the method is interpretable by construction, because the rule base can be read and changed. For a cochlear implant service the point is narrower than it sounds. A graded score makes the reasoning visible to the team and to the patient. What we have not tested is whether the index predicts implant candidacy. That is a study we still have to run.

### Slide 15 — Thank you
Thank you. The preprint is on SSRN and the code is on GitHub. I am happy to take questions on the rule base, the validation, or how this would sit inside a candidacy pathway.

---

## Hearing Loss Burden in Saudi Arabia: Machine-Learning Analysis of GBD 2023

14 slides. Slot 10 minutes at 130 words a minute, so the ceiling is 1,300 words.

Trimmed from 1,411 words (10.9 min) to 1,272 (9.8 min): 139 words cut, and every concession kept.

| Slide | Title | Words | Time | Running |
|---|---|---|---|---|
| 1 | Hearing Loss Burden in Saudi Arabia: Machine-Learning Analysis of GBD 2023 | 89 | 41 s | 41 s |
| 2 | A growing burden, a country that looks fine | 94 | 43 s | 1 min 24 s |
| 3 | Aims | 83 | 38 s | 2 min 03 s |
| 4 | Data and methods | 92 | 42 s | 2 min 45 s |
| 5 | Age structure is the engine | 96 | 44 s | 3 min 30 s |
| 6 | Today's low rate hides a large exposed population | 95 | 44 s | 4 min 13 s |
| 7 | Saudi Arabia vs GCC and MENA | 87 | 40 s | 4 min 54 s |
| 8 | Worse than target on 8 of 10 modifiable factors | 92 | 42 s | 5 min 36 s |
| 9 | The counterfactual result that cuts against intuition | 124 | 57 s | 6 min 33 s |
| 10 | A declining rate, a rising burden by 2040 | 100 | 46 s | 7 min 19 s |
| 11 | Clinical implications for hearing and CI services | 98 | 45 s | 8 min 05 s |
| 12 | Limitations | 94 | 43 s | 8 min 48 s |
| 13 | Conclusion | 88 | 41 s | 9 min 29 s |
| 14 | Thank you | 40 | 18 s | 9 min 47 s |
| **Total** | | **1,272** | **9 min 47 s** | **9.8 min** |

**Deck total: 1,272 words, 9.8 minutes at 130 words a minute.**

### Slide 1 — Hearing Loss Burden in Saudi Arabia: Machine-Learning Analysis of GBD 2023
Good morning. I am Sanyaolu Ameye, consultant ENT surgeon working in Tabuk. Saudi Arabia is one of the youngest countries in the world and one of the most metabolically exposed. In the next ten minutes I will show you what that combination is likely to do to hearing loss, and to demand for hearing and cochlear implant services. The analysis is a machine-learning model built on the GBD 2023 prevalence estimates. I will be precise about which parts of this are released GBD data and which parts are ours.

### Slide 2 — A growing burden, a country that looks fine
Saudi Arabia ranks near the bottom of two hundred countries on prevalence rate, which looks reassuring until you see why. Age structure is the dominant driver in every model we fitted, and this is one of the youngest populations anywhere. So the low rate is a demographic artefact rather than evidence of good hearing health. The world total is still climbing fast, and a low rate today can hide an adverse future, because the same young cohorts carry metabolic risk that will express itself as they age. Ageing is coming to this country too.

### Slide 3 — Aims
So we had three aims. Quantify the burden in global and GCC context, rather than reporting a national figure in isolation. Identify which modifiable factors could actually move it, using better-quartile counterfactuals rather than speculation. And forecast to 2040, because that is the horizon over which an implant service has to plan theatre lists, devices and staff. Before any of that, a word on what the data are and what they are not, because that decides how far the forecast can be trusted.

### Slide 4 — Data and methods
Let me be precise about provenance, because this is the question I would ask from the floor. The series is built from the released GBD 2023 results, downloaded from the IHME results tool. Those values are IHME modelled estimates, not national survey counts. GBD stops at 2023, so everything after that is our own multi-step projection from those estimates, trained through the last observed year, with covariates held on damped trends. Everything downstream inherits that uncertainty. Nothing from 2024 onward is a GBD release, and no clinician should read it as one.

### Slide 5 — Age structure is the engine
Globally cases roughly doubled between 1990 and 2023, and age structure is the important part of this progression. The projection is driven by UN population and age structure, and every covariate specification returns within a narrow band of the same figure, so nothing we offered the model moves it. Rates rose fastest in ageing, industrialising economies, with Djibouti, Korea and China at the top. Sub-Saharan Africa rose by a fraction of that, because youth dilutes the ageing effect, at the cost of a very large absolute burden. Any young country has a hidden hearing loss future.

### Slide 6 — Today's low rate hides a large exposed population
Saudi Arabia carries the fifth largest case load in MENA at a rate that ranks near the bottom of the world, and the reason is demographic. Only a small fraction of the population is over sixty-five. Meanwhile obesity and air pollution sit in the top percentiles globally. So the country looks like a low burden country on the metric that gets quoted in reports, and like a high exposure country on every metric that predicts the future. Both statements are true at the same time, and only one of them gets into the planning document.

### Slide 7 — Saudi Arabia vs GCC and MENA
Within the GCC only Oman has a lower rate. But the absolute case load is the largest in the GCC and fifth in MENA, and that distinction is what matters for service planning. A country can carry a modest rate and still need the largest number of cochlear implants in the region. Across MENA the range is wide and Saudi sits near the bottom of it. Scale and exposure, rather than rate, is the planning problem, and the absolute number is the one that sets a budget.

### Slide 8 — Worse than target on 8 of 10 modifiable factors
Against global better-quartile targets the gaps are metabolic and environmental, not developmental. Obesity, overweight, air pollution and smoking all sit well beyond target, and diabetes is the one that surprises most audiences. Water, sanitation, universal health coverage, PCV3 and physician density are all at or within half a point of target, so the usual development narrative does not explain this profile. This is not an access problem. These exposures act over decades, not at the bedside. If they are not the lever today, they still matter for the cohort arriving in 2040.

### Slide 9 — The counterfactual result that cuts against intuition
Here is the result that is counter-intuitive. Moving obesity, air pollution, smoking or diabetes to the global better-quartile target averts no cases a year in the corrected model. Taken one factor at a time the total is 14,000 a year, a third of one per cent of the burden, and it comes from the factors the model still responds to, smoking, physician density and water, rather than from the metabolic exposures. The zero is not a claim that obesity is harmless. It means those exposures sit outside the range where this model has support. Sensitivity sweeps show a flat response once age structure and income are controlled, which fits meta-analyses reporting modest and heterogeneous associations. So the immediate levers are demographic rather than behavioural.

### Slide 10 — A declining rate, a rising burden by 2040
By 2040 the all-ages rate falls and Saudi Arabia is the only GCC country projected to decline, while every neighbour rises. But absolute cases still climb, because population growth beats the rate decline. Among the over seventies prevalence is already over half, and that is the rate waiting for today's cohorts. The decline is a youth effect, not a health system success. Rate decline and case growth are not in conflict. They are the same population ageing. That is why the two figures on this slide do not disagree. Capacity planning should follow the case count rather than the rate.

### Slide 11 — Clinical implications for hearing and CI services
Four implications for hearing and cochlear implant services. Scale capacity now, because the over seventy caseload grows whatever we do about prevention. Screen the young, so that metabolic risk becomes early intervention rather than late detection. Prevent across sectors, since obesity, diabetes and air pollution sit in health and environment portfolios at once. And benchmark on Saudi's own trajectory rather than the regional average, because its neighbours are heading the other way. The cohorts now entering adulthood are the ones our implantation decisions will shape, and that gives roughly fifteen years of lead time for training and equipment.

### Slide 12 — Limitations
I will like to state some Caveats. The 2024 to 2040 series is our projection, not a released GBD forecast, and it assumes current trends persist. The GBD estimates are themselves modelled, with their own uncertainty, which we inherit. The counterfactuals are predictive attributions, not causal estimates, and unobserved confounders such as noise exposure and ototoxic drugs could reorder the ranking. Country-level aggregation hides subnational gradients, and the over seventy stratum is the least well modelled. None of this changes the direction of the finding. It bounds how precisely the finding should be quoted.

### Slide 13 — Conclusion
So, in summary. The low rate is a demographic illusion, not good hearing health. The exposure profile is among the worst in the world on the factors that predict future loss. Immediate counterfactual gains are small, but the cohort effect is real. Prevention still matters, but it works through the cohort rather than through the year. Capacity built now protects the cohorts arriving between 2040 and 2060, and for an implant service that means planning against absolute case numbers rather than a rate that will keep looking reassuring.

### Slide 14 — Thank you
Thank you. The code and the full pipeline are on GitHub, the underlying series is GBD 2023 from IHME, and I am happy to take questions on the model, the counterfactual method, or what this implies for implant capacity planning.

---

## Recomputed totals

| Deck | Slides | Words before | Min before | Words after | Min after | Cut |
|---|---|---|---|---|---|---|
| Fuzzy SNHL classification | 15 | 1,713 | 13.2 | **1,295** | 10.0 | 418 |
| Hearing loss burden, Saudi Arabia | 14 | 1,411 | 10.9 | **1,272** | 9.8 | 139 |
| **Both** | **29** | **3,124** | **24.0** | **2,567** | **19.7** | **557** |

Timings are words divided by 130, rounded to the second. Slide 15 (fuzzy) and slide 14 (Saudi) carry the hand-over to questions.
