
## A Fuzzy Logic Framework for SNHL Classification
15 slides. Slot 10 minutes.

| Slide | Words | Time |
|---|---|---|
| 1 | 76 | 35 s |
| 2 | 107 | 49 s |
| 3 | 108 | 50 s |
| 4 | 109 | 50 s |
| 5 | 147 | 68 s |
| 6 | 131 | 60 s |
| 7 | 112 | 52 s |
| 8 | 118 | 54 s |
| 9 | 125 | 58 s |
| 10 | 118 | 54 s |
| 11 | 130 | 60 s |
| 12 | 107 | 49 s |
| 13 | 164 | 76 s |
| 14 | 116 | 54 s |
| 15 | 41 | 19 s |


### Slide 1 — Jeddah, Kingdom of Saudi Arabia · 26–28 November 2026
Good morning. I am Sanyaolu Ameye, an ENT surgeon in Tabuk. In the next ten minutes I want to show you why a pure-tone average is a blunt way to describe hearing, and what a fuzzy logic framework does differently. This work is on SSRN as a preprint, and the DOI is on the methods slide. The claim is deliberately narrow. The classifier preserves gradation, and it does so transparently enough for a clinician to audit.

### Slide 2 — Crisp thresholds on continuous biology
Here is the problem, and it is clinical rather than abstract. Patient A has a four-frequency average of 25 decibels and is called normal. Patient B has 26 and is called mild hearing loss. One decibel separates them, inside audiometry's own five to ten decibel test-retest error, yet the label changes follow-up and candidacy. In our sample 18 per cent of ears sit within five decibels of a WHO boundary. And one average also discards shape, so a four kilohertz notch and a flat thirty decibel loss can carry the same grade. That is an argument for changing how we grade, not for moving where we cut.

### Slide 3 — Fuzzy sets for graded severity
Fuzzy set theory lets a measurement belong partly to several categories at once. Instead of asking whether 26 decibels is normal or mild, we ask how much it is normal and how much it is mild. Membership functions overlap at every boundary, and the rule base reasons over those partial memberships. The output is a continuous index from 0 to 100, plus a configuration vector and an asymmetry index. The important property for a clinician is that everything stays inspectable. You can find the rule that fired and argue with it. That is the difference between a score you can inspect and a score you have to trust.

### Slide 4 — Methods and the Mamdani inference system
The data are three NHANES cycles that tested adults aged 20 to 69, giving 10,889 participants and 19,623 clean ears. The split is by participant, 80 to 20, so both ears of one person stay on the same side and no bilateral leakage can flatter agreement. Membership functions and rules were fitted on training data only, and every number that follows comes from the held-out set. Comparators are the WHO PTA-4 rules, XGBoost and a random forest. The framework is open source, and the preprint is on SSRN with DOI 10.2139 slash ssrn.7532157. Both ears are analysed, so a unilateral loss is not diluted by averaging across the pair.

### Slide 5 — Trapezoidal membership functions
Each frequency band carries six trapezoidal functions. The parameters were fitted on the training distribution, not copied from the WHO cutoffs, and each trapezoid's feet are tied to its neighbours' cores rather than fitted on their own. That makes the six a Ruspini partition: they sum to exactly one at every threshold from zero to 120 decibels, and the graded bands are ten to fourteen decibels wide instead of the two decibels an independent fit left. The consequence is on the right. At 26 decibels a patient is 29 per cent normal and 71 per cent mild at the same time. At 30 they are fully mild. The transition is a slope, not a cliff. We chose trapezoids because these distributions have flat cores and asymmetric shoulders. The grey overlay is the actual NHANES distribution, so you can see where the boundaries fall relative to real ears.

### Slide 6 — 42 audiology-derived rules in four groups
The rule base has 42 rules in four groups. Twelve map thresholds to severity and blend across transitional zones. Fourteen type the audiogram from slope and notch, which is how we catch a noise notch hidden behind a normal average. Twelve turn inter-aural difference into a referral recommendation rather than a severity adjustment, so an ear is always graded on its own thresholds. Four let the slope qualify the severity the average implies. Inference is Mamdani min-max composition with centroid defuzzification, which is a standard, well-understood route that returns an interpretable surface rather than a black box. Nothing here needs a graphics card. Four groups, 42 rules, and every rule fits on one printed line. The rule base is the part of this work I would most like you to audit.

