# Pilot: transcriptomics evidence vs PlantMetWiki

Can expression data be turned into evidence attached to the genes and pathways of [PlantMetWiki](https://plantmetwiki.bioinformatics.nl), using the TX terms of the [specification](../../specification/SPECIFICATION.md#6-tx---transcriptomics-data) (TX-01 to TX-22)? This pilot tests the TX use case on tomato (issue [#18](https://github.com/pathway-lod/lod-pathways-community/issues/18)) with four kinds of claims:

| Claim | Statement (rdf:Statement) | Data |
|---|---|---|
| Differential expression | gene `lodp:differentiallyExpressedIn` contrast | E-MTAB-11876 (jasmonate vs none), three routes |
| Response profile | gene `lodp:expressionDeviatesIn` condition | MEANtools RPKM, 27 conditions |
| Gene co-expression | gene `RO:0002610` (correlated with) gene | MEANtools RPKM, ATTED-II `Sly-r.c6-0`, E-MTAB-11876 |
| Pathway co-expression | pathway `rdf:type` `lodp:CoexpressedGenePathway` | MEANtools RPKM, ATTED-II `Sly-r.c6-0` |

The input standard is the output of existing [nf-core](https://nf-co.re) pipelines: [nf-core/rnaseq](https://nf-co.re/rnaseq) 3.27.0 (count and TPM matrices) and [nf-core/differentialabundance](https://nf-co.re/differentialabundance) 2.0.0 (DESeq2 results). Datasets that did not go through them are reshaped into the same files by small adapters, so one converter reads them all.

## Inputs

| Input | Source |
|---|---|
| E-MTAB-11876: tomato cv. Moneymaker hairy roots, jasmonate 50 µM vs none, 24 h, 3 + 3 samples; raw counts, DESeq2 results, design | Expression Atlas, [E-MTAB-11876](https://www.ebi.ac.uk/gxa/experiments/E-MTAB-11876) (MD5 recorded on 2026-11-10); Gryffroy et al. 2023, *PNAS*, [10.1073/pnas.2210300120](https://doi.org/10.1073/pnas.2210300120) |
| E-MTAB-11876 reads (6 single-end runs) | ENA [PRJEB53936](https://www.ebi.ac.uk/ena/browser/view/PRJEB53936), for the nf-core route only (`nfcore/`) |
| Tomato leaves, 9 treatments × 12, 24, 48 h × 2 replicates, RPKM (`rnaseq.rpkm.csv`) | MEANtools case study, Zenodo [15697913](https://zenodo.org/records/15697913) (MD5-checked); reads BioProject PRJNA509154; Jeon et al. 2020, *Cell*, [10.1016/j.cell.2019.11.037](https://doi.org/10.1016/j.cell.2019.11.037) |
| Tomato expression matrix, 1,608 RNA-seq runs, log2 ComBat-corrected | ATTED-II v13.0 `Sly-r.c6-0` (MD5-checked; Zenodo [18679026](https://doi.org/10.5281/zenodo.18679026), CC BY 4.0); method: Obayashi et al. 2022, *Plant Cell Physiol*, [10.1093/pcp/pcac041](https://doi.org/10.1093/pcp/pcac041) |
| Solyc ↔ NCBI Gene ID (for the ATTED-II gene IDs) | Ensembl Plants release 63, SL4.0 `entrez.tsv.gz` (MD5 recorded on 2026-11-10) |
| PlantMetWiki tomato gene nodes with a Solyc locus (21), and their pathways | SPARQL snapshots `data/plantmetwiki_tomato_gene_nodes_2026-11-11.tsv`, `data/plantmetwiki_tomato_gene_pathways_2026-11-12.tsv` (queries in `to_turtle.py`) |

## Method

- **Genes.** A claim refers to the PlantMetWiki gene node itself (`plantcyc/G18C3-3`, `ncbigene/HQ293016`, ...). It is found by its Solyc locus (GPML property `Synonym_1`), with the `gene-` prefix and the version suffix of the source IDs removed. The locus is not written. ATTED-II genes are NCBI Gene IDs, which are mapped to Solyc one-to-one through Ensembl Plants 63. Unmapped genes stay in the matrix, because the mutual rank depends on the gene universe.
- **No anchor.** Claims carry no `lodp:anchoredInPathway`, `lodp:anchorTier` or `wp:organism`. Pathway and organism are reached from the gene node by query (`dcterms:isPartOf`, `wp:organism`). `lodp:TranscriptomicsClaim` is exempt from the anchor rule of `shapes/common.ttl`.
- **Claims as triples.** Each claim is an `rdf:Statement`, and its IRI is built from the triple (`lodp:claim_<subject>_<predicate>_<object>`). The same triple from several datasets or routes is therefore one claim, with one evidence node per run (`lodp:evidence_<claim>_<study>`, an IRI). The direction is on each evidence node (`lodp:direction`):
  - `RO:0002245` over- or `RO:0002246` under-expressed in, from the sign of the log2 fold change or the z-score;
  - `RO:0017003` positively or `RO:0017004` negatively correlated with, from the sign of r.

  Datasets that disagree therefore give conflicting evidence on one claim (a warning), not two opposite claims. For a gene pair, the two gene IRIs are in alphabetical order, as the relation is symmetric. The claim also refers (`sio:SIO_000628`) to the same nodes, which is redundant with `rdf:subject` and `rdf:object`. It is kept for review.
- **Differential expression.** DESeq2 through nf-core/differentialabundance (`--deseq2_shrink_lfc false`, so the Wald statistic is kept), on the counts of nf-core/rnaseq (Salmon) and on the Expression Atlas HTSeq counts. The published Atlas results are the third route; their `p-value` column is the adjusted p-value. Values on the evidence node:
  - log2FC, Wald statistic, lfcSE, baseMean, p-value, adjusted p-value (TX-08 to TX-12);
  - the contrast with its test and reference conditions (TX-17), replicate count (TX-18), plant structure as a PO term (TX-19), treatment (TX-20).

  The run is typed with `OBI:0200036` Benjamini-Hochberg (TX-13), uses a count-matrix node typed `STATO:0000064` (TX-03), and generates a `STATO:0000590` median-of-ratios node (TX-05).
- **Response profile.** The z-score of each condition mean across all condition means of a gene, on log2(RPKM + 1) with population SD (TX-06), with the mean in RPKM (TX-04). This is not a test against a control. Only the MEANtools set has enough conditions; E-MTAB-11876 has 2, where z is always ±0.71.
- **Gene co-expression.** Pearson r and its p-value, Spearman ρ, and the mutual rank over all genes with variance (TX-14, TX-16), for all pairs of PlantMetWiki genes in a matrix.
- **Pathway co-expression.** For each PlantMetWiki pathway with at least 3 genes in the matrix: the mean pairwise Pearson r, against 10,000 random gene sets of the same size (seed 20261112), with an empirical one-sided p-value.
- **Evidence classes.** `ECO:0006069` RNA-sequencing evidence. Co-expression uses `ECO:0007590` high throughput expression pattern evidence, plus the assay class (`ECO:0006069` RNA-seq or `ECO:0007301` microarray), which also covers TX-01.

## Setup and run

```
cd pilots/transcriptomics_overlap
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python run_pilot.py               # download (MD5-checked), reshape, tables -> results/
cd ../../shape_constraints
.venv/bin/python build_rdf.py transcriptomics   # results/ -> rdf/transcriptomics.ttl, validated
```

`run_pilot.py` runs `download_inputs.py` (about 100 MB), `adapters.py`, `export_differential.py` and the three table scripts. The inputs folder can be moved with the environment variable `TX_PILOT_DOWNLOADS` (default `data/downloads/`, ignored by git).

**nf-core route** (optional; Nextflow ≥ 25.10.4 and Docker; reads and genome about 6 GB):

```
bash pilots/transcriptomics_overlap/nfcore/download_inputs.sh
bash pilots/transcriptomics_overlap/nfcore/run_rnaseq.sh                      # Salmon only, about 14 min on 24 CPUs
bash pilots/transcriptomics_overlap/nfcore/run_differentialabundance.sh nfcore
bash pilots/transcriptomics_overlap/nfcore/run_differentialabundance.sh atlas   # Atlas counts (after adapters.py)
```

These are run from the repository root. `nfcore/workstation.config` sets 24 CPUs and 24 GB. Without these outputs, `run_pilot.py` keeps the committed results of the three nf-core-based sets.

## Outputs

`results/<kind>_<study>.tsv`: one table per claim set, each with its `<kind>_<study>.provenance.json` (input, MD5, parameters, versions):

| Table | Content |
|---|---|
| `differential_EMTAB11876_{nfcore_salmon,atlas_counts,atlas_published}.tsv` | DESeq2 results for the PlantMetWiki genes; run metadata and design in the provenance file |
| `expression_profile_meantools_rpkm.tsv` | gene × condition means and z-scores |
| `coexpression_{meantools_rpkm,atted_Sly_r_c6_0,EMTAB11876_nfcore_salmon}.tsv` | gene-pair correlations and mutual ranks |
| `pathway_coexpression_{meantools_rpkm,atted_Sly_r_c6_0}.tsv` | per pathway: mean r, random-set mean and SD, empirical p |

The RDF is written by `shape_constraints/build_rdf.py transcriptomics` (`to_turtle.py build()`) to `shape_constraints/rdf/transcriptomics.ttl`. The small sample with one claim of each type is in `examples/sample_transcriptomics_graph.ttl`.

## First results (2026-11-12)

| Claim set | Claims | Notes |
|---|---|---|
| Differential expression, E-MTAB-11876 | 19 (3 routes merged; 17 with the nf-core Salmon counts) | the Atlas results are reproduced by the rerun on the Atlas counts (r 0.9998); Salmon vs HTSeq r 0.96 |
| Response profile, MEANtools | 432 (16 genes × 27 conditions) | 37 with \|z\| ≥ 2 |
| Gene co-expression | 163 gene pairs (120 + 78 + 136 evidence nodes from the three datasets) | E-MTAB-11876 has only 6 samples: 89 pairs p ≥ 0.05, and 36 pairs conflict in sign with the other datasets |
| Pathway co-expression | 5 pathways, MEANtools and ATTED-II | all p = 0.0001, the smallest possible with 10,000 sets. α-tomatine biosynthesis: mean r 0.96 (MEANtools) and 0.80 (ATTED-II, where random sets give 0.29) |

Validation: 10,252 triples, 619 claims, 831 evidence nodes, **0 violations**, 604 warnings. The warnings are weak or incomplete support:
- 395 response profiles with |z| < 2;
- 89 co-expression pairs with p ≥ 0.05, and 44 negative correlations;
- 36 conflicting directions;
- 27 conditions with 2 replicates;
- 11 differential expression results that are not significant or have no adjusted p-value;
- 2 ATTED-II runs whose log2 ComBat input has no unit term.

TX terms: 18 of 22 requirements used. Not used:
- TX-01: the assay is stated by the ECO class;
- TX-21: covered by COM-04 `prov:used`;
- TX-22: only needed to find the gene node;
- TX-15: `INO:0000231` is a process, not a claim type.

## Pathway IRI

Pathway claims refer to the PlantCyc ID (`dcterms:source` of the PlantMetWiki pathway), because PlantMetWiki PC numbers change between builds (checked on the live endpoint on 2026-11-12):

| PlantCyc pathway | In `pilots/pairedomics_overlap/data/plantmetwiki_pc_pathways.csv` (2026-09-29) and the sample graph | Live | The old number now |
|---|---|---|---|
| `PWY18C3-3` α-tomatine biosynthesis | PC1159 | PC968 | coenzyme A biosynthesis I |
| `PWY-5992` thalianol and derivatives biosynthesis | PC800 | PC382 | glycerolipid acyl chain desaturation |
| `ASPARTATESYN-PWY` L-aspartate biosynthesis | PC992 | PC85 | selinene biosynthesis |

The reference check (`snapshots/pmw_pathway_ids.txt`) only tests that a PC number exists, so an old number still passes. `to_turtle.py --pathway-iri pmw` writes `pathways/PC<n>` instead.

## Next steps

- [ ] Agree on the claim pattern and the draft terms (#35): the claim classes as subtypes of a common class, `lodp:differentiallyExpressedIn`, `lodp:expressionDeviatesIn`, `lodp:direction`, `lodp:CoexpressedGenePathway`; whether `sio:SIO_000628` stays next to `rdf:subject`/`rdf:object`; the `common.ttl` exception for `lodp:TranscriptomicsClaim`, or a change of the anchor rule for all experimental claims.
- [ ] Update the TX requirement texts in `SPECIFICATION.md` (proposed on #35; the pilot already handles each point):
  - TX-17: a place for the time point of a condition (`EFO:0000724`?);
  - TX-06, TX-16: state the reference population of a z-score and the gene universe of a mutual rank;
  - TX-08: whether log2FC is shrunken (the pilot uses unshrunken);
  - TX-12: the Expression Atlas `p-value` column is the adjusted p-value;
  - TX-18: a replicate count, not a sample class;
  - TX-19: a property for plant structure (draft `lodp:plantStructure`, also MET-24; hairy root has no PO term);
  - TX-20: the control condition is typed as a treatment, and the substance has no place.
- [ ] *A. thaliana* (E-MTAB-7609 time course, ATTED-II `Ath-r.c7-0`, the heat-stress data of #30), where plantiSMASH BGCs link to PlantMetWiki through TAIR IDs (second checkbox of #18).
