# Using public spectra to annotate orphan features: ideas (brainstorm, untested)

**Status.** Ideas, not results. Nothing here has been run. Context: [README.md](README.md) (data and plan) and [results/README.md](results/README.md) (overlap results).

**Starting point.** An orphan feature has no PlantMetWiki mass match, but the graph gives it a candidate pathway through gene links and mass deltas. The public spectral libraries (CASMI 2026 training set, 275,810 structures, 2.5 M spectra) can help in five ways.

## 1. The library as a source of candidate structures

- Today an orphan has no structure candidates (the open gap of the [orphan analysis](../../minimum_information/orphan-features-usecase.md)).
- Mass-match the feature to the library structures (neutral mass, 5 ppm, per adduct), then rank the hits with the same graph evidence: similarity to the members of the candidate pathway and mass delta to a member.
- Example: caffeoyltyramine is not in PlantMetWiki, but it is in the library and fits the mass of the THT feature.
- This gives the structure-side tier a realistic candidate set instead of an oracle structure.

## 2. Check a hypothesis against reference MS/MS

- If the feature has its own MS/MS, compare it with the library spectra of the candidate (caffeoyltyramine has 22) with matchms cosine, and look for the expected fragments and neutral losses.
- A match would raise a mass-only guess to a spectrum-supported annotation.

## 3. Spectral similarity as a new link in the graph

- Compare the feature's spectrum with the spectra of the pathway members that have spectra (about half of them). A similar spectrum adds an edge from the feature to the pathway, as in molecular networking.
- It needs a family and a weight in the score. Probably the same family as structure similarity (both reflect shared substructures): take the maximum, do not combine.

## 4. Calibrate that tier with a leave-one-out test (suggested first experiment)

- Same design as the [metabolite-side benchmark](../pairedomics_overlap/metabolite_side_benchmark.py): hide each compound with spectra from its pathways, rank the pathways by spectral similarity to the other members, and compare with random, pathway size, mass-only and fingerprint similarity.
- This gives a measured weight instead of a draft one.
- Spectra of the same skeleton from other libraries must be excluded (same `inchikey14`), or the test leaks.
- It needs only the spectra of the 1,258 matched compounds, a fraction of the 2.5 M spectra, and no feature data.

## 5. Smaller uses

- Spectra can confirm or reject the assumed adduct (an open point of the THT example).
- A formula tool (SIRIUS or MIST-CF) can narrow the mass to a formula before the mass-delta step.
- The matched spectrum gives a confidence level for the annotation, which can be recorded in the evidence graph.

## Limits

- **The feature needs its own MS/MS.** The MEANtools tomato data in MetaboLights have none, so ideas 2 and 3 cannot be run on the THT example. Idea 1 works from mass alone and idea 4 needs no feature data. Which datasets have MS/MS is the main open question.
- **Coverage is about 50 %:** half of the pathway members have no reference spectrum.
- **Similar spectra do not always mean the same pathway;** structural neighbours can sit in different pathways.
- **Idea 1 can add many candidates for one mass;** the graph evidence has to do the ranking, as in the benchmark.