### Slide 7 — FAI against WHO PTA-4 and ML comparators
Against the WHO reference the index reaches weighted kappa 0.946, with Spearman 0.80 and a mean absolute error of 4.3 decibels on 3,913 held-out ears. In clear cases, more than five decibels from any boundary, it agrees with the crisp grade 99.2 per cent of the time. In the borderline band agreement falls to 86.3 per cent, and that disagreement is the point. Note the comparators. XGBoost and random forest look excellent because they are trained to reproduce PTA-4 itself. They are the reference in disguise, not independent benchmarks. Kappa was weighted and quadratic, across the six WHO severity categories. The correlation is attenuated because most of this cohort has normal hearing.

### Slide 8 — The 25/26 dB boundary is graded, not binary
This slide is the one I would show a trainee. Walk the average up one decibel at a time. At 24 the index is 22.4 and the ear already holds more mild membership than normal. At 26 the crisp rule jumps to mild, while the fuzzy system reports 25.0, with membership split 29 per cent normal and 71 per cent mild; at 27 it is 26.3, and by 28 decibels it is 27.5. We are not abolishing categories. We are refusing to pretend that a threshold has no width. For a patient monitored over years, that continuous score is more informative than a label that flips. The step is an artefact of the rule, not of the ear.

### Slide 9 — Clinical case studies: four archetypes
Four cases show what this buys. Case A sits at 27.5 decibels, formally mild, with an index of 26.9 and membership of 0.18 normal against 0.82 mild, so grade and score agree in a graded way. Case B has a normal average of 22.5 decibels but a 30 decibel notch at four kilohertz, which the shape rules type as precipitous. The average missed it. Case C is presbycusis, where the sloping configuration survives instead of flattening into one number. Case D is asymmetric loss, the tested ear at 55 decibels and the other at 28.8: the grade stays 53.9, moderate, and the asymmetry raises the referral output to expedited. That is the honest reading of the model, and it changes where the clinical effort goes.

### Slide 10 — Configuration typing and asymmetry
Configuration typing is presented as exploratory. Across the held-out ears the shape rules return flat for 41.7 per cent and sloping for 24.5 per cent, which reflects our age range. Steeply sloping, precipitous and rising shapes are less common, and their accuracy table is not reproducible across cycles, so I do not claim it. What the fuzzy layer adds is a six-shape membership vector per ear, so a mixed shape is not forced into one bucket. Taking asymmetry as the largest inter-aural difference, 34 per cent of participants exceed fifteen decibels, and that drives the referral output rather than the grade. I would treat the shape output as a research tool rather than a clinical one for now.

### Slide 11 — Longitudinal tracking of sub-threshold change
These are scenarios, not a cohort: NHANES measures each person once, so we have no serial audiometry and I will not quote a progression rate. What the panels show is the shape of the response. Feed the model 0.7 decibels a year and the index climbs 1.3 points a year for eight years while the category never changes. Feed it 3 decibels a year at the high frequencies and the index climbs 7.6 points over four years; the category steps once, at year two, and the index records the intervening change a category cannot. A categorical endpoint would have recorded those patients as unchanged, and that is exactly the signal a hearing preservation trial wants. Age-related change dominates this subgroup, which is what a cohort sampled this way should show.

### Slide 12 — Clinical implications
Where does this go in practice. Triage first, so a patient straddling a boundary is monitored rather than relabelled. Then amplification, where a continuous index maps onto gain and the configuration vector guides frequency-specific fitting. Then ototoxicity monitoring, where a five point shift appears long before a PTA crosses a boundary, which matters for cisplatin and aminoglycoside protocols. Then noise surveillance, since notch detection finds early damage behind a normal average. Then low resource settings, because this could run on mobile audiometry with no server. And trials that need a continuous endpoint. None of this needs a new device, only a different summary statistic on the report.

### Slide 13 — Limitations and next steps
The limitations are real. We have air conduction only, so mixed loss needs bone conduction. The rule base is expert-derived and has not been through formal Delphi consensus, which is the obvious next methodological step. The cohort is adults aged 20 to 69 only, so nothing here speaks to children or to adults over 70. There is no extended high frequency audiometry. And the reference standard carries the same boundary problem I am criticising, which is a fair objection. Two of the membership functions' properties I would flag: the graded bands are ten to fourteen decibels wide by construction, which is the design choice that makes the index graded, and the shape rules returned no crisp configuration for 3.2 per cent of held-out ears, which we report rather than impute. Next steps are multi-site validation, mobile integration, a web calculator with an API, and learned rule parameters. The full rule base is published with the preprint, so anyone in this room can audit it.

### Slide 14 — Interpretable by design, a rule base clinicians can inspect, question and modify.
Three take-home messages. A continuous, frequency-resolved index preserves gradation that crisp thresholds discard. Agreement with the WHO reference is substantial at kappa 0.946, with deliberate disagreement in the borderline zone. And the method is interpretable by construction, because the rule base is something a clinician can read and change. For a cochlear implant service the point is narrower than it sounds. A graded score makes the reasoning visible to the team and to the patient. We have not tested whether the index predicts implant candidacy; that is a study we still have to run. The DOI is on the closing slide and the repository is public, so anyone can check the rule base against the claim.

