# Prioritization framework for the ipecac alkaloid pathway and its enzymes (draft)

**Status.** A plan, not results. It adapts the [evidence tiers and score](../../minimum_information/scoring.md) to a case with known answers. All weights, cut-offs and thresholds below are drafts to be calibrated. Data and findings come from this pilot's [README](README.md).

**Why ipecac.** The THT example was chosen with the answer known, and the [orphan-feature analysis](../../minimum_information/orphan-features-usecase.md) showed that gene evidence alone was no better than chance across a whole dataset. Ipecac (Colinas et al., *Nat. Chem. Biol.*) has what the MEANtools data lack: **enzymes validated by heterologous expression** in two distant plants. That makes it a **positive control**: a prioritization that does not rank the validated genes high has a problem.

## 1. What is prioritized (three levels)

| Level | Question | Unit | Output |
|---|---|---|---|
| **A. Steps** | Which steps of PWY-7135 most need new evidence? | a conversion (8 in PlantMetWiki, plus the acid route that is not in it) | gap priority per step |
| **B. Enzymes** | For a step, which genes should be tested first? | a transcript or a cloned gene | ranked candidates per step, with score and the tiers that fired |
| **C. Nodes** | Which compounds or reactions should be added to PlantMetWiki? | a metabolite or a reaction (ghost edge) | list with evidence |

## 2. Inputs already in the pilot

| Input | File | Use |
|---|---|---|
| Pathway steps and their enzymes | `results/pathway_steps_PWY-7135.csv` | levels A and B (anchors) |
| Metabolite matches (6 of 12 in PlantMetWiki) | `results/metabolite_matches.csv` | anchors; compounds that need nodes |
| Co-expression with a bait (Ci 6 tissues, As 12) | `results/coexpression_selected_*.csv` | omics tier |
| Transcript-metabolite correlation across tissues | `results/gene_metabolite_top_*.csv` | omics tier |
| Enzyme family of transcripts (eggNOG text) | `results/gene_class_summary.csv` | family tier |
| Cloned genes vs PlantMetWiki enzymes | `results/sequence_identity_to_plantmetwiki.csv` | sequence tier; held-out positives |
| Experiments (75 comparisons, Figs 2 to 5) | `results/reaction_evidence.csv` | **held-out validation**, later an experimental tier |

## 3. Level A: priority of a step

A step is worth new evidence when it has little enzyme evidence, when both of its compounds are anchored, and when the paper shows that the conversion happens.

| Criterion | Values (draft) |
|---|---|
| Enzyme status in PlantMetWiki | none 1.0; PlantCyc monomer without sequence 0.8; UniProt enzyme of one species 0.4; two or more species 0.1 |
| Anchoring | both compounds in PlantMetWiki 1.0; one 0.5; none 0.0 |
| Conversion observed in the paper | yes 1.0; no 0.0 |

`priority = enzyme_gap × (0.5 + 0.25 × anchoring + 0.25 × observed)`. The first look at the eight steps (to be recomputed by script):

| # | Step | Enzyme status now | Evidence in the paper | Reading |
|---|---|---|---|---|
| 1 | secologanin → deacetylisoipecoside | monomer only | DAII 22-fold, DAI 20-fold after infiltration of dopamine and secologanin; **no gene expressed** | high; the enzyme may not exist (spontaneous condensation), so level B should allow "no enzyme needed" |
| 2 | DAII → 6-O-methyl-DAII | IpeOMT1 (*Carapichea*) | CiDOMT1 (95 % identical); AsDOMT1-7 (about 25 %) | low for *Carapichea*, **high for a second species** |
| 3 | → aglycon | IpeGLU1 | CiDGD (94 %), AsDGD1-2 (46 %) | low |
| 4 | aglycon → 6,7-O,O-dimethyl aglycon | IpeOMT3 | CiDPOMT (98 %), AsDPOMT1-2 (33 to 34 %) | low |
| 5 | → protoemetine | **none** | reductases CiDR1-2, AsDR1-2 give protoemetinol | **highest** |
| 6 | protoemetine → 7'-O-demethylcephaeline | **none** | none | **highest**, no experimental lead |
| 7 | → cephaeline | IpeOMT2, CiOMT | none for new genes | low |
| 8 | cephaeline → emetine | IpeOMT1, CiOMT | none for new genes | low |

The **acid route** (secologanic acid, DAIIA, DAIA and their methyl ethers) is not in PlantMetWiki: it is level C (new nodes and reactions), not a gap in an existing step.

## 4. Level B: score of a candidate for a step

Same model as the main framework: tiers grouped into **families**, the maximum weight per family, then a noisy-OR over families (`score = 1 − ∏(1 − w_f)`), reported as a range under explicit dependence assumptions.

