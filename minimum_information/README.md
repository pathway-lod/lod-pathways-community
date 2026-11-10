# Minimum information standard: evidence tiers for the pilot data

Draft tiers that say **how much evidence a result of one of our pilots carries**, written as the minimum information that a claim has to contain to reach each tier. They are for discussion; nothing here is decided. The tiers for the components of PlantMetWiki pathways themselves (EC number, Rhea, UniProt, orthologs) are in [`../prioritization/`](../prioritization/) and implemented as queries in [`sparql-examples-pmw`](https://github.com/pathway-lod/sparql-examples-pmw).

How to read the tables:

- **Tier IDs** are `MET-n`, `PO-n`, `BGC-n` for the use cases of the [specification](../specification/SPECIFICATION.md) (metabolomics, paired omics, biosynthetic gene clusters). A higher number means more supporting evidence **within the same family**; the families are not comparable with each other.
- **A tier is passed when its rule is true**, and a result can pass several. A tier that builds on another says so ("and").
- **Minimum information** is what the claim must carry so that the rule can be checked (see the evidence model in the [main README](../README.md#the-pipeline): claim, evidence node typed with ECO, run, and anchor to a PlantMetWiki node with an anchor tier, COM-10).
- **Status** says whether a pilot already computes it (**done**), whether the data exist but it is not computed (**data available**), or whether data or a method is missing (**needs**). I checked these against the pilots' READMEs; where I am not sure it is marked "to check".

Pilots: [`metabolomics_overlap`](../pilots/metabolomics_overlap/) (MET), [`pairedomics_overlap`](../pilots/pairedomics_overlap/) (PO), [`plantismash_overlap`](../pilots/plantismash_overlap/) (BGC), [`unsupervised_overlap`](../pilots/unsupervised_overlap/) (UN, planned).

## A. Metabolite annotation (MET)

A detected metabolite (an LC-MS feature) is annotated by one or more tools and linked to PlantMetWiki and to other detected metabolites.

| Tier | Rule | Minimum information | Status |
|---|---|---|---|
| **MET-1** | At least one annotation tool gives an InChIKey whose **first block (connectivity)** equals that of a PlantMetWiki metabolite | the feature, the tool and its version, the InChIKey of the annotation, the PlantMetWiki metabolite matched, the match level (`connectivity`) | done (metabolomics_overlap; tiers by tool and consensus) |
| **MET-2** | The feature is linked to **another detected metabolite** that shares a **chemical class** (an NPClassifier term) | both features, the class term and the tool and version that assigned it | needs: NPClassifier is a step of the consensus workflow (Wolters et al.) but is not used in the pilot (to check) |
| **MET-3** | The feature is linked to another detected metabolite through a **similarity metric** | both features, the metric (for example the cosine of the MS/MS spectra or a molecular network edge), its value and the threshold | needs: a similarity measure between features (the annotation tools produce molecular networks in the source data; to check) |
| **MET-4** | As MET-3, and the similarity is computed **on the structures (InChI)** of the two annotations | both InChIs, the fingerprint and the similarity (for example Tanimoto), its value and the threshold | needs: both features must have an annotation with a structure |
| **MET-5** | As MET-4, and the **difference between the two structures is exactly the change of a Rhea reaction**, and **PlantMetWiki lists an enzyme that catalyses that Rhea reaction** (or one of its directions) | the structural difference (for example a mass shift and a transformation), the Rhea reaction, the PlantMetWiki enzyme (UniProt ID) and the match to the reaction | needs: matching a structure difference to a reaction; the PlantMetWiki side exists (Rhea IDs on 1,193 reactions, enzymes on the nodes) |

MET-5 is the one that can **expand a pathway**: two detected metabolites that differ by a known enzymatic step, with a known enzyme, suggest a pathway step that PlantMetWiki does not have.

## B. Paired omics: gene and metabolite associations (PO)

A gene is associated with a metabolite feature (for example in a functional cluster of MEANtools). The metabolite and the gene are each mapped to PlantMetWiki; PO-12 of the specification stores the anchored side and the tier of each.

| Tier | Rule | Minimum information | Status |
|---|---|---|---|
| **PO-1** | The **metabolite and the gene match the same PlantMetWiki pathway** | the association (statistic and significance), the metabolite match (MET-1) and the gene match with its tier (`gene_locus`, `gene_uniprot` or `gene_ec`), the pathway | done (pairedomics_overlap) |
| **PO-2** | The metabolite matches a PlantMetWiki pathway and the gene is an **ortholog of a gene of a species that has that pathway** | as PO-1, the ortholog group and its source (for example OrthoDB), the species of the ortholog | needs: orthology in the pilot (a query to OrthoDB exists in `sparql-examples-pmw`, tier 5, per enzyme) |
| **PO-3** | The gene is predicted to **catalyse a transformation** (it matches a PlantMetWiki protein that may catalyse it) and that transformation is **exactly the one between the two associated metabolites** | the gene, its match to a PlantMetWiki protein (UniProt, EC or ortholog), the reaction, and the two metabolites as its substrate and product | needs: pairs of metabolites in the association and the reactions of PlantMetWiki as substrate and product pairs |
| **PO-4** | As PO-2, and the transformation also matches an **enzymatic transformation predicted by a machine-learning model** on the PlantMetWiki graph | as PO-2, the model, its version, the training and test split, and the score of the predicted link (UN-01 to UN-12) | needs: predictions of the models of PlantMetBench with the ID mapping to PlantMetWiki ([`unsupervised_overlap`](../pilots/unsupervised_overlap/)) |

## C. Biosynthetic gene clusters (BGC)

Two **co-expressed genes** (from the same transcriptomic data) are looked at together with the biosynthetic gene clusters of plantiSMASH.

| Tier | Rule | Minimum information | Status |
|---|---|---|---|
| **BGC-1** | The co-expressed genes are in the **same biosynthetic gene cluster** | the two genes, the co-expression statistic, the cluster, the tool and version (plantiSMASH) and the rule that detected the cluster | needs: the co-expression and the cluster data in one table (the BGC pilot links clusters to pathways, not to co-expression) |
| **BGC-2** | As BGC-1, and **only one of the two genes** matches a PlantMetWiki pathway | as BGC-1, and the match of that gene (tier) and the pathway | needs, as BGC-1. This is a **candidate for extending the pathway**: the second gene may be a new step |
| **BGC-3** | As BGC-1, and **both genes** match a PlantMetWiki pathway | as BGC-1, and the matches of both genes (tier) and the pathways; whether it is the same pathway | needs, as BGC-1 |

Order by support: BGC-3 is the strongest. BGC-2 is a different kind of result (a lead for new knowledge), so it is listed with its own flag and not simply below BGC-3. The cluster-to-pathway links of the plantiSMASH pilot (`gene_direct`, `gene_uniprot`, `gene_ec`) are the "matches" in BGC-2 and BGC-3.

## Open questions

1. **Order inside a family.** Is the order MET-1 to MET-5 and PO-1 to PO-4 right? For instance, is PO-3 (an exact transformation) stronger than PO-2 (an ortholog in a species with the pathway)? Do PO-3 and PO-2 combine?
2. **Similarity.** Which similarity metrics and thresholds count for MET-3 and MET-4, and should they be part of the tier or only recorded?
3. **BGC-2 and BGC-3.** Should "one gene matches" be a lead flag and not a lower tier?
4. **Independence.** Tiers that build on others ("and") are cumulative. Which ones should be reported separately?
5. **Chance.** The pilots already show that some associations pass at chance level (for example the correlations with six tissues in the ipecac data). Should a tier name the null model or the significance it needs?
6. **Terms.** Which terms express these rules? `lodp:anchorTier`, `lodp:linkTier` and others are local placeholders (see the specification and the term table), and the tier names above need terms or values.
7. **Which tiers go to the queries.** Once a tier is agreed, its check can be written as a SPARQL query in `sparql-examples-pmw` (the tiers that depend on data outside PlantMetWiki, such as MET-3, run on the evidence graph instead).