### Slide 15 — Questions and discussion
Thank you. The preprint is on SSRN with the DOI on screen, the code is on GitHub, and I am happy to take questions on the rule base, the validation or how this would sit inside a cochlear implant candidacy pathway.

**Deck total: 1709 words, 13.1 minutes.** Slot 10 min — **overruns by 3.1 min, about 408 words to cut.**

---

## Hearing Loss Burden in Saudi Arabia: Machine-Learning Analysis of GBD 2023
14 slides. Slot 10 minutes.

| Slide | Words | Time |
|---|---|---|
| 1 | 106 | 49 s |
| 2 | 99 | 46 s |
| 3 | 101 | 47 s |
| 4 | 113 | 52 s |
| 5 | 107 | 49 s |
| 6 | 100 | 46 s |
| 7 | 107 | 49 s |
| 8 | 113 | 52 s |
| 9 | 119 | 55 s |
| 10 | 102 | 47 s |
| 11 | 106 | 49 s |
| 12 | 103 | 48 s |
| 13 | 107 | 49 s |
| 14 | 45 | 21 s |


### Slide 1 — Jeddah, Kingdom of Saudi Arabia · 26–28 November 2026
Good morning. I am Sanyaolu Ameye, consultant ENT surgeon in Tabuk. Saudi Arabia is one of the youngest countries in the world and one of the most metabolically exposed. In the next ten minutes I will show you what that combination is likely to do to hearing loss, and to demand for hearing and cochlear implant services. The analysis is a machine-learning model built on the GBD 2023 prevalence estimates, and I will be precise about what that provenance means before I show you a single number. I will also be explicit about which parts of this are released GBD data and which parts are ours.

### Slide 2 — A growing burden, a country that looks fine
Hearing loss affects 1.81 billion people worldwide, heading toward 2.1 billion by 2040 on status quo trends. Saudi Arabia ranks 187th of 200 on prevalence rate, which looks reassuring until you see why. Age structure is the dominant driver in every model we fitted, and Saudi Arabia has one of the youngest populations anywhere, with only 2.8 per cent over 65. So the low rate is a demographic artefact rather than evidence of good hearing health. And a low rate today can hide an adverse future, because the same young cohorts carry metabolic risk that will express itself later.

### Slide 3 — IDENTIFY LEVERS
Three aims. Quantify the burden in global and GCC context, rather than reporting a national figure in isolation. Identify which modifiable factors could actually move it, using better-quartile counterfactuals rather than speculation. And forecast to 2040, because that is the horizon over which a cochlear implant service has to plan theatre lists, devices and staff. Before any of that, a word on what the data are and what they are not, because that determines how far the forecast can be trusted. Everything after slide four is either a released GBD estimate or a projection, and I will label which is which.

### Slide 4 — Data and methods
Let me be precise about provenance, because this is the question I would ask from the floor. The series is built from the released GBD 2023 results, downloaded from the IHME results tool in July 2026, covering 204 countries and territories from 1990 to 2023, both sexes, all ages and five age bands. Those values are IHME modelled estimates, not national survey counts. The 2040 figures are not a GBD release. They are our own multi-step projection from those estimates, trained through 2023 with an expanding-window split, and it holds covariates at damped trends. Everything from 2024 onward is therefore a forecast, and no clinician should read it as a published GBD figure.

### Slide 5 — Age structure is the engine
Globally cases went from 0.86 to 1.81 billion between 1990 and 2023. Age structure is the important part of this slide. The projection is driven by UN population and age structure, and every covariate specification returns between 2.10 and 2.13 billion, so nothing we offered the model moves it. Rates rose fastest in ageing, industrialising economies, with Djibouti, Korea and China at the top. Sub-Saharan Africa rose only 11 per cent because youth dilutes the ageing effect, at the cost of a very large absolute burden. Any young country has a hidden hearing loss future. That single contrast is the argument for planning ahead in this region.

### Slide 6 — Today's low rate hides a large exposed population
Saudi Arabia had 4.1 million cases in 2023, fifth largest in MENA, at a rate of 12,173 per 100,000. That rate ranks 187th of 200 and is the lowest in the GCC after Oman, and the reason is demographic. Only 2.8 per cent of the population is over 65. Meanwhile obesity sits at the 91st global percentile and PM2.5 at the 99th. So the country looks like a low burden country on the metric that gets quoted in reports, and like a high exposure country on every metric that predicts the future. Both statements are true at the same time.