| Family | Tier | Weight (draft) | Data |
|---|---|---|---|
| Membership | the enzyme is listed for this step in PlantMetWiki | 0.90 | anchors; these are the **known** enzymes, not candidates |
| Sequence | identity ≥ 60 % to a PlantMetWiki enzyme of this step | 0.70 | `sequence_identity_to_plantmetwiki.csv` |
| Sequence | 40 to 60 % | 0.50 | same |
| Family | eggNOG family fits the step chemistry (OMT for methylation, glycoside hydrolase for deglycosylation, reductase for reduction, decarboxylase, P450) | 0.30 | `gene_class_summary.csv` |
| Omics | co-expressed with the bait (Pearson ≥ 0.75, expressed) | 0.20 (*Carapichea*, 6 tissues) or 0.40 (*Alangium*, 12) | `coexpression_selected_*.csv` |
| Omics | correlated with the substrate or product of the step across tissues (r ≥ 0.75) | 0.20 (6 tissues) or 0.40 (12) | `gene_metabolite_top_*.csv` |

Rules carried over from the earlier analyses:

- **Specificity:** a candidate that reaches many steps through one tier counts less for each (`w / (1 + log2 k)`).
- **Weights follow the information in the data:** with six tissues, r ≥ 0.75 is reached by chance by about 4 % of transcripts, so the *Carapichea* omics tiers get a low weight; *Alangium* is far above chance.
- **Reasons for failure are recorded**, not only the score (no transcript for the cloned gene, identity too low, bait is not the described gene).
- **The experiments are not a tier input** (see section 5).

## 5. Validation: ipecac as a positive control

The paper's experiments give **held-out labels**: genes that make a product in *N. benthamiana*. They must not feed the score, or the test is circular.

| Test | Question | Metric |
|---|---|---|
| Rank of positives | Do the validated genes rank above other transcripts of their family for their step? | rank percentile, top-k hit rate |
| Null | Is that better than random transcripts of the same family and expression? | shuffled-annotation null with the same sizes, as in the orphan analysis |
| Species transfer | If the score is set on *Carapichea*, do the *Alangium* genes still rank? | leave-one-species-out |
| Tier ablation | Which tier carries the ranking? | score with each family removed |
| Negatives | Do co-expressed or correlated transcripts that were not tested rank above the positives? | not available: untested is not negative |

**The test that matters most is the species transfer.** The *Carapichea* genes are 94 to 98 % identical to PlantMetWiki's enzymes, so the sequence tier finds them trivially. The *Alangium* genes work experimentally at 17 to 46 % identity, so the sequence tier **cannot** reach them. This is the same failure as the tomato decarboxylase (about 20 %). The question is whether the family and omics tiers recover them, and with which weights.

## 6. Known obstacles

1. **The cloned genes and the transcripts are linked only through Extended Data Fig. 2 of the paper** (author's answer: the tables carry the sequence IDs; the gene names are listed in that figure). The figure is not in the pilot's files, so the join `gene name → NODE ID` is still to be made from it. Until then the omics tiers cannot be computed for the validated genes.
2. **The *Alangium* bait problem is resolved:** version 1 of the table was calculated with another transcript; version 2 of the Zenodo record has the correct table (bait `NODE_37865`, tyrosine dopa decarboxylase). The co-expression set shrank (1,034 transcripts after the expression cut-off, was 1,413) and no class is enriched any more.
3. **Six tissues in *Carapichea*** give almost no statistical power; the shortlist rests on expression and annotation.
4. **Pairing is by tissue, not by sample** (one RNA-seq plant, three metabolomics plants).
5. **eggNOG descriptions are family-level text**, not functions; the family tier can only filter.
6. **CiDE and CiIpS have no sequence in the file**, and accession numbers are "to be announced".
7. **Structures:** protoemetinol, 10-O-demethylprotoemetinol and 7-O-Me-DAIA were added from PubChem (CIDs given by the author) and are not in PlantMetWiki, so they are level C candidates (new nodes).

## 7. Outputs

- **`step_priority.csv`:** the step table of section 3, computed.
- **`enzyme_candidates.csv`:** per step, ranked candidates with `score`, `tiers`, family weights, range under dependence assumptions, and the failure reasons.
- **`validation.csv`:** ranks and metrics of the held-out positives with the null.
- **A figure:** the step gap table with the ranked candidates, and the validation ranks against the null.
- Later: the same candidates as evidence graphs in the shape of the minimum information model.

## 8. Decisions needed

1. Are **steps** the right unit, or should the pathway-level question (is this pathway present in the species) also be scored?
2. How should **"no enzyme needed"** (spontaneous condensation, step 1) be represented?
3. Should the **acid route** be scored as a separate pathway or as an extension of PWY-7135?
4. Which **sequence thresholds** (60 % and 40 % are drafts) and how to treat distant species, where function is conserved at low identity?
5. May the **experimental results** enter the final evidence graph as a tier after validation?

## 9. Next steps

1. Write `step_priority.py` for level A and check the table against the data.
2. Build the candidate table for the three steps with a family signal (methylation, deglycosylation, reduction) from the committed co-expression and correlation tables.
3. Run the held-out test with the sequence and family tiers; run the omics tiers once the transcript link exists.
4. Get Extended Data Fig. 2 (gene name ↔ transcript ID) from the paper or the author.
