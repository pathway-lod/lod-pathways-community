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

**With the transferred-EC tier** (`ORPHAN_SEQ=1`; an EC transferred from proteins of the same UniRef50 cluster, sequence family, weight 0.50; outputs with the suffix `_seq`):

| links | compounds with a candidate | beating the null (p < 0.05), v1 | v2 |
|---|---|---|---|
| MR ≤ 3 | 38 | 2 | 0 |
| MR ≤ 10 | 71 | 1 | 0 |
| MR ≤ 25 | 79 | 0 | 1 |

- **No change at the whole-dataset level.** The new tier gives more candidates (best score ≥ 0.5 for all 71 compounds at MR ≤ 10 instead of 57), but not more than chance.
- **The THT compound now gets its pathway.** For M322T887 (the [M+Na]+ peak of the caffeoyltyramine hypothesis) the hydroxycinnamic acid tyramine amides pathway becomes a candidate through the THT genes (`Solyc08g068710` and the neighbour `Solyc08g068790`), but at rank **74 of 92** in v1 (score 0.50, below 41 pathways at 0.70 from EC plus ortholog hits on generic metabolism) and rank **25 of 92** in v2. Its p-value for any pathway of that score is 0.997. The same happens for M962T828 (rank 52 of 65 in v1, rank 7 of 65 in v2).
- ## Testing the claim: does the metabolite side single out the THT pathway?

Two tests ([`metabolite_side_benchmark.py`](../pilots/pairedomics_overlap/metabolite_side_benchmark.py), `orphan_features_v2.py` with `ORPHAN_SEQ=1 ORPHAN_GENERIC=1`).

**1. Leave-one-out on PlantMetWiki (known answers).** Each compound with a structure (2,158 compounds in 962 pathways with at least 4 structures) is hidden and its pathway is ranked from the metabolite side only. Ties count as the midpoint.

| Method | top-1 | top-5 | top-10 | median rank (fraction of pathways) |
|---|---|---|---|---|
| random | 0.005 | 0.020 | 0.034 | 0.29 |
| pathway size (baseline) | 0.024 | 0.046 | 0.068 | 0.15 |
| mass delta, specific conjugations only | 0.047 | 0.138 | 0.172 | 0.50 |
| **mass delta, specific + generic (2H, O, CH2, H2O)** | 0.218 | 0.517 | 0.620 | 0.005 |
| relative mass defect | 0.119 | 0.239 | 0.278 | 0.055 |
| structure, Morgan bits, top-3 mean | 0.413 | 0.750 | 0.834 | 0.002 |
| **structure, Morgan counts, top-3 mean** | **0.452** | **0.770** | 0.839 | 0.002 |
| structure, atom pairs counts, top-3 mean | 0.443 | 0.749 | 0.816 | 0.002 |
| structure, RDKit path bits, top-3 mean | 0.374 | 0.685 | 0.766 | 0.002 |

- **Both sides carry real signal**, far above random and above the pathway-size baseline. Structure similarity is the strongest; count fingerprints and the top-3 mean (instead of the single best hit) are best. This chooses the fingerprint on a benchmark and not on the THT example.
- **Generic mass deltas matter.** An earlier version of `orphan_features_v2.py` dropped 2H, O, CH2 and H2O as "too generic"; the benchmark shows they are the informative ones (top-5 52 % against 14 % for specific conjugations only). That choice was wrong and is now an option (`ORPHAN_GENERIC=1`).
- **Optimistic.** The hidden compounds have pathway neighbours that differ by exactly such a group (reaction partners). A true orphan is not guaranteed to have one.

**2. The THT case.**
- **With the hypothesis structure** (an oracle): the PWY-5474 pathway is rank 1 of 962 with atom pairs, 2 with Morgan counts, 13.5 with Morgan bits, 20 with RDKit path. This needs a structure.
- **Mass only** (neutral 299.1152): with specific + generic deltas it is rank **1 of 962**; only 3 pathways have any mass-delta hit (the feature is one OH above p-coumaroyltyramine and one CH2 below feruloyltyramine). With the specific conjugations alone it has no hit.
- **Gene side only** (transferred-EC tier): rank 74 of 92 gene-supported pathways (v1).
- **Both sides in agreement.** Of the 92 pathways with gene support for M322T887, **3** also have a mass-delta hit (suberin monomers, hydroxycinnamic acid tyramine amides, Amaryllidacea alkaloids), including the right one. For M962T828 the right pathway has no mass-delta hit.
- **Across the 71 orphan compounds with gene candidates**, 17 have at least one pathway supported by both the gene tiers and a mass delta, against 10.3 expected when the gene annotation is shuffled (P = 0.002). For the two THT compounds the agreement is not significant on its own (36 to 39 % chance); the excess is a property of the whole set, about 7 compounds.

**Reading.** The claim is **partly supported**: the metabolite side does single out the pathway, **but through the pathway neighbours and the structure hypothesis**, and the benchmark shows it is not special to THT. A method that finds THT-like hits is **agreement of independent sides**: (1) a gene-side candidate list (sequence, EC, ortholog), (2) a metabolite-side list from mass deltas to pathway metabolites (and, when a structure hypothesis exists, count-fingerprint similarity, top-3 mean), (3) the intersection, ranked by the combined score. It narrows 92 candidates to 3 for the THT compound. **Caveats:** THT is the development case, the generic deltas were reinstated after seeing the benchmark and the THT rank (a forking path), the benchmark is leave-one-out inside PlantMetWiki, the intersection still leaves a median of 3 pathways per compound (5 of 17 compounds have exactly one), and no structure candidates exist for real orphans (the NPDB annotation table of the dataset is not mass-consistent).

**Reading.** The tier brings the right pathway into the list, but does not make it stand out: a candidate list built from gene tiers alone is long, and the correct pathway sits among many equally supported ones. It needs the metabolite side (mass, structure) to be picked out, as in the THT example.

**Reading.** In this dataset, gene-side evidence alone does not prioritize orphan features; a correlation is a lead, not a pathway. The THT example of notebook 06 works because the compound class was known in advance.

**Not done / limits.** No MS/MS or literature check is possible (MetaboLights MTBLS1039 lists no MS/MS or annotation file; the paper was not readable). The weights, deltas, gate margin and the MR ≤ 10 cut are drafts. The null shuffles only the gene annotation.

**Next.** Restrict to specialized-metabolism pathways, add enzyme-class and substrate-mass consistency, and test on the ipecac pilot where answers are known.