### Slide 7 — Saudi Arabia vs GCC and MENA
Within the GCC only Oman has a lower rate. But the 4.1 million cases are the largest absolute burden in the GCC and fifth in MENA, and that distinction matters for service planning. A country can carry a modest rate and still need the largest number of cochlear implants in the region. The MENA range runs from Iraq at 11,764 to Tunisia at 18,128, so Saudi sits near the bottom of that distribution. Scale and exposure, rather than rate, is the planning problem. For implant planning, that absolute number is the figure that sets the budget. That is the number I would take into a planning meeting.

### Slide 8 — Worse than target on 8 of 10 modifiable factors
Against global better-quartile targets Saudi Arabia misses on 8 of 10 modifiable factors. The real gaps are metabolic and environmental. Obesity is 39.8 per cent against a target of 13.1, overweight 71.7 against 38, PM2.5 at 73 micrograms against 12.7, and smoking 13.3 against 9.8. Diabetes is 20.8 per cent against a target of 8.8 and rising, which surprises most audiences. Water, sanitation, universal health coverage, PCV3 and physician density all sit at or within half a point of target, so the usual development narrative does not explain this profile. This is not an access problem. If the exposures are not the lever today, they still matter for the cohort arriving in 2040.

### Slide 9 — The counterfactual result that cuts against intuition
Here is the result that cuts against intuition, and reviewers always challenge it. Moving obesity, PM2.5, smoking or diabetes to the global better-quartile target averts no cases a year in the corrected model, 0.00 per cent of the burden, and only 14,000 a year, 0.34 per cent, when the factors are taken one at a time. Sensitivity sweeps confirm the response is flat once age structure and income are controlled. That is consistent with meta-analyses showing modest and heterogeneous associations. So the immediate levers in this model are demographic rather than behavioural, which is why the forecast matters more than the counterfactual for this country. It is also why any prevention argument needs a cohort argument attached to it.

### Slide 10 — A declining rate, a rising burden by 2040
By 2040 the all-ages rate falls 4.3 per cent, and Saudi Arabia is the only GCC country projected to decline, against UAE plus 7.0, Kuwait plus 11.8 and Qatar plus 18.4. But absolute cases still rise 20.9 per cent, from 4.10 to 4.96 million, because population growth beats the rate decline. Among the over 70s, prevalence already exceeds 57 per cent. Two reminders on this slide. Everything to 2023 is GBD 2023, and everything after it is our projection. And the decline is a youth effect, not a health system success. Capacity planning should follow the case count rather than the rate.

### Slide 11 — Clinical implications for hearing and CI services
Four implications for hearing and cochlear implant services. Scale capacity now, planning for close to five million cases by 2040, because the over 70 caseload grows whatever we do about prevention. Screen the young, so that metabolic risk becomes early intervention rather than late detection. Prevent across sectors, since obesity, diabetes and PM2.5 sit in health and environment portfolios at once. And benchmark on Saudi's own trajectory rather than the regional average, because its neighbours are heading the other way. The 2040 to 2060 cohorts are the ones our current implantation decisions will shape. That gives roughly fifteen years of lead time for training and equipment.

### Slide 12 — 
Caveats, and I would rather state them than be asked. The 2024 to 2040 series is our projection from GBD 2023, not a released GBD forecast, and it assumes current trends persist. The GBD 2023 estimates are themselves modelled, with their own uncertainty, which we inherit. The counterfactuals are predictive attributions, not causal estimates, and unobserved confounders such as noise exposure and ototoxic drugs could reorder the ranking. Country-level aggregation hides subnational gradients, and the over 70 stratum is the least well modelled. None of these changes the direction of the finding, and all of them bound how precisely it should be quoted.

### Slide 13 — Prevention and hearing-care capacity built now will protect the 2040–2060 cohorts.
So, in summary. The low rate is a demographic illusion, not good hearing health. The exposure profile is among the worst in the world on the factors that predict future loss. Immediate counterfactual gains are small, but the cohort effect is real and measurable. Capacity built now is what protects the 2040 to 2060 cohorts, and for a cochlear implant service that means planning against absolute case numbers rather than against a rate that will keep looking reassuring. The direction of the finding is robust to every caveat on the previous slide. The absolute number is the one that decides how many implants we need to fund.

### Slide 14 — Questions and discussion
Thank you. The code and the full pipeline are on GitHub, the underlying series is GBD 2023 from IHME, and I am happy to take questions on the model, on the counterfactual method, or on what this implies for implant capacity planning in the Kingdom.

**Deck total: 1428 words, 11.0 minutes.** Slot 10 min — **overruns by 1.0 min, about 128 words to cut.**
