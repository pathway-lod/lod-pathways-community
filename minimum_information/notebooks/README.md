# Notebooks: results of the minimum information tiers

One notebook per case. Each runs the SPARQL queries of the tiers (the files of [`sparql-examples-pmw`](https://github.com/pathway-lod/sparql-examples-pmw/tree/main/examples/MinimumInformationTiers)) on the evidence graphs of the pilots and **keeps the outputs**, so that the number of results of each tier can be read and discussed without running anything.

| Notebook | Case | Tiers |
|---|---|---|
| [`01_metabolomics.ipynb`](01_metabolomics.ipynb) | 5. Metabolomics: metabolite annotations | `annotation-matches-plantmetwiki`, `shared-chemical-class`, `similarity-link`, `structure-similarity`, `rhea-step-between-metabolites` |
| [`02_paired_omics.ipynb`](02_paired_omics.ipynb) | 6. Paired omics (with cases 5 and 7) | `gene-and-metabolite-in-same-pathway`, `gene-in-plantmetwiki-pathway`, `ortholog-in-pathway-species`, `gene-catalyses-the-transformation`, `ortholog-plus-ml-prediction` |
| [`05_ranked_components.ipynb`](05_ranked_components.ipynb) | All scopes: **ranked** reactions, metabolites and genes | the three megaqueries `ranked-pathway-metabolites`, `ranked-pathway-reactions`, `ranked-pathway-genes` (all evidence as optional branches, a noisy-OR score over families of tiers that are not independent), with figures in [`figures/`](figures/) and the draft weights in [`weights.csv`](weights.csv) |
| [`06_meantools_tht_example.ipynb`](06_meantools_tht_example.ipynb) | 6. Paired omics: **a worked biological example** (tomato THT genes and caffeoyltyramine, MEANtools, *C. fulvum*) | walks one association that the direct mapping misses through every tier (locus, UniProt, EC, orthology, sequence similarity, co-expression, InChIKey, Tanimoto, Rhea) and shows how to read the MEANtools statistics; nine figures in [`figures/`](figures/) (`tht_schema.png`, `tht_correlation_context.png`, `tht_feature_profiles.png`, `tht_sequence_identity.png`, `tht_fingerprints.png`, `tht_tier_ladder.png`, `tht_score.png`, `tht_funnel.png`, `tht_how_to_read.png`); summary in [`../meantools-use-case.md`](../meantools-use-case.md) |
| [`04_idsm_similarity.ipynb`](04_idsm_similarity.ipynb) | 5 (with 2, 4 and 6). Chemical similarity with IDSM | `idsm-similar-metabolites-in-pathway`, `metabolite-similar-to-pathway-metabolite-idsm`, `idsm-similar-metabolite-with-coexpressed-catalysing-gene` (these run on the public PlantMetWiki endpoint, with IDSM called by `SERVICE`) |
| [`03_gene_clusters.ipynb`](03_gene_clusters.ipynb) | 3 and 4. Gene clusters and co-expression (with case 6) | `genes-in-same-bgc`, `coexpressed-in-same-cluster`, `coexpressed-in-cluster-one-in-pathway`, `coexpressed-in-cluster-both-in-pathway` |

Each tier has a cell with the query's description, the run (status, number of rows, seconds, first rows) and a **For discussion** cell for comments. The results of each tier are also saved as CSV in [`results/`](results/), with [`results/summary.csv`](results/summary.csv) for all tiers.

## Ranked megaqueries (run on 2026-11-12, genes and the whole notebook re-run on 2026-11-18)

On the evidence graphs of the pilots: **3,688** metabolite-pathway pairs (492 metabolites in 674 pathways; 1,089 with a score of at least 0.9), **7,772** reactions (all PlantMetWiki reactions, scored by their Rhea, EC and UniProt evidence; 1,605 of them have none and score 0) and **266** gene-pathway pairs (62 genes in 213 pathways; the first run on 2026-11-12 had 12 rows, because the graphs had only the Solyc locus of each gene). Of the gene pairs, 111 reach the pathway only through an EC number of the gene (score 0.40), 110 through an ortholog of a pathway enzyme (0.50, 35 of them also through an EC number: 0.70) and 10 through the locus or the cluster tiers (5 at 0.90, among them the GAME17 gene of the alpha-tomatine pathway, and 5 genes only in a cluster at 0.30). The queries ran in about 11 minutes (metabolites, almost all of it the formula-layer branch), 2 s (reactions) and 2 minutes (genes). The metabolite query has four evidence branches that return data: annotation matches (exact or first block), the formula-layer proxy for structure similarity (934 pairs only by this tier, capped at 3,000 rows), and the IDSM similarity to the substrates of pathway PC968 (19). The Rhea step between metabolites is not in the live queries (asked through PlantMetWiki it exceeds the 60 s limit of the endpoint). The notebook shows the score distributions, the tiers passed, the pathways with most high-score or low-score components, a funnel per level of evidence, and how stable the ranking is when the weights change by 20% (the rank correlation stays above 0.99). **Caveat:** in the current annotation graph the exact-InChIKey tier is inflated, because the stored key is the PlantMetWiki key that the pilot matched (see the notebook).

## Results of the single-tier queries (run on 2026-11-11 and 2026-11-18, PlantMetWiki release r17.0.0_20260605-171052)

Every tier returns a **list of pathway components that reach it** (columns `component`, `componentType`, `pathway`, and the support as metadata); the number of rows is the number of such component-pathway pairs. On 2026-11-18 the notebooks 01 to 03 were run again, after the **gaps that made most tiers empty** were closed (see "What changed" at the top of notebooks 02 and 03):

- **Paired omics (02).** The gene tiers now use the three tiers of the pilot (locus, UniProt entry, EC number) instead of the Solyc locus alone, and the graphs have the links they need: `pilots/pairedomics_overlap/results/gene_annotation.ttl` (UniProt entry, EC numbers and OrthoDB orthologs of 315 of the 350 genes) and `feature_annotation.ttl` (the mass match of 43 features), both built by `build_gene_annotation.py`.
- **Gene clusters (03).** The 63 tomato plantiSMASH clusters are now in the graph (`pilots/plantismash_overlap/results/bgc_tomato.ttl`, built by `build_tomato_bgc.py`), and the co-expression tiers join on the gene IRI instead of comparing every cluster gene with every association gene, so they finish in seconds instead of timing out.
- **Metabolomics (01).** `structure-similarity` was rewritten with faster joins and now finishes (about 4 min, capped at 200 rows); `rhea-step-between-metabolites` still fails on the public endpoint (60 s limit).

| Tier | Case | Status | Seconds | Run on |
|---|---|---|---|---|
| `coexpressed-in-cluster-both-in-pathway` | 3 gene clusters | no rows | 5.5 | 2026-11-18 |
| `coexpressed-in-cluster-one-in-pathway` | 3 gene clusters | no rows | 4.2 | 2026-11-18 |
| `coexpressed-in-same-cluster` | 3 gene clusters | no rows | 2.2 | 2026-11-18 |
| `genes-in-same-bgc` | 3 gene clusters | rows (506 rows) | 0.0 | 2026-11-18 |
| `annotation-matches-plantmetwiki` | 5 metabolomics | rows (2781 rows) | 4.4 | 2026-11-18 |
| `rhea-step-between-metabolites` | 5 metabolomics | error (the public endpoint, 60 s limit) |  | 2026-11-18 |
| `shared-chemical-class` | 5 metabolomics | no rows | 0.0 | 2026-11-18 |
| `similarity-link` | 5 metabolomics | no rows | 0.0 | 2026-11-18 |
| `structure-similarity` | 5 metabolomics | rows (200 rows) | 241.0 | 2026-11-18 |
| `gene-and-metabolite-in-same-pathway` | 6 paired omics | no rows | 16.7 | 2026-11-18 |
| `gene-catalyses-the-transformation` | 6 paired omics | no rows | 36.1 | 2026-11-18 |
| `gene-in-plantmetwiki-pathway` | 6 paired omics | rows (146 rows) | 2.1 | 2026-11-18 |
| `ortholog-in-pathway-species` | 6 paired omics | no rows | 1.1 | 2026-11-18 |
| `ortholog-plus-ml-prediction` | 6 paired omics | no rows | 0.0 | 2026-11-18 |

The IDSM queries (they run on the public PlantMetWiki endpoint, with the example metabolites and gene given in the queries):

| Tier | Case | Status | Seconds | Run on |
|---|---|---|---|---|
| `idsm-similar-metabolite-with-coexpressed-catalysing-gene` | 5 metabolomics (IDSM) | rows (4 rows) | 2.9 | 2026-11-11 |
| `idsm-similar-metabolites-in-pathway` | 5 metabolomics (IDSM) | rows (19 rows) | 2.1 | 2026-11-11 |
| `metabolite-similar-to-pathway-metabolite-idsm` | 5 metabolomics (IDSM) | rows (7 rows) | 0.6 | 2026-11-11 |

How to read it:

- **rows**: the tier found components. `annotation-matches-plantmetwiki` found 2,781 metabolite-pathway pairs (the notebook keeps the first 2,000 in its CSV). `gene-in-plantmetwiki-pathway` found 146 gene-pathway pairs, almost all through the **EC number** (weak: see the tier column in the notebook); `genes-in-same-bgc` found the genes of the tomato and Arabidopsis clusters.
- **no rows, a computed result.** The query ran on the data it needs and found nothing, and the notebook says why: `gene-and-metabolite-in-same-pathway` (0 of the pairs share a pathway, as in the pilot: 0 of 721), `ortholog-in-pathway-species` (23 genes have an ortholog among the enzymes of PlantMetWiki pathways, but the annotated metabolite is never in the same pathway), `gene-catalyses-the-transformation` (no PlantMetWiki conversion between two matched metabolites is catalysed by the enzyme of the gene), and the three co-expression-and-cluster tiers (only 6 of the 350 genes of the associations are in a tomato cluster, and no cluster has two of them).
- **no rows, no data yet.** `shared-chemical-class` (no chemical classes in the annotation graph), `similarity-link` (no similarity between features) and `ortholog-plus-ml-prediction` (no PlantMetBench predictions in the graphs) cannot find anything until their data exist, so zero rows says nothing about the biology.
- **error**: `rhea-step-between-metabolites` calls PlantMetWiki without a restriction and the public endpoint stops it (60 s limit). It stays out of the live ranked queries.

## Run them again

```bash
cd minimum_information/notebooks
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m ipykernel install --user --name mi-notebooks   # a kernel for the notebooks
# then open the notebooks with the kernel mi-notebooks, or run one from the command line:
.venv/bin/python - <<'EOF'
import nbformat
from nbclient import NotebookClient
nb = nbformat.read("01_metabolomics.ipynb", as_version=4)
NotebookClient(nb, kernel_name="mi-notebooks", timeout=1800).execute()
nbformat.write(nb, "01_metabolomics.ipynb")
EOF
```

- Internet access is needed: the queries call PlantMetWiki, Rhea and UniProt on the live endpoints, so the numbers change with the PlantMetWiki release.
- The queries are read from a sibling checkout `../../sparql-examples-pmw` if it exists, otherwise from the published files on GitHub.
- `mi.py` runs each query in its own process with a time limit; `mi_worker.py` is the process. The evidence graphs are the Turtle files of `shape_constraints/rdf/` and `examples/`.
- The notebooks run one at a time or together; each tier writes its own file in `results/status/`, so parallel runs do not overwrite each other.
