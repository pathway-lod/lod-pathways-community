# Use case: can PlantMetWiki prioritize orphan MEANtools features? (negative result, draft)

**Question.** Of the MEANtools tomato features without a PlantMetWiki compound (95 of 138; 79 compounds after merging adducts and isotopes, with at least one gene link), can the pathways reached by their correlated genes rank candidates for annotation better than chance?

**Method** (scripts in [`pilots/pairedomics_overlap`](../pilots/pairedomics_overlap/)):
- `orphan_features.py` (model v1): gene tiers (locus 0.90, UniProt 0.80, EC 0.40, OrthoDB ortholog 0.50) for all 5,380 correlated genes; links are MR ≤ 10 and r > 0; score = noisy-OR of the membership and sequence families. Null: 1,000 random gene sets of the same size (annotation shuffled); `p_any` is the chance that random genes give a pathway at least as good anywhere.
- `orphan_features_v2.py` (model v2, drafts): (1) gene weights divided by 1 + log2 k, k = pathways a gene reaches through that tier; (2) a mass-delta tier (0.20; neutral mass differs by a specific conjugation from a pathway metabolite, ≤ 5 ppm); (3) a mass-defect gate (score × 0.5 if the compound's relative mass defect is outside that of the pathway's non-cofactor metabolites ± 75 ppm).
- Single-reaction diagrams (`RC…`, `…-RXN`), which PlantMetWiki types as pathways, are excluded (the first run had them in the candidate list).

**Results** (compounds whose best pathway beats the null at p < 0.05):

| links | compounds | expected by chance | v1 | v2 |
|---|---|---|---|---|
| MR ≤ 3 | 35 | 1.75 | 2 | 2 |
| MR ≤ 10 | 69 | 3.5 | 1 | 0 |
| MR ≤ 25 | 79 | 4.0 | 0 | 1 |

- The gene tiers reach some pathway for most orphan compounds (69 of 79 at MR ≤ 10), with a median of about 14 candidates each, **but not more often than chance**.
- v1's top candidates (sterol and glycoalkaloid pathways via the locus tier) were co-induced defence genes, and their masses do not fit (low mass defect, or m/z 265.57 that cannot be a singly charged ion). v2 removes them from the top, but the new top (PRPP biosynthesis, calmodulin calcium transport, secologanin and strictosidine) is generic enzyme chemistry and also at chance level.

**Reading.** In this dataset, gene-side evidence alone does not prioritize orphan features; a correlation is a lead, not a pathway. The THT example of notebook 06 works because the compound class was known in advance.

**Not done / limits.** No MS/MS or literature check is possible (MetaboLights MTBLS1039 lists no MS/MS or annotation file; the paper was not readable). The weights, deltas, gate margin and the MR ≤ 10 cut are drafts. The null shuffles only the gene annotation.

**Next.** Restrict to specialized-metabolism pathways, add enzyme-class and substrate-mass consistency, and test on the ipecac pilot where answers are known.
