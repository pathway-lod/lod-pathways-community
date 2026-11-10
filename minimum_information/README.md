# Minimum information standard: evidence tiers for the pilot data

Draft tiers that say **how much evidence a result of one of our pilots carries**, written as the minimum information that a claim has to contain to reach each tier. They are for discussion; nothing here is decided. The tiers for the components of PlantMetWiki pathways themselves (EC number, Rhea, UniProt, orthologs) are in [`../prioritization/`](../prioritization/) and implemented as queries in [`sparql-examples-pmw`](https://github.com/pathway-lod/sparql-examples-pmw).

How to read the tables:

- **Tiers have descriptive names** (not IDs, so that they are not mistaken for the requirement IDs of the specification, such as MET-08 or PO-12), grouped by the use cases of the [specification](../specification/SPECIFICATION.md) (metabolomics, paired omics, biosynthetic gene clusters). A tier is stronger than another **within the same family**; the families are not comparable with each other. Each tier is written as a SPARQL query in [`sparql-examples-pmw`](https://github.com/pathway-lod/sparql-examples-pmw) (site: <https://pathway-lod.github.io/sparql-examples-pmw/>), listed there by the seven cases of the project.
- **A tier is passed when its rule is true**, and a result can pass several. A tier that builds on another says so ("and").
- **Minimum information** is what the claim must carry so that the rule can be checked (see the evidence model in the [main README](../README.md#the-pipeline): claim, evidence node typed with ECO, run, and anchor to a PlantMetWiki node with an anchor tier, COM-10).
- **Status** says whether a pilot already computes it (**done**), whether the data exist but it is not computed (**data available**), or whether data or a method is missing (**needs**). I checked these against the pilots' READMEs; where I am not sure it is marked "to check".

Pilots: [`metabolomics_overlap`](../pilots/metabolomics_overlap/) (MET), [`pairedomics_overlap`](../pilots/pairedomics_overlap/) (PO), [`plantismash_overlap`](../pilots/plantismash_overlap/) (BGC), [`unsupervised_overlap`](../pilots/unsupervised_overlap/) (UN, planned).

## A. Metabolite annotation (MET)

A detected metabolite (an LC-MS feature) is annotated by one or more tools and linked to PlantMetWiki and to other detected metabolites.

| Tier | Rule | Minimum information | Status |
|---|---|---|---|
| **annotation-matches-plantmetwiki** | At least one annotation tool gives an InChIKey whose **first block (connectivity)** equals that of a PlantMetWiki metabolite | the feature, the tool and its version, the InChIKey of the annotation, the PlantMetWiki metabolite matched, the match level (`connectivity`) | done (metabolomics_overlap; tiers by tool and consensus) |
| **shared-chemical-class** | The feature is linked to **another detected metabolite** that shares a **chemical class** (an NPClassifier term) | both features, the class term and the tool and version that assigned it | needs: NPClassifier is a step of the consensus workflow (Wolters et al.) but is not used in the pilot (to check) |
| **similarity-link** | The feature is linked to another detected metabolite through a **similarity metric** | both features, the metric (for example the cosine of the MS/MS spectra or a molecular network edge), its value and the threshold | needs: a similarity measure between features (the annotation tools produce molecular networks in the source data; to check) |
| **structure-similarity** | As `similarity-link`, and the similarity is computed **on the structures (InChI)** of the two annotations | both InChIs, the fingerprint and the similarity (for example Tanimoto), its value and the threshold | needs: both features must have an annotation with a structure |
| **rhea-step-between-metabolites** | As `structure-similarity`, and the **difference between the two structures is exactly the change of a Rhea reaction**, and **PlantMetWiki lists an enzyme that catalyses that Rhea reaction** (or one of its directions) | the structural difference (for example a mass shift and a transformation), the Rhea reaction, the PlantMetWiki enzyme (UniProt ID) and the match to the reaction | needs: matching a structure difference to a reaction; the PlantMetWiki side exists (Rhea IDs on 1,193 reactions, enzymes on the nodes) |

`rhea-step-between-metabolites` is the one that can **expand a pathway**: two detected metabolites that differ by a known enzymatic step, with a known enzyme, suggest a pathway step that PlantMetWiki does not have.

## B. Paired omics: gene and metabolite associations (PO)

A gene is associated with a metabolite feature (for example in a functional cluster of MEANtools). The metabolite and the gene are each mapped to PlantMetWiki; PO-12 of the specification stores the anchored side and the tier of each.

| Tier | Rule | Minimum information | Status |
|---|---|---|---|
| **gene-and-metabolite-in-same-pathway** | The **metabolite and the gene match the same PlantMetWiki pathway** | the association (statistic and significance), the metabolite match (`annotation-matches-plantmetwiki`) and the gene match with its tier (`gene_locus`, `gene_uniprot` or `gene_ec`), the pathway | done (pairedomics_overlap) |
| **ortholog-in-pathway-species** | The metabolite matches a PlantMetWiki pathway and the gene is an **ortholog of a gene of a species that has that pathway** | as `gene-and-metabolite-in-same-pathway`, the ortholog group and its source (for example OrthoDB), the species of the ortholog | needs: orthology in the pilot (a query to OrthoDB exists in `sparql-examples-pmw`, tier 5, per enzyme) |
| **gene-catalyses-the-transformation** | The gene is predicted to **catalyse a transformation** (it matches a PlantMetWiki protein that may catalyse it) and that transformation is **exactly the one between the two associated metabolites** | the gene, its match to a PlantMetWiki protein (UniProt, EC or ortholog), the reaction, and the two metabolites as its substrate and product | needs: pairs of metabolites in the association and the reactions of PlantMetWiki as substrate and product pairs |
| **ortholog-plus-ml-prediction** | As `ortholog-in-pathway-species`, and the transformation also matches an **enzymatic transformation predicted by a machine-learning model** on the PlantMetWiki graph | as `ortholog-in-pathway-species`, the model, its version, the training and test split, and the score of the predicted link (UN-01 to UN-12) | needs: predictions of the models of PlantMetBench with the ID mapping to PlantMetWiki ([`unsupervised_overlap`](../pilots/unsupervised_overlap/)) |

## C. Biosynthetic gene clusters (BGC)

Two **co-expressed genes** (from the same transcriptomic data) are looked at together with the biosynthetic gene clusters of plantiSMASH.

| Tier | Rule | Minimum information | Status |
|---|---|---|---|
| **coexpressed-in-same-cluster** | The co-expressed genes are in the **same biosynthetic gene cluster** | the two genes, the co-expression statistic, the cluster, the tool and version (plantiSMASH) and the rule that detected the cluster | needs: the co-expression and the cluster data in one table (the BGC pilot links clusters to pathways, not to co-expression) |
| **coexpressed-in-cluster-one-in-pathway** | As `coexpressed-in-same-cluster`, and **only one of the two genes** matches a PlantMetWiki pathway | as `coexpressed-in-same-cluster`, and the match of that gene (tier) and the pathway | needs, as `coexpressed-in-same-cluster`. This is a **candidate for extending the pathway**: the second gene may be a new step |
| **coexpressed-in-cluster-both-in-pathway** | As `coexpressed-in-same-cluster`, and **both genes** match a PlantMetWiki pathway | as `coexpressed-in-same-cluster`, and the matches of both genes (tier) and the pathways; whether it is the same pathway | needs, as `coexpressed-in-same-cluster` |

Order by support: `coexpressed-in-cluster-both-in-pathway` is the strongest. `coexpressed-in-cluster-one-in-pathway` is a different kind of result (a lead for new knowledge), so it is listed with its own flag and not simply below `coexpressed-in-cluster-both-in-pathway`. The cluster-to-pathway links of the plantiSMASH pilot (`gene_direct`, `gene_uniprot`, `gene_ec`) are the "matches" in `coexpressed-in-cluster-one-in-pathway` and `coexpressed-in-cluster-both-in-pathway`.

## Open questions

1. **Order inside a family.** Is the order of the metabolomics tiers and of the paired-omics tiers right? For instance, is `gene-catalyses-the-transformation` (an exact transformation) stronger than `ortholog-in-pathway-species` (an ortholog in a species with the pathway)? Do `gene-catalyses-the-transformation` and `ortholog-in-pathway-species` combine?
2. **Similarity.** Which similarity metrics and thresholds count for `similarity-link` and `structure-similarity`, and should they be part of the tier or only recorded?
3. **`coexpressed-in-cluster-one-in-pathway` and `coexpressed-in-cluster-both-in-pathway`.** Should "one gene matches" be a lead flag and not a lower tier?
4. **Independence.** Tiers that build on others ("and") are cumulative. Which ones should be reported separately?
5. **Chance.** The pilots already show that some associations pass at chance level (for example the correlations with six tissues in the ipecac data). Should a tier name the null model or the significance it needs?
6. **Terms.** Which terms express these rules? `lodp:anchorTier`, `lodp:linkTier` and others are local placeholders (see the specification and the term table), and the tier names above need terms or values.
7. **Which tiers go to the queries.** Once a tier is agreed, its check can be written as a SPARQL query in `sparql-examples-pmw` (the tiers that depend on data outside PlantMetWiki, such as `similarity-link`, run on the evidence graph instead).
