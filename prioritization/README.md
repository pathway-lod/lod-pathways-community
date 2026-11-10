# Prioritisation: evidence tiers for the components of a pathway

A place to **discuss and decide** the scoring and prioritisation tiers of pathway components (reactions, enzymes, genes, metabolites). The tiers that are agreed here are **implemented as SPARQL queries** in the repository [`pathway-lod/sparql-examples-pmw`](https://github.com/pathway-lod/sparql-examples-pmw) (SIB SPARQL-examples format; some queries are federated with Rhea, UniProt and OrthoDB). This folder holds the discussion; that repository holds the queries.

**Browse the queries:** <https://pathway-lod.github.io/sparql-examples-pmw/examples/PlantMetWiki/> (one page per tier, with the query text, the endpoint it runs on and the `.rq` and `.ttl` files).

This is a draft for brainstorming. Nothing here is decided; use a pull request or an issue to propose a change.

## Why tiers

A claim that attaches to PlantMetWiki (the pipeline of the [main README](../README.md#the-pipeline)) should say how strong its attachment and its evidence are, so that candidates can be ranked. Tiers are ordered, named and defined by a query, so the ranking can be reproduced and challenged.

## Tiers that exist already

| Where | Tiers (strongest first) | Meaning |
|---|---|---|
| Anchor tier, COM-10 ([specification](../specification/SPECIFICATION.md)) | `curated`, `gene_direct`, `gene_locus`, `structure_match`, `gene_uniprot`, `gene_ec`, `mass_match` | How a claim was attached to a PlantMetWiki node |
| BGC to pathway ([`pilots/plantismash_overlap`](../pilots/plantismash_overlap/)) | direct, UniProt, EC | Same gene, same UniProt enzyme, or same EC number |
| Metabolite annotation ([`pilots/metabolomics_overlap`](../pilots/metabolomics_overlap/)) | `gnps_library`, `consensus_inchi`, `sirius`, `ms2query_exact`, `dreams`, `ms2query_analog` | Which tool or consensus produced the structure |
| Paired omics ([`pilots/pairedomics_overlap`](../pilots/pairedomics_overlap/)) | `gene_locus`, `gene_uniprot`, `gene_ec` (genes); `mass_match` (features) | How a gene or feature was linked to a pathway |

## Tiers implemented as queries (first draft)

The queries can be read and tried on the website: <https://pathway-lod.github.io/sparql-examples-pmw/examples/PlantMetWiki/>.

Evidence for the reactions of PlantMetWiki (release 17, queried 2026-11-10). The reactions are `gpml:Interaction` nodes; the queries are in [`sparql-examples-pmw/examples/PlantMetWiki`](https://github.com/pathway-lod/sparql-examples-pmw/tree/main/examples/PlantMetWiki).

| Tier | Name | Rule | Reactions that reach it (of 7,772) | Federates with |
|---|---|---|---|---|
| 1 | `ec` | the reaction has an EC number | 5,988 | |
| 2 | `rhea` | the reaction has a Rhea identifier that is an approved reaction in Rhea | 1,193 (with an identifier) | Rhea |
| 3 | `uniprot` | the reaction itself names a UniProt enzyme (reviewed or not) | 1,062 | UniProt |
| 4 | `enzyme_node` | the pathway has enzyme nodes with a UniProt ID (reviewed in Swiss-Prot or not) | per pathway | UniProt |
| 5 | `ortholog` | the enzyme's UniProt entry is in an OrthoDB orthologous group | sample of 300 enzymes | OrthoDB |

The tiers overlap and are **not yet an ordered scale**: a reaction can have an EC number but no Rhea identifier, or the other way round.

## Tiers for the pilot data (minimum information)

The tiers above grade the **components of a pathway** in PlantMetWiki. A second set grades **the results of our pilots** (annotations, associations, clusters) and is written as the minimum information a claim has to carry. It is in [`../minimum_information/`](../minimum_information/):

| Family | Tiers (summary) |
|---|---|
| Metabolite annotation | `annotation-matches-plantmetwiki` an annotated InChIKey matches a PlantMetWiki metabolite on the first block; `shared-chemical-class` two detected metabolites share a chemical class (NPClassifier); `similarity-link` linked by a similarity metric; `structure-similarity` linked by a structure similarity (InChI); `rhea-step-between-metabolites` and the difference between them is a Rhea reaction with a known PlantMetWiki enzyme |
| Paired omics | `gene-and-metabolite-in-same-pathway`; `ortholog-in-pathway-species` the gene is an ortholog of a gene in a species with the pathway; `gene-catalyses-the-transformation` the gene is predicted to catalyse exactly the transformation between the two metabolites; `ortholog-plus-ml-prediction` the ortholog case plus a machine-learning predicted transformation |
| Biosynthetic gene clusters | `coexpressed-in-same-cluster` co-expressed genes are in the same cluster; `coexpressed-in-cluster-one-in-pathway` and only one gene matches a pathway (a lead to extend it); `coexpressed-in-cluster-both-in-pathway` and both genes match |

## Questions to discuss

1. **Unit.** What do we rank: the reaction, the enzyme, the gene, the whole pathway, or a claim attached to one of them?
2. **Order.** Is the order EC < Rhea < UniProt < reviewed UniProt < ortholog right? Is a Rhea match stronger than an EC number? Is a reviewed (Swiss-Prot) enzyme stronger than an unreviewed one? Should the ortholog tier look at the species (an ortholog in a close plant counts more) and not only at the existence of a group?
3. **Scores.** Do we use ordered tiers only, or numeric scores (for example weights per tier summed per component)? Who sets the weights, and can they be benchmarked against the curated pathways of PlantMetWiki (the plan of the project)?
4. **Evidence that PlantMetWiki has and we do not use yet.** The PlantCyc evidence codes (see PMN-07, PMN-08 of the specification), literature references (`dcterms:references`), the enzymatic reaction counts, the `Orphan` flag (a reaction without enzyme).
5. **Evidence from the claims.** How do the evidence of a prediction (machine learning, co-expression, MS annotation level, BGC) and the tier of its anchor combine into one priority? Should the two be shown separately?
6. **Missing links.** Enzyme nodes list `Catalyzes` reaction IDs that do not match any reaction node, so a per-reaction enzyme tier is not possible yet (see the README of `sparql-examples-pmw`).
7. **Orthologs.** Which resource: OrthoDB (works from SPARQL now), OMA (its SPARQL endpoint answers differently and was not tested), PlantMetWiki's own orthology if it gets one.
8. **Predictions that use many modalities.** For the predictions of PlantMetBench (see [`pilots/unsupervised_overlap`](../pilots/unsupervised_overlap/)), should the tier also depend on how many curated nodes a model used?
9. **Terms.** Tier names are placeholders (`lodp:anchorTier` and others are local). Which should be proposed to an ontology?

## How to contribute

- Add or change rows of the tables or add questions in a pull request to this folder, or open an issue with the label `ontology-terms` for a term.
- Once a tier is agreed, add its SPARQL query to `sparql-examples-pmw` (one `.ttl` per query) and link it here.
- The queries can be tested with `run_examples.py` of that repository; queries over the evidence graphs of this repository (`examples/`, `shape_constraints/rdf/`) are explained in its README.
