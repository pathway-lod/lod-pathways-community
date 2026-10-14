# Specification: ontology terms for predicted-pathway data in the knowledge graph

**Status:** draft v0.1, started 2026-10-07.

This document collects, for each use case, what we need to say about the data and which ontology terms could say it. It is complemented by a gap analysis: where existing ontologies cover a need, where they only partly do, and where we need a new term.

- The requirements and the free text are written **here**, in Markdown.
- The terms live in [`ontology_terms.csv`](ontology_terms.csv), one row per requirement and candidate term. That file is the source of truth.
- The tables below are **generated from the CSV**. Do not edit them by hand: edit the CSV and run the script (see [How to edit](#how-to-edit)).


## Use cases and acronyms

The acronym is also the prefix of the requirement IDs (`PO-03` is the third requirement of the paired omics use case).

<!-- BEGIN:usecases -->
| Acronym | Use case | Stands for | Requirements | IDs |
|---|---|---|---|---|
| **PMN** | PlantCyc computationally inferred | Plant Metabolic Network (PlantCyc and the other Cyc databases) | 14 | PMN-01 to PMN-14 |
| **BGC** | plantiSMASH BGCs | biosynthetic gene cluster | 16 | BGC-01 to BGC-16 |
| **MET** | Metabolomics data | metabolomics | 18 | MET-01 to MET-18 |
| **PO** | Paired omics data | paired omics (transcriptomics and metabolomics of the same samples) | 12 | PO-01 to PO-12 |
| **UN** | Unsupervised predictions | unsupervised (machine-learning) predictions | 12 | UN-01 to UN-12 |
| **TX** | Transcriptomics data | transcriptomics | 22 | TX-01 to TX-22 |
| **COM** | Shared by all use cases | common to all use cases | 12 | COM-01 to COM-12 |
<!-- END:usecases -->

## How to edit

1. **Write a requirement** in the "Specifications" part of a use case (free text is fine), and give it the next free ID of its use case (`PMN-15`, `BGC-17`, ...).
2. **Add rows to the CSV**, one per candidate term: the same `req_id` and `requirement` on every row of a requirement, a `role` for the term, and your `decision`. A requirement with no candidate gets one `gap` row. Spreadsheet programs open the CSV directly.
3. **Run the script** from this folder:

   ```bash
   ../shape_constraints/.venv/bin/python check_terms.py --update --render
   ```

   It validates the CSV, fills in each term's label and IRI from the [Ontology Lookup Service](https://www.ebi.ac.uk/ols4/) (so labels are never typed by hand), and regenerates every table in this file and the dashboard [`index.html`](index.html). Without options it only validates, with no network.

**Colours.** GitHub Markdown cannot colour text, so the tables use coloured circles: 🟢 covered, 🟡 partial, 🔴 gap for the status; 🟠 open, 🔵 proposed, ✅ agreed, ⛔ rejected for the decision. The dashboard [`index.html`](index.html) shows the same with real colours, filters (use case, status, decision, owner, action, ontology) and a search box. A filtered view can be shared as a link, for example `index.html#decision=open&owner=Elena Del Pup`.

**Who decides what.** The `owner` column names the person who has to decide or answer. The block "Decisions needed" lists the open requirements, those with an owner first.

**Discussion and ownership on GitHub.** Each requirement can have GitHub issues (label `ontology-terms`, requirement ID at the start of the title). In the dashboard, selecting a requirement ID shows its issues live from GitHub, with state, number of comments and assignees, and two buttons: *Open a discussion* and *Suggest a term*. Both open an issue form that is already filled in with the requirement ([`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/)). GitHub users appear as owners (with @) when assigned to an issue; assigning needs write access to the repository, otherwise a maintainer assigns. When a suggestion is accepted, a maintainer puts the label `accept-term` on its issue; a workflow then adds the row to the CSV and opens a pull request. The label `decision:agreed` (or `decision:rejected`, `decision:proposed`, `decision:open`) records a decision the same way. The full description of the discussion app, the one-time setup and the workflows is in [`README.md`](README.md).

**Issues from the command line.** [`sync_issues.py`](sync_issues.py) opens one issue per requirement that needs a term request or a question (`action` = `request_term` or `ask`) and writes the issue link into `issue_url`. It is a dry run unless `--create` is given, and needs `gh auth login` first. `--labels-only` creates the labels that the forms and workflows use; this is needed once.

**Dashboard on the web.** [`index.html`](index.html) is published with GitHub Pages by a workflow (setting: Settings > Pages > Source: GitHub Actions; steps in [`README.md`](README.md)). The page is a single file with no dependencies; it reads the issues from the public GitHub API.

**Columns of the CSV**

| Column | Meaning |
|---|---|
| `req_id`, `use_case`, `requirement` | the requirement; the same on all rows of a requirement |
| `element_type` | what is needed: class, relation, property, evidence_type, identifier, method, value_set, other |
| `role` | `primary` (best fit), `alternative`, `stand_in` (used for lack of a better term), `local` (our own placeholder term), `gap` (no term at all) |
| `curie`, `label`, `ontology`, `iri` | the candidate term; label and IRI are filled by the script |
| `coverage` | how well this term covers the requirement: `exact`, `partial` or `none` |
| `decision` | `proposed` (suggested), `open` (to discuss), `agreed`, `rejected` |
| `action` | `reuse` an existing term, `request_term` from an ontology, `local_term` (define our own), `review` (needs a look), `ask` (ask the named `owner`), `none` |
| `used_in` | where the term is already used: `sample_graph`, `shapes`, `rdf` |
| `notes`, `source`, `owner`, `issue_url`, `verified` | free comments; where the requirement came from; who has to decide or answer (required for `ask`); a link to the discussion issue; the date the term was last checked |

**Status of a requirement** (generated): *covered* if a primary term fits it exactly; *partial* if only stand-ins or partial fits exist; *gap* if only local terms or no term exist. **Decision** is the least settled decision among its rows.

## Overview

<!-- BEGIN:overview -->
| Use case | Requirements | Covered | Partial | Gap | Open decisions | Local terms |
|---|---|---|---|---|---|---|
| PMN - PlantCyc computationally inferred | 14 | 10 | 1 | 3 | 5 | 1 |
| BGC - plantiSMASH BGCs | 16 | 8 | 2 | 6 | 3 | 7 |
| MET - Metabolomics data | 18 | 7 | 4 | 7 | 11 | 12 |
| PO - Paired omics data | 12 | 5 | 1 | 6 | 6 | 9 |
| UN - Unsupervised predictions | 12 | 3 | 3 | 6 | 12 | 2 |
| TX - Transcriptomics data | 22 | 12 | 6 | 4 | 13 | 6 |
| COM - Shared by all use cases | 12 | 6 | 1 | 5 | 4 | 5 |
| **All** | **106** | **51** | **18** | **37** | **54** | **38** |
<!-- END:overview -->

### Decisions needed

<!-- BEGIN:decisions -->
54 requirements wait for a decision; 8 have a named owner and are listed first, then the ones that need a term request or a question to someone.

| ID | Use case | Requirement | Owner | Action | Why it is open |
|---|---|---|---|---|---|
| **PMN-12** | PMN - PlantCyc computationally inferred | A reusable crosswalk between PlantCyc EV- codes and ECO | Elena Del Pup | request_term | No ECO or PlantCyc crosswalk found (searching the codes in the Ontology Lookup Service returns nothing). |
| **BGC-12** | BGC - plantiSMASH BGCs | The BGC overlaps a PlantMetWiki pathway | Elena Del Pup | review | Open design question: say this only at query time, or also record it? |
| **MET-04** | MET - Metabolomics data | A spectral library match supports the annotation | Elena Del Pup | review | Ask Adriano Rutz whether a term for a spectral library match as evidence already exists, or whether to request one. |
| **PMN-11** | PMN - PlantCyc computationally inferred | Prediction method and confidence of the extended PlantCyc predictions | Elena Del Pup | review | TODO(Elena): which method produces the predictions and what scores or confidence they carry. |
| **UN-04** | UN - Unsupervised predictions | Training procedure (supervised learning on known links) | Elena Del Pup | review | Link prediction is trained on known links, so the section title 'Unsupervised predictions' may need rewording (for example 'Machine-learning predictions'). |
| **UN-08** | UN - Unsupervised predictions | Ranking metrics of the benchmark (precision of the top k hits, for example P-H@50) | Elena Del Pup | review | No term found for precision of the top k hits. |
| **UN-10** | UN - Unsupervised predictions | Input modalities and edge types of the model (for example metabolite fingerprints, protein and DNA embeddings) | Elena Del Pup | review | No term found. |
| **UN-12** | UN - Unsupervised predictions | A predicted link can be told apart from a curated link in queries | Elena Del Pup | review | Open design question: the two end nodes are curated PlantMetWiki nodes but the link is a prediction, so the anchor tier 'curated' would mislead. |
| **PO-03** | PO - Paired omics data | Evidence: transcript and metabolite abundances are correlated | - | request_term, review | Less specific (not high-throughput). |
| **BGC-08** | BGC - plantiSMASH BGCs | Complete match with a MIBiG BGC (all genes similar) | - | review | A prediction is not the same thing as a curated cluster, so 'exact' is a stretch. |
| **BGC-09** | BGC - plantiSMASH BGCs | Partial match with a MIBiG BGC | - | review | The threshold between complete and partial is a choice (now: 100% of genes similar). |
| **COM-01** | COM - Shared by all use cases | A claim (prediction, association or annotation) points to the evidence that supports it | - | reuse, review | SEPIO models an assertion, its evidence lines and their strength (SEPIO:0000002, SEPIO:0000132). |
| **COM-06** | COM - Shared by all use cases | A run records the name of the software | - | local_term, review | SWO:0000001 is the class 'software'. |
| **COM-08** | COM - Shared by all use cases | A claim is attached to a PlantMetWiki pathway | - | local_term, review | 'refers to' is generic and does not say that the target is an existing PlantMetWiki node. |
| **COM-11** | COM - Shared by all use cases | A statement about an existing PlantMetWiki triple carries evidence (reification) | - | review | Used for PlantCyc evidence on node membership. |
| **MET-03** | MET - Metabolomics data | A single in-silico tool proposed the structure (SIRIUS, MS2Query, DreaMS) | - | reuse, review | Machine-learning methods. |
| **MET-05** | MET - Metabolomics data | Confidence level of the identification (MSI or Schymanski level) | - | review | MSI levels. |
| **MET-09** | MET - Metabolomics data | An MS feature is annotated as a PlantMetWiki metabolite | - | review, local_term | SKOS mapping relations are meant for concepts, not measurements. |
| **MET-10** | MET - Metabolomics data | A related compound (MS2Query analogue with a different mass) is not a detection | - | review | Analogue hits are currently left out of the generated RDF. |
| **MET-12** | MET - Metabolomics data | Tool-specific scores (SIRIUS confidence, MS2Query model score, DreaMS similarity, precursor m/z difference) | - | local_term, review | 'probability value': the scores are not all probabilities. |
| **MET-15** | MET - Metabolomics data | Retention time of a feature | - | review | Not in the generated RDF yet. |
| **MET-16** | MET - Metabolomics data | Ion mode (positive or negative) of a feature | - | local_term, review | 'positive scan'; MS:1000129 is 'negative scan'. |
| **MET-17** | MET - Metabolomics data | Adduct of the detected ion | - | review | Needed for mass-based matching (used in the MEANtools pilot, not in the RDF). |
| **PMN-07** | PMN - PlantCyc computationally inferred | Computational inference reviewed by a curator (EV-COMP-HINF) | - | review | Not present in the PlantMetWiki snapshot; confirm the mapping with the PlantCyc curators. |
| **PMN-08** | PMN - PlantCyc computationally inferred | Computational inference without human oversight (EV-COMP-AINF) | - | review | Not present in the PlantMetWiki snapshot. |
| **PMN-14** | PMN - PlantCyc computationally inferred | Which Cyc database a statement or prediction comes from | - | review | 'A related resource from which the described resource is derived'. |
| **PO-04** | PO - Paired omics data | Correlation coefficient of the pair | - | reuse, review | Spearman, if MEANtools is run with that method. |
| **PO-05** | PO - Paired omics data | Significance of the correlation | - | reuse, review | FWER-adjusted p-value, if multiple testing is corrected. |
| **PO-08** | PO - Paired omics data | Functional cluster (module) of genes and metabolites | - | local_term, review | 'Clustered expression profiles': genes only, no metabolites. |
| **PO-09** | PO - Paired omics data | Significance of the functional cluster | - | local_term, review | Generic p-value class. |
| **PO-10** | PO - Paired omics data | Method: expression correlation analysis and clustering | - | reuse, review | Weighted correlation network analysis. |
| **TX-01** | TX - Transcriptomics data | Expression was measured by RNA sequencing | - | reuse, review | Topic, not an assay. |
| **TX-02** | TX - Transcriptomics data | Evidence: the statement is based on RNA-seq expression data | - | reuse, review | Manual assertion. |
| **TX-05** | TX - Transcriptomics data | Normalisation method (library-size normalisation, TMM, variance-stabilising transformation) | - | review | Variance stabilizing transformation (as in DESeq2 'vst'). |
| **TX-06** | TX - Transcriptomics data | z-score of an expression value (standardised across samples or conditions) | - | reuse, review | 'standard score'. |
| **TX-08** | TX - Transcriptomics data | Fold change between two conditions (log2 fold change of a DESeq2 result) | - | review, local_term | 'fold change'; the log2 scale is not captured. |
| **TX-10** | TX - Transcriptomics data | Standard error of the log2 fold change (DESeq2 lfcSE) | - | review | 'standard error of estimate'. |
| **TX-11** | TX - Transcriptomics data | Mean of the normalised counts across samples (DESeq2 baseMean) | - | review | 'sample mean'; the counts it is computed from (normalised) have to be stated. |
| **TX-12** | TX - Transcriptomics data | Adjusted p-value of a differential expression result (DESeq2 padj) | - | review, local_term | Q-value. |
| **TX-14** | TX - Transcriptomics data | Correlation of the expression profiles of two genes (or of a gene and a metabolite) | - | reuse, review | Spearman. |
| **TX-15** | TX - Transcriptomics data | Two genes are co-expressed | - | review | 'co-expression' in the Interaction Network Ontology; check that it describes a statistical association, not a physical interaction. |
| **TX-17** | TX - Transcriptomics data | The comparison a differential result refers to (treatment against control, tissue, time point) | - | local_term, review | Names the two conditions and their direction, so that the sign of a fold change is defined. |
| **TX-18** | TX - Transcriptomics data | Replicates of a condition | - | reuse, review | 'biological replicate role'. |
| **TX-20** | TX - Transcriptomics data | Treatment or condition applied to the plants | - | reuse, review | Agronomy Ontology 'treatment'. |
| **UN-01** | UN - Unsupervised predictions | A predicted link between two existing PlantMetWiki nodes that is not in the curated graph (for example 'this enzyme catalyses this reaction') | - | review | 'A relationship between two or more entities derived by some informational analysis'. |
| **UN-02** | UN - Unsupervised predictions | Evidence: a machine-learning model predicted the link | - | review | Deep-learning neural network method evidence used in automatic assertion; fits a graph neural network. |
| **UN-03** | UN - Unsupervised predictions | Type of the model (graph neural network and its architecture) | - | review | One family of graph neural networks. |
| **UN-05** | UN - Unsupervised predictions | Version of the model code and the training run (hyperparameters, random seed) | - | review | Covers the version. |
| **UN-06** | UN - Unsupervised predictions | Prediction score of the model for a link | - | local_term, review | Number given by the model; whether it is a calibrated probability has to be stated per model. |
| **UN-07** | UN - Unsupervised predictions | Model performance on the benchmark (area under the ROC curve, area under the precision-recall curve) | - | review | Area under the receiver operator characteristic curve. |
| **UN-09** | UN - Unsupervised predictions | Data split strategy of the evaluation (random, organism-held-out, pathway-held-out) | - | review | No term found. |
| **MET-08** | MET - Metabolomics data | What the structure match compared (first InChIKey block, or the full key) | - | local_term | Values: connectivity, full. |
| **UN-11** | UN - Unsupervised predictions | The benchmark dataset the model was trained and evaluated on | - | local_term | Reuses the local property of MET-18; value is the dataset IRI (for example a Zenodo DOI). |
| **MET-01** | MET - Metabolomics data | The annotation comes from LC-MS/MS data | - | reuse | - |
<!-- END:decisions -->

Term IDs are written as OBO-style CURIEs (Compact Uniform Resource Identifier) (`ECO:0000314`). `lodp:` is a **placeholder** namespace for terms that no ontology has; it is defined in [`../shape_constraints/vocab/lodp.ttl`](../shape_constraints/vocab/lodp.ttl). The shapes that check data against these terms are in [`../shape_constraints/`](../shape_constraints/).

---

## 1. PMN - PlantCyc computationally inferred

### Summary of the goal

PlantCyc statements (for example "this enzyme node is part of this pathway") carry PlantCyc evidence codes (`EV-...`). Some codes are computational: by BioCyc's description, `EV-COMP-AINF` is "inferred computationally without human oversight" and `EV-COMP-HINF` is computational inference reviewed by a curator (definitions to be verified against the [BioCyc evidence ontology](http://bioinformatics.ai.sri.com/evidence-ontology/)). The goal is to make this distinction queryable in the knowledge graph by mapping the codes to the Evidence & Conclusion Ontology (ECO), and to give the **extended PlantCyc** computational predictions the same treatment.

[Evidence codes and their usage in PMN](https://plantcyc.org/evidence-codes-tutorials/) which uses the [Pathway Tools Evidence Ontology](https://brg.ai.sri.com/evidence-ontology/) available here [https://brg.ai.sri.com/evidence-ontology/downloads/evidence.html](https://brg.ai.sri.com/evidence-ontology/downloads/evidence.html). 

Superclasses: FRAMES

Subclasses: EV-AS, EV-COMP, EV-EXP, EV-IC

In PMN they use four types of these: 
A flask (experimental evidence) (example)
A book (a traceable author statement from the literature) (example)
A computer (computational evidence) (example)
A curator (inferred by curator) (example)

> The goal is to accurately represent the PMN evidence ontology terms (both the experimental and computational evidence) in the PlantMetWiki KG. 

### Available data for testing

- **PlantMetWiki evidence codes** (PlantCyc release in the node IRIs: `r17.0.0`): 1,113 citation values on nodes, of which 394 carry an evidence code. Only one computational code occurs: `EV-COMP-HINF-SEQ-ORTHOLOGY` (5 values). Snapshot: [`../shape_constraints/data/plantmetwiki_citations.csv`](../shape_constraints/data/plantmetwiki_citations.csv).
- **Generated RDF** with the proposed ECO mapping: [`../shape_constraints/rdf/plantcyc.ttl`](../shape_constraints/rdf/plantcyc.ttl) (364 nodes, 409 evidence entries).
- **Extended PlantCyc computational predictions:** available in the other Cyc repositories. e.g. SolCyc/TomatoCyc or AraCyc. 

### Specifications and fitting ontology terms

> **TODO(Elena):** write or paste the requirements here. Each one gets an ID and rows in the CSV. The draft requirements below come from what we have seen in the data.

<!-- BEGIN:terms:plantcyc -->
| ID | Requirement | Fitting terms | Stand-ins and alternatives | Local terms needed / gap | Status | Decision | Action | Owner |
|---|---|---|---|---|---|---|---|---|
| **PMN-01** | Experimental evidence: direct assay (EV-EXP-IDA and its purified / unpurified-protein variants) | `ECO:0000314` direct assay evidence used in manual assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-02** | Experimental evidence: expression pattern (EV-EXP-IEP) | `ECO:0000270` expression pattern evidence used in manual assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-03** | Experimental evidence, not further specified (EV-EXP) | `ECO:0000006` experimental evidence | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-04** | Author statement with traceable support (EV-EXP-TAS, EV-AS-TAS) | `ECO:0000304` author statement supported by traceable reference used in manual assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-05** | Inferred by a curator (EV-IC) | `ECO:0000305` curator inference used in manual assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-06** | Computational: sequence orthology, reviewed (EV-COMP-HINF-SEQ-ORTHOLOGY) | `ECO:0000266` sequence orthology evidence used in manual assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-07** | Computational inference reviewed by a curator (EV-COMP-HINF) | `ECO:0007668` computational evidence used in manual assertion | `ECO:0007631` computational inference used in manual assertion (alternative) | - | 🟢 covered | 🟠 open | review | - |
| **PMN-08** | Computational inference without human oversight (EV-COMP-AINF) | `ECO:0007669` computational evidence used in automatic assertion | `ECO:0000363` computational inference used in automatic assertion (alternative) | - | 🟢 covered | 🟠 open | review | - |
| **PMN-09** | The original PlantCyc evidence code is kept next to the ECO class | - | - | `lodp:originalEvidenceCode` original evidence code | 🔴 gap | 🔵 proposed | local_term | - |
| **PMN-10** | The publication that supports the evidence | `dcterms:references` References | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-11** | Prediction method and confidence of the extended PlantCyc predictions | - | - | TODO(Elena): which method produces the predictions and what scores or confidence they carry. | 🔴 gap | 🟠 open | review | Elena Del Pup |
| **PMN-12** | A reusable crosswalk between PlantCyc EV- codes and ECO | - | - | No ECO or PlantCyc crosswalk found (searching the codes in the Ontology Lookup Service returns nothing). The mapping in this table could be contributed. | 🔴 gap | 🟠 open | request_term | Elena Del Pup |
| **PMN-13** | Release (version) of the Cyc database a statement or prediction comes from (PlantCyc, MetaCyc, species-specific Cyc databases) | `SWO:0004000` has version | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PMN-14** | Which Cyc database a statement or prediction comes from | - | `dcterms:source` Source (stand-in) | - | 🟡 partial | 🟠 open | review | - |
<!-- END:terms:plantcyc -->

---

## 2. BGC - plantiSMASH BGCs

### Summary of the goal

plantiSMASH predicts biosynthetic gene clusters (BGCs) in plant genomes with rule-based detection. All BGCs in its database are **predictions**. The goal is to link them to PlantMetWiki genes and pathways, and to say how each BGC was predicted (rule, tool, version), how it compares with experimentally characterised clusters in MIBiG, and how much it overlaps with the pathway it is linked to.

> Is there a BGC, and for which pathway? How much overlap? which families? 

### Available data for testing

- **plantiSMASH 2.0 precalculated database:** <https://plantismash.bioinformatics.nl/precalc/v2/>. 30,426 BGCs were parsed from 430 genomes (the paper reports 30,423). Each BGC has its detection rule, core domains, genes and a KnownClusterBLAST match to MIBiG (percentage of genes similar).
- **PlantMetWiki BGC graphs** (`bgc-plantismash`, `bgc-mibig`) and the `map-to-rdf` conversion ([Zenodo 10.5281/zenodo.20640349](https://doi.org/10.5281/zenodo.20640349)): 65 plantiSMASH BGCs for *A. thaliana*, and 9 species-typed plus 41 untyped MIBiG BGCs.
- **Pilot results:** [`../pilots/plantismash_overlap/`](../pilots/plantismash_overlap/). Direct links for *A. thaliana*: 33 BGCs, 53 genes and 216 pathways; 57 BGCs with 448 links of the direct and UniProt tiers overall.
- **Generated RDF:** [`../shape_constraints/rdf/bgc.ttl`](../shape_constraints/rdf/bgc.ttl).

### Specifications and fitting ontology terms

>  there is a BGC, detected by rule X, plantiSMASH version X, complete or partial MIBiG match, X overlap with pathway nodes.

<!-- BEGIN:terms:bgc -->
| ID | Requirement | Fitting terms | Stand-ins and alternatives | Local terms needed / gap | Status | Decision | Action | Owner |
|---|---|---|---|---|---|---|---|---|
| **BGC-01** | There is a biosynthetic gene cluster | `SO:0002357` biosynthetic_gene_cluster | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **BGC-02** | A BGC has genes as parts | `BFO:0000051` has part | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **BGC-03** | The BGC was predicted computationally by sequence-model (pHMM) rules | `ECO:0000256` match to sequence model evidence used in automatic assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **BGC-04** | The prediction is based on the co-location of genes in the genome | `ECO:0007327` genomic context evidence used in automatic assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **BGC-05** | The BGC was detected by rule X (plantiSMASH rule, i.e. BGC type) | - | - | `lodp:detectionRule` detection rule | 🔴 gap | 🔵 proposed | local_term | - |
| **BGC-06** | The core enzyme domains that triggered the rule | - | - | `lodp:coreDomain` core domain | 🔴 gap | 🔵 proposed | local_term | - |
| **BGC-07** | plantiSMASH version and database release | `SWO:0004000` has version | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **BGC-08** | Complete match with a MIBiG BGC (all genes similar) | - | `skos:exactMatch` has exact match (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **BGC-09** | Partial match with a MIBiG BGC | - | `skos:closeMatch` has close match (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **BGC-10** | The MIBiG match is supported by gene similarity (KnownClusterBLAST) | `ECO:0000249` sequence similarity evidence used in automatic assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **BGC-11** | Percentage of the MIBiG cluster's genes that have a similar gene in the BGC | - | `GENEPIO:0100602` sequence identity percentage (alternative, rejected) | `lodp:percentGenesSimilar` percent genes similar | 🔴 gap | 🔵 proposed | local_term | - |
| **BGC-12** | The BGC overlaps a PlantMetWiki pathway | `RO:0002131` overlaps | - | - | 🟢 covered | 🟠 open | review | Elena Del Pup |
| **BGC-13** | How the overlap was established (same gene, same UniProt enzyme, or same EC number) | - | - | `lodp:linkTier` link tier | 🔴 gap | 🔵 proposed | local_term | - |
| **BGC-14** | Amount of overlap (shared genes, fraction of the pathway's genes or ECs) | - | - | `lodp:nSharedGenes` number of shared genes<br>`lodp:fractionPathwayGenes` fraction of pathway genes | 🔴 gap | 🔵 proposed | local_term | - |
| **BGC-15** | The BGC-pathway link is itself a computed claim with evidence | `ECO:0007679` combinatorial computational evidence used in automatic assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **BGC-16** | The genome assembly the BGC was predicted on | - | - | `lodp:genomeAssembly` genome assembly | 🔴 gap | 🔵 proposed | local_term | - |
<!-- END:terms:bgc -->

---

## 3. MET - Metabolomics data

### Summary of the goal

Untargeted LC-MS/MS features can be annotated with different tools (GNPS library search, SIRIUS, MS2Query, DreaMS). The goal is to say, for each feature, which PlantMetWiki metabolite it was annotated as, with which evidence tier, and (if available) the agreement between tools, so users can filter by how strong the annotation is.

> Questions the users could ask: where does this annotation come from? Which tool? which parameters? 

### Available data for testing

- **Brassicaceae LC-MS/MS dataset** (17 species, leaf and root): raw data in MetaboLights [MTBLS14270](https://www.ebi.ac.uk/metabolights/MTBLS14270) and MassIVE MSV000101479; annotated tables and intermediate results in Zenodo [10.5281/zenodo.19391098](https://doi.org/10.5281/zenodo.19391098); scripts in the [consensus annotation repository](https://github.com/capsicumbaccatum/Metabolic_fingerprinting_consensus_annotation).
- **Tools:** SIRIUS 6.1.0, MS2Query 1.0, DreaMS 1.0, GNPS library matches, and the consensus module.
- **Pilot results:** [`../pilots/metabolomics_overlap/`](../pilots/metabolomics_overlap/). 6,433 negative-mode and 7,683 positive-mode features of 14 species; 567 PlantMetWiki metabolites detected, 139 of them with strong evidence (library or consensus).
- **Generated RDF:** [`../shape_constraints/rdf/annotation.ttl`](../shape_constraints/rdf/annotation.ttl) (2,722 annotations).

### Specifications and fitting ontology terms

> 

<!-- BEGIN:terms:metabolomics -->
| ID | Requirement | Fitting terms | Stand-ins and alternatives | Local terms needed / gap | Status | Decision | Action | Owner |
|---|---|---|---|---|---|---|---|---|
| **MET-01** | The annotation comes from LC-MS/MS data | `ECO:0001580` liquid chromatography coupled with tandem mass spectrometry evidence | - | - | 🟢 covered | 🟠 open | reuse | - |
| **MET-02** | Several tools were combined automatically (consensus annotation) | `ECO:0007653` automatically integrated combinatorial computational evidence used in automatic assertion | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **MET-03** | A single in-silico tool proposed the structure (SIRIUS, MS2Query, DreaMS) | `ECO:0007669` computational evidence used in automatic assertion | `ECO:0008004` machine learning method evidence used in automatic assertion (alternative)<br>`ECO:0008006` deep learning neural network method evidence used in automatic assertion (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **MET-04** | A spectral library match supports the annotation | - | `MS:1001031` spectral library search (stand-in)<br>`EDAM:operation_3801` Spectral library search (alternative) | - | 🟡 partial | 🟠 open | review | Elena Del Pup |
| **MET-05** | Confidence level of the identification (MSI or Schymanski level) | `MS:1002896` compound identification confidence level | `MS:1002955` hr-ms compound identification confidence level (alternative)<br>`NCIT:C181006` Metabolite Identification Confidence Level (alternative) | - | 🟢 covered | 🟠 open | review | - |
| **MET-06** | The identified structure is given by its InChIKey | `CHEMINF:000059` InChIKey | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **MET-07** | The metabolite in PlantMetWiki is identified by an InChIKey IRI | - | - | - | 🔴 gap | ✅ agreed | - | - |
| **MET-08** | What the structure match compared (first InChIKey block, or the full key) | - | - | `lodp:matchLevel` match level | 🔴 gap | 🟠 open | local_term | - |
| **MET-09** | An MS feature is annotated as a PlantMetWiki metabolite | - | `skos:closeMatch` has close match (stand-in) | `lodp:MetaboliteAnnotation` metabolite annotation | 🟡 partial | 🟠 open | review, local_term | - |
| **MET-10** | A related compound (MS2Query analogue with a different mass) is not a detection | - | `skos:relatedMatch` has related match (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **MET-11** | Agreement between tools (full or partial, score, which tools agree) | - | - | `lodp:matchType` match type<br>`lodp:agreementScore` agreement score<br>`lodp:agreeingTool` agreeing tool | 🔴 gap | 🔵 proposed | local_term | - |
| **MET-12** | Tool-specific scores (SIRIUS confidence, MS2Query model score, DreaMS similarity, precursor m/z difference) | - | `SIO:000765` probability value (alternative) | `lodp:siriusConfidenceApprox` SIRIUS approximate confidence<br>`lodp:ms2queryModelScore` MS2Query model score<br>`lodp:dreamsSimilarity` DreaMS similarity | 🔴 gap | 🟠 open | local_term, review | - |
| **MET-13** | An untargeted MS feature as a resource (m/z, retention time, ion mode, dataset) | - | - | `lodp:MetaboliteFeature` metabolite feature | 🔴 gap | 🔵 proposed | local_term | - |
| **MET-14** | Identifier of the feature within its dataset | - | - | `lodp:featureId` feature identifier | 🔴 gap | 🔵 proposed | local_term | - |
| **MET-15** | Retention time of a feature | `MS:1000894` retention time | - | - | 🟢 covered | 🟠 open | review | - |
| **MET-16** | Ion mode (positive or negative) of a feature | `MS:1000130` positive scan | `MS:1000077` positive polarity acquisition (alternative) | `lodp:ionMode` ion mode | 🟡 partial | 🟠 open | local_term, review | - |
| **MET-17** | Adduct of the detected ion | `MS:1000353` adduct ion | `MS:1002807` positive mode adduct ion (alternative) | - | 🟢 covered | 🟠 open | review | - |
| **MET-18** | The study or dataset a feature comes from | - | - | `lodp:dataset` dataset | 🔴 gap | 🔵 proposed | local_term | - |
<!-- END:terms:metabolomics -->

---

## 4. PO - Paired omics data

### Summary of the goal

MEANtools correlates metabolite features with gene transcripts and groups genes and metabolites that co-vary into functional clusters. The goal is to state "gene G is associated with metabolite M because they are in the same functional cluster" together with its statistics, and to show where PlantMetWiki supports the association (a known pathway) or does not (a possibly new one).

> Potential other paired omics data beyond tomato 


### Available data for testing

- **MEANtools tomato case study** (fungal treatment): MEANtools output in Zenodo [15697913](https://zenodo.org/records/15697913) (`Jeon_fungal.sqlite`; the 2.6 GB bacterial output is not used yet); metabolomics in MetaboLights [MTBLS1039](https://www.ebi.ac.uk/metabolights/MTBLS1039) (positive mode); RNA-seq in BioProject PRJNA509154; code at <https://github.com/kumarsaurabh20/meantools> (release [10.5281/zenodo.15720912](https://doi.org/10.5281/zenodo.15720912)).
- **Pilot results:** [`../pilots/meantools_overlap/`](../pilots/meantools_overlap/). 21,817 gene-metabolite pairs in functional clusters (decay rate 10), 4,068 of them in clusters with p < 0.05.
- **Generated RDF:** [`../shape_constraints/rdf/association.ttl`](../shape_constraints/rdf/association.ttl) (1,293 associations).

### Specifications and fitting ontology terms

> Requirements: 

<!-- BEGIN:terms:paired_omics -->
| ID | Requirement | Fitting terms | Stand-ins and alternatives | Local terms needed / gap | Status | Decision | Action | Owner |
|---|---|---|---|---|---|---|---|---|
| **PO-01** | A gene and a metabolite feature are associated | `SIO:001257` chemical-gene association | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PO-02** | The association refers to its gene and its feature | `SIO:000628` refers to | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **PO-03** | Evidence: transcript and metabolite abundances are correlated | - | `ECO:0007590` high throughput expression pattern evidence used in automatic assertion (stand-in)<br>`ECO:0007298` expression pattern evidence used in automatic assertion (alternative)<br>`ECO:0007829` combinatorial computational and experimental evidence used in automatic assertion (alternative) | - | 🟡 partial | 🟠 open | request_term, review | - |
| **PO-04** | Correlation coefficient of the pair | `STATO:0000280` Pearson's correlation coefficient | `STATO:0000201` Spearman's rank correlation coefficient (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **PO-05** | Significance of the correlation | `OBI:0000175` p-value | `OBI:0001265` FWER adjusted p-value (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **PO-06** | Mutual rank of the gene-metabolite pair | - | - | `lodp:mutualRank` mutual rank | 🔴 gap | 🔵 proposed | local_term | - |
| **PO-07** | Edge weight derived from the mutual rank and the decay rate | - | - | `lodp:edgeWeight` edge weight<br>`lodp:decayRate` decay rate | 🔴 gap | 🔵 proposed | local_term | - |
| **PO-08** | Functional cluster (module) of genes and metabolites | - | `EDAM:data_3768` Clustered expression profiles (alternative) | `lodp:functionalCluster` functional cluster | 🔴 gap | 🟠 open | local_term, review | - |
| **PO-09** | Significance of the functional cluster | - | `OBI:0000175` p-value (alternative) | `lodp:clusterPValue` cluster p-value | 🔴 gap | 🟠 open | local_term, review | - |
| **PO-10** | Method: expression correlation analysis and clustering | `EDAM:operation_3463` Expression correlation analysis<br>`EDAM:operation_3432` Clustering | `EDAM:operation_3766` Weighted correlation network analysis (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **PO-11** | Identity of the tomato gene (Solyc locus) and its PlantMetWiki counterpart | - | - | `lodp:solycLocus` Solyc locus | 🔴 gap | 🔵 proposed | local_term | - |
| **PO-12** | Which side of the association is found in PlantMetWiki (gene, metabolite or both) | - | - | `lodp:anchoredSide` anchored side<br>`lodp:geneAnchorTier` gene anchor tier<br>`lodp:metaboliteAnchorTier` metabolite anchor tier | 🔴 gap | 🔵 proposed | local_term | - |
<!-- END:terms:paired_omics -->

---

## 5. UN - Unsupervised predictions

### Summary of the goal

> Goal is GNN predictions that come from a ML model using some of the modalities and edges. The examples are from PlantMetBench (internal work soon to put on arXiv)

### Available data for testing

- PlantMetBench predictions from GNN and other multimodal ML models 


<!-- BEGIN:terms:unsupervised -->
| ID | Requirement | Fitting terms | Stand-ins and alternatives | Local terms needed / gap | Status | Decision | Action | Owner |
|---|---|---|---|---|---|---|---|---|
| **UN-01** | A predicted link between two existing PlantMetWiki nodes that is not in the curated graph (for example 'this enzyme catalyses this reaction') | `SIO:000897` association | `rdf:Statement` Statement (stand-in) | - | 🟢 covered | 🟠 open | review | - |
| **UN-02** | Evidence: a machine-learning model predicted the link | `ECO:0008006` deep learning neural network method evidence used in automatic assertion | `ECO:0008004` machine learning method evidence used in automatic assertion (alternative) | - | 🟢 covered | 🟠 open | review | - |
| **UN-03** | Type of the model (graph neural network and its architecture) | - | `AIO:GraphConvolutionalNetwork` Graph Convolutional Network (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **UN-04** | Training procedure (supervised learning on known links) | `OBI:0002588` supervised machine learning | - | - | 🟡 partial | 🟠 open | review | Elena Del Pup |
| **UN-05** | Version of the model code and the training run (hyperparameters, random seed) | `SWO:0004000` has version | - | - | 🟡 partial | 🟠 open | review | - |
| **UN-06** | Prediction score of the model for a link | - | `SIO:000765` probability value (alternative) | `lodp:predictionScore` prediction score | 🔴 gap | 🟠 open | local_term, review | - |
| **UN-07** | Model performance on the benchmark (area under the ROC curve, area under the precision-recall curve) | `STATO:0000608` area under the receiver operator characteristic curve | `STATO:0000691` area under the precision-recall curve (alternative) | - | 🟢 covered | 🟠 open | review | - |
| **UN-08** | Ranking metrics of the benchmark (precision of the top k hits, for example P-H@50) | - | - | No term found for precision of the top k hits. TODO(Elena): list the metrics that PlantMetBench reports. | 🔴 gap | 🟠 open | review | Elena Del Pup |
| **UN-09** | Data split strategy of the evaluation (random, organism-held-out, pathway-held-out) | - | - | No term found. The three strategies are those of the public link-prediction dataset (Zenodo 10.5281/zenodo.21172660); confirm for PlantMetBench. | 🔴 gap | 🟠 open | review | - |
| **UN-10** | Input modalities and edge types of the model (for example metabolite fingerprints, protein and DNA embeddings) | - | - | No term found. The public dataset uses MAP4 fingerprints for metabolites, ESM-C embeddings for proteins and PlantCaduceus embeddings for gene products. TODO(Elena): list the modalities used. | 🔴 gap | 🟠 open | review | Elena Del Pup |
| **UN-11** | The benchmark dataset the model was trained and evaluated on | - | - | `lodp:dataset` dataset | 🔴 gap | 🟠 open | local_term | - |
| **UN-12** | A predicted link can be told apart from a curated link in queries | - | - | Open design question: the two end nodes are curated PlantMetWiki nodes but the link is a prediction, so the anchor tier 'curated' would mislead. A tier such as 'predicted' or a separate flag is needed. | 🔴 gap | 🟠 open | review | Elena Del Pup |
<!-- END:terms:unsupervised -->

---

## 6. TX - Transcriptomics data

### Summary of the goal

Expression measurements and the statistics derived from them serve as evidence for statements about genes, for example that a gene is induced by a treatment or that two genes are co-expressed. They include counts, normalised values with their unit (TPM, FPKM, RPKM), z-scores, differential expression results (for example the DESeq2 log2 fold change, test statistic and adjusted p-value) and association scores such as correlations and mutual ranks. The goal is to name each measurement, its unit and the method that produced it with ontology terms, so that this evidence can be attached to PlantMetWiki genes and pathways and compared across datasets.

> **TODO(Elena):** state the goal in your own words, and the questions that users should be able to ask (for example "which genes of this pathway are induced by the treatment").

### Available data for testing

- **Tomato RNA-seq expression matrix** (normalised; file `rnaseq.rpkm.csv`) from the MEANtools case study, Zenodo [15697913](https://zenodo.org/records/15697913); reads in BioProject PRJNA509154.
- **Correlations and mutual ranks** between genes and metabolite features: the MEANtools output `Jeon_fungal.sqlite`, analysed in [`../pilots/meantools_overlap/`](../pilots/meantools_overlap/).
- **PlantCyc expression evidence:** the code `EV-EXP-IEP` (inferred from expression pattern) on 53 PlantMetWiki nodes, mapped to `ECO:0000270` (PMN-02).

> **TODO(Elena):** list the datasets with DESeq2 results or z-scores that should be used for testing.

### Specifications and fitting ontology terms

> **TODO(Elena):** write or paste the requirements here. The drafts below cover the measurements and statistics named in the request: counts and normalised values, z-scores, DESeq2 results, correlations and mutual ranks, and the sample and condition descriptions that give them meaning.

<!-- BEGIN:terms:transcriptomics -->
| ID | Requirement | Fitting terms | Stand-ins and alternatives | Local terms needed / gap | Status | Decision | Action | Owner |
|---|---|---|---|---|---|---|---|---|
| **TX-01** | Expression was measured by RNA sequencing | `OBI:0001177` RNA sequencing assay | `EDAM:topic_3170` RNA-Seq (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **TX-02** | Evidence: the statement is based on RNA-seq expression data | `ECO:0006069` RNA-sequencing evidence used in automatic assertion | `ECO:0006068` RNA-sequencing evidence used in manual assertion (alternative)<br>`ECO:0000295` RNA-sequencing evidence (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **TX-03** | Raw read count of a gene in a sample | `STATO:0000064` sequence read count | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **TX-04** | Normalised expression value with its unit (TPM, FPKM or RPKM) | `STATO:0000589` TPM-transcript per million | `STATO:0000172` FPKM-fragments per kilobase of transcript per million fragments mapped (alternative)<br>`STATO:0000206` RPKM-reads per kilobase of transcript per million fragments mapped (alternative) | - | 🟢 covered | 🔵 proposed | reuse | - |
| **TX-05** | Normalisation method (library-size normalisation, TMM, variance-stabilising transformation) | - | `OBI:0200022` variance stabilizing transformation (stand-in)<br>`STATO:0000591` TMM-trimmed mean of M-values corrected count (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **TX-06** | z-score of an expression value (standardised across samples or conditions) | `STATO:0000104` z-score | `SIO:001245` standard score (alternative)<br>`NCIT:C68741` Z-Score (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **TX-07** | Method: differential gene expression analysis (for example DESeq2) | `EDAM:operation_3223` Differential gene expression profiling | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **TX-08** | Fold change between two conditions (log2 fold change of a DESeq2 result) | - | `STATO:0000169` fold change (stand-in) | `lodp:log2FoldChange` log2 fold change | 🟡 partial | 🟠 open | review, local_term | - |
| **TX-09** | Test statistic of the differential expression test (DESeq2 Wald statistic) | `STATO:0000584` Wald statistic | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **TX-10** | Standard error of the log2 fold change (DESeq2 lfcSE) | - | `STATO:0000562` standard error of estimate (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **TX-11** | Mean of the normalised counts across samples (DESeq2 baseMean) | - | `STATO:0000401` sample mean (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **TX-12** | Adjusted p-value of a differential expression result (DESeq2 padj) | - | `EDAM:data_3932` Q-value (stand-in)<br>`OBI:0001265` FWER adjusted p-value (alternative) | `lodp:adjustedPValue` adjusted p-value | 🟡 partial | 🟠 open | review, local_term | - |
| **TX-13** | Multiple-testing correction method (Benjamini-Hochberg, the DESeq2 default) | `OBI:0200036` Benjamini and Hochberg false discovery rate correction method | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **TX-14** | Correlation of the expression profiles of two genes (or of a gene and a metabolite) | `STATO:0000280` Pearson's correlation coefficient | `STATO:0000201` Spearman's rank correlation coefficient (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **TX-15** | Two genes are co-expressed | - | `INO:0000231` co-expression (stand-in) | - | 🟡 partial | 🟠 open | review | - |
| **TX-16** | Mutual rank of a pair based on correlation ranks (co-expression network, MEANtools) | - | - | `lodp:mutualRank` mutual rank | 🔴 gap | 🔵 proposed | local_term | - |
| **TX-17** | The comparison a differential result refers to (treatment against control, tissue, time point) | - | `EFO:0000727` treatment (alternative) | `lodp:contrast` contrast | 🔴 gap | 🟠 open | local_term, review | - |
| **TX-18** | Replicates of a condition | `EFO:0000683` replicate | `OBI:0000198` biological replicate role (alternative)<br>`SIO:001418` replicate (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **TX-19** | Plant structure (tissue or organ) the sample was taken from | `PO:0009011` plant structure | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **TX-20** | Treatment or condition applied to the plants | `EFO:0000727` treatment | `AGRO:00000322` treatment (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **TX-21** | The sequencing dataset the expression values come from (BioProject, SRA or GEO accession) | - | - | `lodp:dataset` dataset | 🔴 gap | 🔵 proposed | local_term | - |
| **TX-22** | Gene identifiers: expression tables and PlantMetWiki use different gene IDs | - | - | `lodp:solycLocus` Solyc locus | 🔴 gap | 🔵 proposed | local_term | - |
<!-- END:terms:transcriptomics -->

---

## 7. COM - Shared by all use cases

These requirements come back in every use case: evidence, provenance, how a claim is attached to PlantMetWiki, and how strong that attachment is.

<!-- BEGIN:terms:common -->
| ID | Requirement | Fitting terms | Stand-ins and alternatives | Local terms needed / gap | Status | Decision | Action | Owner |
|---|---|---|---|---|---|---|---|---|
| **COM-01** | A claim (prediction, association or annotation) points to the evidence that supports it | `SIO:000772` has evidence | `SEPIO:0000189` has_evidence (alternative) | - | 🟢 covered | 🟠 open | reuse, review | - |
| **COM-02** | The type of evidence is stated with a controlled class | `ECO:0000000` evidence | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **COM-03** | Evidence is attributed to the run (tool, pipeline or curation effort) that produced it | `prov:wasGeneratedBy` was generated by | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **COM-04** | A run lists the input data it used | `prov:used` used | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **COM-05** | A run records the version of the software or resource | `SWO:0004000` has version | - | - | 🟢 covered | 🔵 proposed | reuse | - |
| **COM-06** | A run records the name of the software | - | `SWO:0000001` software (alternative) | `lodp:software` software | 🔴 gap | 🟠 open | local_term, review | - |
| **COM-07** | Kinds of run are distinguished (prediction tool, linking, consensus, curation) | - | - | `lodp:Run` run | 🔴 gap | 🔵 proposed | local_term | - |
| **COM-08** | A claim is attached to a PlantMetWiki pathway | - | `SIO:000628` refers to (alternative) | `lodp:anchoredInPathway` anchored in pathway | 🔴 gap | 🟠 open | local_term, review | - |
| **COM-09** | A claim is attached to a PlantMetWiki metabolite | - | - | `lodp:anchoredToMetabolite` anchored to metabolite | 🔴 gap | 🔵 proposed | local_term | - |
| **COM-10** | How strong the attachment to PlantMetWiki is (anchor tier) | - | - | `lodp:anchorTier` anchor tier | 🔴 gap | 🔵 proposed | local_term | - |
| **COM-11** | A statement about an existing PlantMetWiki triple carries evidence (reification) | `rdf:Statement` Statement | - | - | 🟡 partial | 🟠 open | review | - |
| **COM-12** | The species a claim or prediction refers to | `wp:organism` organism | - | - | 🟢 covered | 🔵 proposed | reuse | - |
<!-- END:terms:common -->

---

## Gap analysis

Requirements that are not fully covered by an existing term, sorted from gap to partial.

<!-- BEGIN:gaps -->
| ID | Use case | Requirement | Status | Action | What is missing |
|---|---|---|---|---|---|
| **BGC-05** | BGC - plantiSMASH BGCs | The BGC was detected by rule X (plantiSMASH rule, i.e. BGC type) | 🔴 gap | local_term | 13 values are allowed (the 12 rule types of plantiSMASH 2.0 plus 'putative'); 12 occur in the database (no BGC has the 'phenylpropanoid' rule). No ontology found; a small SKOS scheme is proposed. The MIBiG biosynthetic classes are a candidate to review (not in the Ontology Lookup Service). |
| **BGC-06** | BGC - plantiSMASH BGCs | The core enzyme domains that triggered the rule | 🔴 gap | local_term | String with the domain name (e.g. SQHop_cyclase_N). Pfam / InterPro accessions are candidates to review (not in the Ontology Lookup Service). |
| **BGC-11** | BGC - plantiSMASH BGCs | Percentage of the MIBiG cluster's genes that have a similar gene in the BGC | 🔴 gap | local_term | Integer, 0-100. |
| **BGC-13** | BGC - plantiSMASH BGCs | How the overlap was established (same gene, same UniProt enzyme, or same EC number) | 🔴 gap | local_term | Values: gene_direct, gene_uniprot, gene_ec. |
| **BGC-14** | BGC - plantiSMASH BGCs | Amount of overlap (shared genes, fraction of the pathway's genes or ECs) | 🔴 gap | local_term | Count of genes the BGC shares with the pathway. |
| **BGC-16** | BGC - plantiSMASH BGCs | The genome assembly the BGC was predicted on | 🔴 gap | local_term | NCBI assembly accession, e.g. GCF_000001735.4. |
| **COM-06** | COM - Shared by all use cases | A run records the name of the software | 🔴 gap | local_term, review | A plain string. |
| **COM-07** | COM - Shared by all use cases | Kinds of run are distinguished (prediction tool, linking, consensus, curation) | 🔴 gap | local_term | Subclass of prov:Activity; subclasses per kind of run are defined in shape_constraints/vocab/lodp.ttl. |
| **COM-08** | COM - Shared by all use cases | A claim is attached to a PlantMetWiki pathway | 🔴 gap | local_term, review | Gives one query that works across all use cases. |
| **COM-09** | COM - Shared by all use cases | A claim is attached to a PlantMetWiki metabolite | 🔴 gap | local_term | The value is the identifiers.org InChIKey IRI that PlantMetWiki uses for metabolites. |
| **COM-10** | COM - Shared by all use cases | How strong the attachment to PlantMetWiki is (anchor tier) | 🔴 gap | local_term | Values, strongest first: curated, gene_direct, gene_locus, structure_match, gene_uniprot, gene_ec, mass_match. Weak tiers raise warnings in the shapes. |
| **MET-07** | MET - Metabolomics data | The metabolite in PlantMetWiki is identified by an InChIKey IRI | 🔴 gap | - | - |
| **MET-08** | MET - Metabolomics data | What the structure match compared (first InChIKey block, or the full key) | 🔴 gap | local_term | Values: connectivity, full. |
| **MET-11** | MET - Metabolomics data | Agreement between tools (full or partial, score, which tools agree) | 🔴 gap | local_term | Values: full (3 of 3 tools), partial (2 of 3). |
| **MET-12** | MET - Metabolomics data | Tool-specific scores (SIRIUS confidence, MS2Query model score, DreaMS similarity, precursor m/z difference) | 🔴 gap | local_term, review | Four annotations have a SIRIUS confidence of -Infinity (not computed); the value is left out of the RDF. |
| **MET-13** | MET - Metabolomics data | An untargeted MS feature as a resource (m/z, retention time, ion mode, dataset) | 🔴 gap | local_term | No ontology class for an untargeted feature was found. |
| **MET-14** | MET - Metabolomics data | Identifier of the feature within its dataset | 🔴 gap | local_term | - |
| **MET-18** | MET - Metabolomics data | The study or dataset a feature comes from | 🔴 gap | local_term | MetaboLights (MTBLS14270) and MassIVE (MSV000101479) IRIs. DCAT is a candidate to review (not in the Ontology Lookup Service). |
| **PMN-09** | PMN - PlantCyc computationally inferred | The original PlantCyc evidence code is kept next to the ECO class | 🔴 gap | local_term | Keeps the claim traceable to PlantCyc's own vocabulary. |
| **PMN-11** | PMN - PlantCyc computationally inferred | Prediction method and confidence of the extended PlantCyc predictions | 🔴 gap | review | TODO(Elena): which method produces the predictions and what scores or confidence they carry. |
| **PMN-12** | PMN - PlantCyc computationally inferred | A reusable crosswalk between PlantCyc EV- codes and ECO | 🔴 gap | request_term | No ECO or PlantCyc crosswalk found (searching the codes in the Ontology Lookup Service returns nothing). The mapping in this table could be contributed. |
| **PO-06** | PO - Paired omics data | Mutual rank of the gene-metabolite pair | 🔴 gap | local_term | No term found in STATO or OBI. |
| **PO-07** | PO - Paired omics data | Edge weight derived from the mutual rank and the decay rate | 🔴 gap | local_term | exp(-(MR-1)/DR), 0-1. |
| **PO-08** | PO - Paired omics data | Functional cluster (module) of genes and metabolites | 🔴 gap | local_term, review | Cluster id as an attribute of the association; a cluster node of its own is an open choice. |
| **PO-09** | PO - Paired omics data | Significance of the functional cluster | 🔴 gap | local_term, review | ClusterONE p-value; most clusters are not significant. |
| **PO-11** | PO - Paired omics data | Identity of the tomato gene (Solyc locus) and its PlantMetWiki counterpart | 🔴 gap | local_term | PlantMetWiki stores Solyc loci only as properties of pathway nodes (about 20 tomato loci). |
| **PO-12** | PO - Paired omics data | Which side of the association is found in PlantMetWiki (gene, metabolite or both) | 🔴 gap | local_term | Support from PlantMetWiki can be partial. |
| **TX-16** | TX - Transcriptomics data | Mutual rank of a pair based on correlation ranks (co-expression network, MEANtools) | 🔴 gap | local_term | No term found in STATO, OBI or SIO (searched 'mutual rank' twice). Same local term as PO-06. |
| **TX-17** | TX - Transcriptomics data | The comparison a differential result refers to (treatment against control, tissue, time point) | 🔴 gap | local_term, review | Names the two conditions and their direction, so that the sign of a fold change is defined. |
| **TX-21** | TX - Transcriptomics data | The sequencing dataset the expression values come from (BioProject, SRA or GEO accession) | 🔴 gap | local_term | Same local property as MET-18. The tomato data: BioProject PRJNA509154. |
| **TX-22** | TX - Transcriptomics data | Gene identifiers: expression tables and PlantMetWiki use different gene IDs | 🔴 gap | local_term | Same property as PO-11. MEANtools uses ITAG2 models (Solyc..), plantiSMASH and UniProt use RefSeq or Ensembl Plants IDs; an ID crosswalk is needed (BridgeDb). |
| **UN-06** | UN - Unsupervised predictions | Prediction score of the model for a link | 🔴 gap | local_term, review | Number given by the model; whether it is a calibrated probability has to be stated per model. |
| **UN-08** | UN - Unsupervised predictions | Ranking metrics of the benchmark (precision of the top k hits, for example P-H@50) | 🔴 gap | review | No term found for precision of the top k hits. TODO(Elena): list the metrics that PlantMetBench reports. |
| **UN-09** | UN - Unsupervised predictions | Data split strategy of the evaluation (random, organism-held-out, pathway-held-out) | 🔴 gap | review | No term found. The three strategies are those of the public link-prediction dataset (Zenodo 10.5281/zenodo.21172660); confirm for PlantMetBench. |
| **UN-10** | UN - Unsupervised predictions | Input modalities and edge types of the model (for example metabolite fingerprints, protein and DNA embeddings) | 🔴 gap | review | No term found. The public dataset uses MAP4 fingerprints for metabolites, ESM-C embeddings for proteins and PlantCaduceus embeddings for gene products. TODO(Elena): list the modalities used. |
| **UN-11** | UN - Unsupervised predictions | The benchmark dataset the model was trained and evaluated on | 🔴 gap | local_term | Reuses the local property of MET-18; value is the dataset IRI (for example a Zenodo DOI). |
| **UN-12** | UN - Unsupervised predictions | A predicted link can be told apart from a curated link in queries | 🔴 gap | review | Open design question: the two end nodes are curated PlantMetWiki nodes but the link is a prediction, so the anchor tier 'curated' would mislead. A tier such as 'predicted' or a separate flag is needed. |
| **BGC-08** | BGC - plantiSMASH BGCs | Complete match with a MIBiG BGC (all genes similar) | 🟡 partial | review | A prediction is not the same thing as a curated cluster, so 'exact' is a stretch. |
| **BGC-09** | BGC - plantiSMASH BGCs | Partial match with a MIBiG BGC | 🟡 partial | review | The threshold between complete and partial is a choice (now: 100% of genes similar). |
| **COM-11** | COM - Shared by all use cases | A statement about an existing PlantMetWiki triple carries evidence (reification) | 🟡 partial | review | - |
| **MET-04** | MET - Metabolomics data | A spectral library match supports the annotation | 🟡 partial | review | Ask Adriano Rutz whether a term for a spectral library match as evidence already exists, or whether to request one. MS:1001031 is a PSI-MS term for the method; searching ECO for 'spectral library' finds no class; the generated RDF uses ECO:0001580 only. |
| **MET-09** | MET - Metabolomics data | An MS feature is annotated as a PlantMetWiki metabolite | 🟡 partial | review, local_term | SKOS mapping relations are meant for concepts, not measurements. A dedicated 'annotated as' property would be cleaner. |
| **MET-10** | MET - Metabolomics data | A related compound (MS2Query analogue with a different mass) is not a detection | 🟡 partial | review | Analogue hits are currently left out of the generated RDF. |
| **MET-16** | MET - Metabolomics data | Ion mode (positive or negative) of a feature | 🟡 partial | local_term, review | Strings 'positive' and 'negative'. |
| **PMN-14** | PMN - PlantCyc computationally inferred | Which Cyc database a statement or prediction comes from | 🟡 partial | review | 'A related resource from which the described resource is derived'. Today the sample graph names the database in lodp:software ('PlantCyc'), which stretches that property. |
| **PO-03** | PO - Paired omics data | Evidence: transcript and metabolite abundances are correlated | 🟡 partial | request_term, review | Closest ECO class. ECO has no class for metabolite-transcript correlation; request one. |
| **TX-05** | TX - Transcriptomics data | Normalisation method (library-size normalisation, TMM, variance-stabilising transformation) | 🟡 partial | review | Variance stabilizing transformation (as in DESeq2 'vst'). |
| **TX-08** | TX - Transcriptomics data | Fold change between two conditions (log2 fold change of a DESeq2 result) | 🟡 partial | review, local_term | 'fold change'; the log2 scale is not captured. |
| **TX-10** | TX - Transcriptomics data | Standard error of the log2 fold change (DESeq2 lfcSE) | 🟡 partial | review | 'standard error of estimate'. |
| **TX-11** | TX - Transcriptomics data | Mean of the normalised counts across samples (DESeq2 baseMean) | 🟡 partial | review | 'sample mean'; the counts it is computed from (normalised) have to be stated. |
| **TX-12** | TX - Transcriptomics data | Adjusted p-value of a differential expression result (DESeq2 padj) | 🟡 partial | review, local_term | Q-value. The raw p-value is OBI:0000175 (PO-05). |
| **TX-15** | TX - Transcriptomics data | Two genes are co-expressed | 🟡 partial | review | 'co-expression' in the Interaction Network Ontology; check that it describes a statistical association, not a physical interaction. |
| **UN-03** | UN - Unsupervised predictions | Type of the model (graph neural network and its architecture) | 🟡 partial | review | One family of graph neural networks. A search of the Artificial Intelligence Ontology for 'graph neural network' returns only this class; confirm the architectures that were used. |
| **UN-04** | UN - Unsupervised predictions | Training procedure (supervised learning on known links) | 🟡 partial | review | - |
| **UN-05** | UN - Unsupervised predictions | Version of the model code and the training run (hyperparameters, random seed) | 🟡 partial | review | - |
<!-- END:gaps -->

### Which ontologies cover what

Number of requirements per ontology and use case (a requirement counts once per ontology, whatever the role of its term; rejected terms are left out).

<!-- BEGIN:ontologies -->
| Ontology | PMN - PlantCyc computationally inferred | BGC - plantiSMASH BGCs | MET - Metabolomics data | PO - Paired omics data | UN - Unsupervised predictions | TX - Transcriptomics data | COM - Shared by all use cases | All |
|---|---|---|---|---|---|---|---|---|
| [ECO](https://www.evidenceontology.org/): Evidence & Conclusion Ontology | 8 | 4 | 3 | 1 | 1 | 1 | 1 | 19 |
| [STATO](https://stato-ontology.org/): Statistical Methods Ontology | - | - | - | 1 | 1 | 9 | - | 11 |
| [SIO](https://github.com/MaastrichtU-IDS/semanticscience): Semanticscience Integrated Ontology | - | - | 1 | 2 | 2 | 2 | 2 | 9 |
| [OBI](https://obi-ontology.org/): Ontology for Biomedical Investigations | - | - | - | 2 | 1 | 5 | - | 8 |
| [EDAM](https://edamontology.org/): EDAM (data analysis and management) | - | - | 1 | 2 | - | 3 | - | 6 |
| [MS](https://www.psidev.info/): PSI-MS (mass spectrometry ontology) | - | - | 5 | - | - | - | - | 5 |
| [SWO](https://github.com/allysonlister/swo): Software Ontology | 1 | 1 | - | - | 1 | - | 2 | 5 |
| [SKOS](https://www.w3.org/TR/skos-reference/): SKOS (mapping relations) | - | 2 | 2 | - | - | - | - | 4 |
| [EFO](https://www.ebi.ac.uk/efo/): Experimental Factor Ontology | - | - | - | - | - | 3 | - | 3 |
| [DCTERMS](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): Dublin Core Terms | 2 | - | - | - | - | - | - | 2 |
| [NCIT](https://ncithesaurus.nci.nih.gov/): NCI Thesaurus | - | - | 1 | - | - | 1 | - | 2 |
| [PROV](https://www.w3.org/TR/prov-o/): PROV-O (provenance) | - | - | - | - | - | - | 2 | 2 |
| [RDF](https://www.w3.org/TR/rdf11-concepts/): RDF | - | - | - | - | 1 | - | 1 | 2 |
| [AGRO](https://github.com/AgriculturalSemantics/agro): Agronomy Ontology | - | - | - | - | - | 1 | - | 1 |
| [AIO](https://github.com/berkeleybop/artificial-intelligence-ontology): Artificial Intelligence Ontology | - | - | - | - | 1 | - | - | 1 |
| [BFO](https://basic-formal-ontology.org/): Basic Formal Ontology | - | 1 | - | - | - | - | - | 1 |
| [CHEMINF](https://github.com/semanticchemistry/semanticchemistry): Chemical Information Ontology | - | - | 1 | - | - | - | - | 1 |
| [INO](https://github.com/INO-ontology/ino): Interaction Network Ontology | - | - | - | - | - | 1 | - | 1 |
| [PO](https://planteome.org/): Plant Ontology | - | - | - | - | - | 1 | - | 1 |
| [RO](https://oborel.github.io/): Relation Ontology | - | 1 | - | - | - | - | - | 1 |
| [SEPIO](https://github.com/monarch-initiative/SEPIO-ontology): Scientific Evidence and Provenance Information Ontology | - | - | - | - | - | - | 1 | 1 |
| [SO](http://www.sequenceontology.org/): Sequence Ontology | - | 1 | - | - | - | - | - | 1 |
| [WP](https://vocabularies.wikipathways.org/wp): WikiPathways vocabulary | - | - | - | - | - | - | 1 | 1 |
| lodp: Local placeholder vocabulary (draft) | 1 | 6 | 8 | 6 | 2 | 6 | 5 | 34 |
<!-- END:ontologies -->

## Open questions for discussion

These come from the rows marked `open` and from the pilots.

1. **Evidence model:** keep the simple pattern (`SIO:000772` *has evidence* to an ECO-typed node), or adopt SEPIO's assertion and evidence-line model (`SEPIO:0000001`, `SEPIO:0000002`)? SEPIO is richer but heavier.
2. **Stand-ins:** several needs are met only by stand-ins (`skos:closeMatch` for "annotated as", `ECO:0007590` for metabolite-transcript correlation). Which of these should become requests for new terms?
3. **ECO term requests:** a class for metabolite-transcript correlation evidence, and for spectral library matches. The PlantCyc code crosswalk (PMN-12) could be offered at the same time.
4. **Local vocabulary:** how much of `lodp:` should become a permanent vocabulary (detection rules, overlap scores, MEANtools scores), and under which namespace?
5. **Identification confidence** (MET-05): record the MSI or Schymanski level or not?
6. **Scope of the unsupervised use case** (section 5).

## History of the terms table

The CSV is tracked in git, so every change to a term or decision is in the history. Record decisions in the `decision` column and link the discussion in `issue_url`.
