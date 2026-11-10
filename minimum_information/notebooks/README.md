# Notebooks: results of the minimum information tiers

One notebook per case. Each runs the SPARQL queries of the tiers (the files of [`sparql-examples-pmw`](https://github.com/pathway-lod/sparql-examples-pmw/tree/main/examples/MinimumInformationTiers)) on the evidence graphs of the pilots and **keeps the outputs**, so that the number of results of each tier can be read and discussed without running anything.

| Notebook | Case | Tiers |
|---|---|---|
| [`01_metabolomics.ipynb`](01_metabolomics.ipynb) | 5. Metabolomics: metabolite annotations | `annotation-matches-plantmetwiki`, `shared-chemical-class`, `similarity-link`, `structure-similarity`, `rhea-step-between-metabolites` |
| [`02_paired_omics.ipynb`](02_paired_omics.ipynb) | 6. Paired omics (with cases 5 and 7) | `gene-and-metabolite-in-same-pathway`, `gene-in-plantmetwiki-pathway`, `ortholog-in-pathway-species`, `gene-catalyses-the-transformation`, `ortholog-plus-ml-prediction` |
| [`03_gene_clusters.ipynb`](03_gene_clusters.ipynb) | 3 and 4. Gene clusters and co-expression (with case 6) | `coexpressed-in-same-cluster`, `coexpressed-in-cluster-one-in-pathway`, `coexpressed-in-cluster-both-in-pathway` |

Each tier has a cell with the query's description, the run (status, number of rows, seconds, first rows) and a **For discussion** cell for comments. The results of each tier are also saved as CSV in [`results/`](results/), with [`results/summary.csv`](results/summary.csv) for all tiers.

## Results of the first run (2026-11-10, PlantMetWiki release r17.0.0_20260605-171052)

| Tier | Case | Status | Seconds |
|---|---|---|---|
| `coexpressed-in-cluster-both-in-pathway` | 3 gene clusters | timeout |  |
| `coexpressed-in-cluster-one-in-pathway` | 3 gene clusters | no rows | 85.5 |
| `coexpressed-in-same-cluster` | 3 gene clusters | no rows | 2.0 |
| `annotation-matches-plantmetwiki` | 5 metabolomics | rows (2015 rows) | 4.0 |
| `rhea-step-between-metabolites` | 5 metabolomics | error: killed by the system (probably out of memory) |  |
| `shared-chemical-class` | 5 metabolomics | no rows | 0.0 |
| `similarity-link` | 5 metabolomics | no rows | 0.0 |
| `structure-similarity` | 5 metabolomics | timeout |  |
| `gene-and-metabolite-in-same-pathway` | 6 paired omics | no rows | 2.1 |
| `gene-catalyses-the-transformation` | 6 paired omics | no rows | 0.0 |
| `gene-in-plantmetwiki-pathway` | 6 paired omics | no rows | 1.6 |
| `ortholog-in-pathway-species` | 6 paired omics | no rows | 0.0 |
| `ortholog-plus-ml-prediction` | 6 paired omics | no rows | 0.0 |

How to read it:

- **rows**: the tier found hits. `annotation-matches-plantmetwiki`: 2,015 of the 2,430 features that have an annotation (83%) are annotated by at least one tool with an InChIKey whose first block matches a PlantMetWiki metabolite.
- **no rows**: the query ran and found nothing. For `gene-and-metabolite-in-same-pathway`, `gene-in-plantmetwiki-pathway` (no gene of the 1,293 MEANtools associations is listed by its Solyc locus in PlantMetWiki) and `coexpressed-in-cluster-one-in-pathway` this is a result of the data. For `shared-chemical-class`, `similarity-link`, `ortholog-in-pathway-species`, `gene-catalyses-the-transformation`, `ortholog-plus-ml-prediction` and `coexpressed-in-same-cluster` the data that the tier needs (chemical classes, similarities, orthologs, gene-to-UniProt links, model predictions, all genes of the clusters) are not in the graphs yet, so zero rows do not say anything about the biology.
- **timeout** and **error**: the query did not finish within its time limit (150 s), or the process was stopped by the system, probably for lack of memory. These queries (`structure-similarity`, `coexpressed-in-cluster-both-in-pathway`, `rhea-step-between-metabolites`) call PlantMetWiki several times without a restriction. They need a limit, a cache of the PlantMetWiki metabolites, or a subset of the features.

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
