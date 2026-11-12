# How to read the score of the ranked queries

The three megaqueries `ranked-pathway-metabolites`, `ranked-pathway-reactions` and `ranked-pathway-genes` ([queries](https://pathway-lod.github.io/sparql-examples-pmw/examples/MinimumInformationTiers/)) list **pathway components** (a metabolite, a reaction or a gene **in a pathway**) and give each a `score`. This page says exactly how the score is computed, and where every piece of evidence is checked.

## The rule, step by step

1. **Evidence tiers.** Each tier is a check with a fixed **weight** between 0 and 1 (the tables below). A component *passes* a tier when the check is true for it. The tiers it passes are in the column `tiersPassed`.
2. **Families.** Tiers that are not independent of each other (for example EC and Rhea; all the annotation tools; for genes, the genes of a biosynthetic gene cluster and the genes of a pathway) are in the same **family**.
3. **One weight per family.** For each family, the component takes the weight of the **strongest tier it passes** (the maximum, not the sum). The columns `wIdentity`, `wRelatedness`, `wReaction` (metabolites), `wDatabase`, `wEnzyme`, `wOmics`, `wPrediction` (reactions) and `wMembership`, `wOmics`, `wSequence` (genes) are these weights; an empty or 0 column means that no tier of the family was passed.
4. **Noisy-OR over the families.** `score = 1 - (1 - w_family1) x (1 - w_family2) x ...`. Independent families add up; a second family can only raise the score, and the score never exceeds 1.
5. **Ranking.** The result is sorted by `score`, and for metabolites then by the number of supporting tools. Equal scores are ties.

The weights are **drafts**. The score is an **ordered measure of how much independent evidence a component has**, not a probability, until the weights are calibrated (hold-out test and null model, see the notebook).

### Support factor of the metabolite identity weight

The identity weight is `base x support`, with `base` = 0.95 for an exact InChIKey (with stereo and charge) and 0.80 for a first-block (connectivity) match, and `support` = 0.65 for 1 annotation tool, 0.80 for 2, and 1.0 from 3 tools (`0.5 + 0.15 x tools`, at most 1).

## Worked examples (taken from the results of 2026-11-12)

| Component | Tiers passed | Family weights | Calculation | Score |
|---|---|---|---|---|
| a metabolite annotated by 5 tools, exact key | `inchikey-exact, inchikey-first-block` | identity 0.95 x 1.0 = 0.95 | 1 - (1 - 0.95) | **0.95** |
| a metabolite annotated by 1 tool, exact key | same | identity 0.95 x 0.65 = 0.6175 | 1 - (1 - 0.6175) | **0.6175** |
| a metabolite annotated by 1 tool, first block only | `inchikey-first-block` | identity 0.80 x 0.65 = 0.52 | 1 - (1 - 0.52) | **0.52** |
| a metabolite, 5 tools, exact, and the same formula layer as another pathway metabolite | `inchikey-exact, inchikey-first-block, structure-similarity` | identity 0.95, relatedness 0.30 | 1 - (0.05 x 0.70) | **0.965** |
| a metabolite only found by the formula-layer proxy | `structure-similarity` | relatedness 0.30 | 1 - 0.70 | **0.30** |
| a reaction with an EC number only | `ec;` | database 0.40 | 1 - 0.60 | **0.40** |
| a reaction with Rhea and UniProt | `rhea;uniprot;` | database 0.60, enzyme 0.70 | 1 - (0.40 x 0.30) | **0.88** |
| a reaction with EC and UniProt (no Rhea) | `ec;uniprot;` | database 0.40, enzyme 0.70 | 1 - (0.60 x 0.30) | **0.82** |
| a gene listed in the pathway and in a cluster whose other gene is also in it | `gene-in-plantmetwiki-pathway, bgc-both-in-pathway, bgc-partner-in-pathway` | membership max(0.90, 0.70, 0.50) = 0.90 | 1 - (1 - 0.90) | **0.90** (the cluster adds nothing: not independent) |

## Where each piece of evidence is checked

Each branch of a megaquery is one piece of evidence, with a comment `family ...` and its weight. The same weights are in [`notebooks/weights.csv`](notebooks/weights.csv). The single-tier queries (one per tier) are the same checks, one at a time.

### Metabolites (`ranked-pathway-metabolites`)

| Family | Tier (what is checked) | Weight | In the live query | Data today | Note |
|---|---|---|---|---|---|
| identity | `inchikey-exact` | 0.95 | yes | data | full InChIKey incl. stereo/charge equal; multiplied by a support factor 0.5+0.15*tools (1.0 from 3 tools) |
| identity | `inchikey-first-block` | 0.80 | yes | data | first block (connectivity) equal; same support factor |
| relatedness | `shared-chemical-class` | 0.20 | yes | no data yet | NPClassifier class shared with a pathway metabolite |
| relatedness | `similarity-link` | 0.40 | yes | no data yet | 0.40 x similarity score |
| relatedness | `structure-similarity` | 0.30 | yes | data (about 10 min) | same InChI formula layer (proxy) |
| relatedness | `idsm-similar-metabolites-in-pathway` | 0.50 | yes | data (pathway PC968 only) | IDSM/Sachem similarity to a substrate of a pathway; the component is a ChEBI IRI |
| reaction | `rhea-step-between-metabolites` | 0.70 | no | too slow for the endpoint (60 s proxy limit) | Rhea reaction connects two detected metabolites with a known enzyme |

### Reactions (`ranked-pathway-reactions`)

| Family | Tier (what is checked) | Weight | In the live query | Data today | Note |
|---|---|---|---|---|---|
| database identifiers | `rhea` | 0.60 | yes | data | Rhea identifier on the reaction |
| database identifiers | `ec` | 0.40 | yes | data | EC number on the reaction |
| enzyme | `uniprot` | 0.70 | yes | data | UniProt enzyme on the reaction |
| omics | `gene-catalyses-the-transformation` | 0.70 | yes | no data yet | co-expressed gene whose enzyme catalyses the conversion between two associated metabolites |
| omics | `rhea-step-between-metabolites` | 0.60 | no | too slow for the endpoint (60 s proxy limit) | Rhea reaction between two detected metabolites |
| omics | `idsm-similar-metabolite-with-coexpressed-catalysing-gene` | 0.50 | no | example only |  |
| prediction | `ml-predicted-reaction` | 0.30 | yes | no data yet | reaction predicted by a machine-learning model (ghost edge) |

### Genes (`ranked-pathway-genes`)

| Family | Tier (what is checked) | Weight | In the live query | Data today | Note |
|---|---|---|---|---|---|
| membership | `gene-in-plantmetwiki-pathway` | 0.90 | yes | data | gene listed in a pathway by Solyc or Araport identifier |
| membership | `bgc-both-in-pathway` | 0.70 | yes | data (sample graph) | gene and a gene of the same BGC are in the same pathway |
| membership | `bgc-partner-in-pathway` | 0.50 | yes | data (sample graph) | a gene of the same BGC is in the pathway |
| membership | `genes-in-same-bgc` | 0.30 | yes | data (sample graph) | two or more genes in one BGC (no pathway) |
| omics | `coexpressed-with-pathway-gene` | 0.50 | yes | data | same MEANtools functional cluster as a gene of the pathway |
| sequence | `ortholog-in-pathway-species` | 0.50 | yes | no data yet | ortholog of a pathway gene in another species |
| omics | `gene-and-metabolite-in-same-pathway` | 0.60 | yes | no data yet | gene associated with a detected metabolite annotated as a metabolite of the pathway |

## Where to look

| What | Where |
|---|---|
| The queries, with the family and weight of every branch in comments | `examples/MinimumInformationTiers/ranked-pathway-*.ttl` in [sparql-examples-pmw](https://github.com/pathway-lod/sparql-examples-pmw), or the site <https://pathway-lod.github.io/sparql-examples-pmw/> |
| The weights as a table | [`notebooks/weights.csv`](notebooks/weights.csv) |
| The results, figures and a check of the score | [`notebooks/05_ranked_components.ipynb`](notebooks/05_ranked_components.ipynb) |
| The result tables | `notebooks/results/ranked-pathway-*.csv` |
| Each tier on its own | the single-tier queries of the same folder, and the notebooks 01 to 04 |

## Caveats

- In the current annotation graph the stored InChIKey is the PlantMetWiki key that the pilot matched, so `inchikey-exact` is true for almost every pair; it becomes meaningful when the graph stores the tool's own InChIKey.
- `yes` in the column "In the live query" means that the branch is in the megaquery; "no data yet" means that the graphs hold no such data, so the branch adds nothing to a score.
- `rhea-step-between-metabolites` is not in the live queries (it exceeds the 60 s limit of the PlantMetWiki endpoint); `idsm-similar-metabolites-in-pathway` covers only the pathway PC968.
