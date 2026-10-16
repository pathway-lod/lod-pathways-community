# Pilot: MEANtools functional clusters (tomato) vs PlantMetWiki

How many of the gene–metabolite associations that MEANtools finds in the tomato case study can be mapped to [PlantMetWiki](https://plantmetwiki.bioinformatics.nl)? And do the gene and the metabolite meet in the same PlantCyc pathway?

The final goal is an **evidence model** for *"gene G is associated with metabolite M because they are in the same MEANtools functional cluster"*. This pilot tests the PO use case (*paired omics M-T correlations*) of the [specification](../../specification/SPECIFICATION.md#4-po---paired-omics-data); see also the [pipeline](../../README.md#the-pipeline).

## Inputs

| Input | Source |
|---|---|
| MEANtools output, fungal treatment (correlations, mutual ranks, ClusterONE functional clusters per decay rate) | Zenodo [15697913](https://zenodo.org/records/15697913), `Jeon_fungal.sqlite` (MD5-checked) |
| Exact m/z of the XCMS features | [sattely-lab/falcarindiol_pathway_metabolomics](https://github.com/sattely-lab/falcarindiol_pathway_metabolomics), pinned commit `7a7e0f6` |
| Tomato UniProt entries (Solyc locus, accession, EC) | UniProt REST, snapshot `data/uniprot_tomato.tsv.gz` (2026-09-29) |
| PlantMetWiki pathway ECs, enzyme UniProt ids, Solyc loci, metabolite InChIs | SPARQL snapshots `data/plantmetwiki_*.csv` (2026-09-29) |
| PlantMetWiki metabolites, pathway membership and classes | reused from [`../metabolomics_overlap`](../metabolomics_overlap/) |

Raw data behind the case study: MetaboLights MTBLS1039 (positive ion mode) and BioProject PRJNA509154.

## Method

- **Genes → PlantMetWiki pathways**, three tiers:
  1. `gene_locus`: the Solyc locus is itself a gene of the pathway. PlantMetWiki has ~20 SGN loci, e.g. the GAME and ASAT genes.
  2. `gene_uniprot`: the gene's UniProt protein is an enzyme of the pathway.
  3. `gene_ec`: the gene's EC number (from UniProt) catalyses a reaction of the pathway.
- **Metabolite features → PlantMetWiki pathways:** `mass_match` means the feature m/z matches a PlantMetWiki metabolite as [M+H]⁺, [M+Na]⁺, [M+NH4]⁺, [M+K]⁺ or [M+H−H₂O]⁺ within ±10 ppm. This is MS1 evidence only.
- **Associations:** every gene × metabolite pair within a functional cluster is checked for a shared PlantMetWiki pathway, and compared with a chance background.

## Setup and run

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # pinned versions
```

Open [`explore_results.ipynb`](explore_results.ipynb) with the `.venv` kernel and **Run All**. Or, from the command line:

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace explore_results.ipynb
```

- The Zenodo SQLite and the XCMS table are downloaded on the first run and checked against their MD5 checksums.
- `.venv/bin/python match_meantools.py` writes the CSVs and the RDF export.

## Outputs

- [`explore_results.ipynb`](explore_results.ipynb) holds the results with written interpretation.
- `results/cluster_pairs.csv`: every gene–metabolite pair in a functional cluster (DR 10), with correlation, mutual rank, cluster statistics and its PlantMetWiki mapping.
- `results/gene_pathway_map.csv` and `results/metabolite_pathway_map.csv`: how each gene and each feature reaches PlantMetWiki.
- `results/associations.ttl`: a **draft** RDF export of the associations from significant clusters. It does not conform to the [shape constraints](../../shape_constraints/) (for example, it has no anchor tier) and is superseded by `build_rdf.py association` there, which writes validated RDF.

## First results (2026-09-29, fungal treatment, decay rate 10)

- **Genes:** 311 of 3,406 clustered genes (9%) reach a PlantMetWiki pathway, almost all through EC numbers. Only about 20% of genes have an EC number at all.
- **Metabolites:** 43 of 137 clustered features (31%) match a PlantMetWiki pathway metabolite by mass.
- **Associations:** 0 of 721 fully mapped pairs share a PlantMetWiki pathway, where about 5 are expected by chance. The same holds at every decay rate.
  - Most fungus-induced metabolites (oxylipins, acetylenic fatty acids) have no PlantCyc pathway.
  - The metabolite identities rest on mass only.
- **Gene modules do reflect known pathways.** 26 clusters contain ≥ 2 different enzymes of the same PlantMetWiki pathway, against about 9 expected at random (0 of 100 seeded shuffles reach it).
- **Falcarindiol** (the pathway Jeon et al. discovered) can't be tested with this file:
  - Its XCMS features are not in the fungal MEANtools output.
  - PlantMetWiki has only *crepenynate biosynthesis* (the first step).
  - No tomato UniProt entry carries its acetylenase EC number.
- **Data issue:** MEANtools' `NPDB_annotations` table is not mass-consistent (4 of 149 [M+H]⁺ rows match), and the tolerance code has a bug (`mm_low` is computed with `checkP`). Worth reporting to the authors.

## Evidence model (draft, in `results/associations.ttl`)

| What | Term |
|---|---|
| association | `SIO:001257` chemical-gene association (`SIO:000628` refers to the gene and the feature) |
| evidence | `SIO:000772` has evidence → `ECO:0007590` high throughput expression pattern evidence used in automatic assertion |
| method | `EDAM:operation_3463` Expression correlation analysis + `EDAM:operation_3432` Clustering; `SWO:0004000` has version |
| scores | `STATO:0000280` Pearson's r, `OBI:0000175` p-value; mutual rank, edge weight, decay rate and cluster p-value as placeholder `lodp:` properties |
| PlantMetWiki support | `lodp:supportedByPlantMetWikiPathway` (optional) |

**Gap:** ECO has no term for metabolite–transcript correlation evidence. This is a candidate term request to ECO.

## Next steps

- [ ] Identify metabolites from MS/MS: run SIRIUS or a library search on MTBLS1039 and reuse the evidence tiers of the first pilot.
- [ ] Run on the bacterial-treatment output (2.6 GB), and check the falcarindiol features there.
- [ ] Improve gene function assignment: Pfam/InterPro → EC, or orthology to the Arabidopsis genes in PlantMetWiki.
- [ ] Match at reaction level: gene EC and metabolite in the *same* reaction.
- [ ] Request the ECO term; define the `lodp:` properties in a small vocabulary.
- [ ] Report the `NPDB_annotations` issue to the MEANtools authors.
