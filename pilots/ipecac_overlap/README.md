# Pilot: ipecac alkaloid biosynthesis (Colinas et al.) vs PlantMetWiki

Which metabolites and which pathway steps of *Ipecac alkaloid biosynthesis in two evolutionarily distant plants* (Colinas, Morweiser, Dittberner et al., O'Connor lab) are already in [PlantMetWiki](https://plantmetwiki.bioinformatics.nl), and where could the data add evidence to a pathway?

This pilot belongs to the PO (paired omics) and MET use cases of the [specification](../../specification/SPECIFICATION.md). It has two parts: [part 1](#part-1-structures-pathway-and-co-expression) uses the Zenodo deposit (structures and co-expression), and [part 2](#part-2-the-paired-data-sequences-and-experiments) adds the supplementary tables of the paper (metabolite measurements per tissue, protein sequences and the heterologous expression experiments).

## Part 1: structures, pathway and co-expression

### Inputs

| Input | Source |
|---|---|
| SMILES of the 12 metabolites of Figure 2 | Zenodo [10.5281/zenodo.23661892](https://doi.org/10.5281/zenodo.23661892), `smiles.xlsx` |
| Expression and Pearson correlation of 137,713 transcripts of *Carapichea ipecacuanha* (Ci), 6 tissues | same record, `Ci_transcriptome_pearson.xlsx` |
| Expression and Pearson correlation of 178,877 transcripts of *Alangium salviifolium* (As), 12 tissues | same record, `As_transcriptome_pearson.xlsx` |
| PlantMetWiki metabolites, the pathway *emetine biosynthesis* (PlantCyc PWY-7135) and its enzymes | SPARQL endpoint, snapshots in `data/plantmetwiki_*.csv` (date in `data/SNAPSHOT_INFO.txt`) |
| Names and EC numbers of the enzymes of PWY-7135 | UniProt REST, snapshot `data/uniprot_pwy7135_enzymes.tsv` |

The three Zenodo files are downloaded on the first run and checked against the MD5 sums that Zenodo lists.

**What the transcript tables are.** The author's description (personal communication): the transcriptomes are de novo assemblies from short reads. The Pearson value is the correlation of a transcript's expression across the tissues with a *bait* gene; metabolite data were not used as bait and the transcriptome was not correlated with the metabolome. The author's cut-offs were Pearson ≥ 0.75 and an expression of at least 50 in the tissue of highest expression of the genes (leaf buds in *Alangium*, young leaf in *Carapichea*). Candidates were then filtered by their eggNOG-mapper description. The IDs are those of the assembly; there are no UniProt identifiers and no sequences in the deposit.

### Method

- **Metabolites.** The SMILES are converted to InChIKeys with RDKit. PlantMetWiki nodes with the same first block (connectivity) are found, and the match level is read from the key blocks: `full` (all three equal), `stereo (protonation differs)` (blocks 1 and 2 equal), `connectivity` (block 1 only), `none`. PlantMetWiki stores charged forms of amines (keys ending in `-O` or `-P`), while the paper's structures are neutral (`-N`), so a full-key comparison fails for alkaloids.
- **Pathway.** The conversions of PWY-7135, their enzymes (UniProt accession, name, EC) and which of the paper's metabolites are the substrates and products.
- **Genes.** Transcripts with Pearson ≥ 0.75 and expression ≥ 50 are selected. The reported Pearson values were reproduced from the expression columns (raw values, bait row as reference; largest difference 7e-16). The p-value is not in the deposit; it is derived from r and the number of tissues (two-sided t-test) and is only an indication.
- **Classes.** The eggNOG description is searched for enzyme-family words (methyltransferase, cytochrome P450, decarboxylase and so on) and each class is tested for enrichment among the selected transcripts against all annotated transcripts (Fisher's exact test, Benjamini-Hochberg over all 18 tests). These are family-level hypotheses, not annotations of a function.

### Results

#### Metabolites

`results/metabolite_matches.csv`. Of the 12 metabolites, 6 have a PlantMetWiki node with the same first InChIKey block.

| Metabolite | Match level | PlantMetWiki node | Pathway |
|---|---|---|---|
| Secologanin | full | secologanin | PWY-7135 emetine biosynthesis; also PWY-5290, PWY-5292 |
| DAII (deacetylisoipecoside) | stereo, protonation differs | deacetylisoipecoside | PWY-7135 |
| Cephaeline | stereo, protonation differs | cephaeline | PWY-7135 |
| Emetine | stereo, protonation differs | emetine | PWY-7135 |
| DAI | connectivity only | deacetylisoipecoside (the stereoisomer of DAII) | PWY-7135 |
| Protoemetine | connectivity only | protoemetine | PWY-7135 |
| Secologanic acid, DAIIA, DAIA, 6-O-Me-DAIIA, 6-O-Me-DAIA, ipecoside | none | not in PlantMetWiki | |

- All six matched metabolites are in the one pathway *emetine biosynthesis*. Secologanin is also in two other pathways.
- **Protoemetine differs in the stereo block.** The paper's key is `BBVFHYCHEWCGBH-ZQIUZPCESA-N`, PlantMetWiki's `BBVFHYCHEWCGBH-KVULBXGLSA-O`. This could be a different stereoisomer or a different stereo depiction in PlantCyc; it should be checked before the two are treated as the same compound.
- **Six metabolites have no node.** Five are carboxylic acids (secologanic acid and the four *-A* intermediates, for example 6-O-Me-DAIIA is PubChem 6-O-Me-deacetylisoipecosidic acid), and ipecoside is a known glycoside. PlantMetWiki's pathway has the corresponding methyl esters instead. These are candidates for new nodes if the pathway of the paper goes through the acids.

#### The pathway in PlantMetWiki

`results/pathway_steps_PWY-7135.csv`. PWY-7135 has 8 conversions.

| Step | Enzyme listed in PlantMetWiki |
|---|---|
| secologanin to deacetylisoipecoside | a PlantCyc monomer (MONOMER-17752) with no sequence |
| deacetylisoipecoside to 6-O-methyl-N-deacetylisoipecoside | D3KY98, IpeOMT1 (*C. ipecacuanha*) |
| 6-O-methyl-N-deacetylisoipecoside to its aglycon | B6ZKM3, IpeGLU1 (β-glucosidase, EC 3.2.1.220) |
| aglycon to 6,7-O,O-dimethyl aglycon | D3KYA0, IpeOMT3 |
| 6,7-O,O-dimethyl aglycon to protoemetine | none listed |
| protoemetine to 7'-O-demethylcephaeline | none listed |
| 7'-O-demethylcephaeline to cephaeline | D3KY99 (IpeOMT2) and E7FL15 (CiOMT) |
| cephaeline to emetine | D3KY98 (IpeOMT1) and E7FL15 (CiOMT) |

Five steps have a UniProt-linked enzyme, one has only a PlantCyc monomer, and two have no enzyme. Those three steps are where new gene evidence would add most. The enzymes already there are all from *C. ipecacuanha*, none from *Alangium*.

#### Genes

`results/coexpression_summary.csv`, `results/coexpression_selected_Ci.csv`, `results/coexpression_selected_As.csv`, `results/gene_class_summary.csv`.

| | Carapichea (Ci) | Alangium (As) |
|---|---|---|
| Transcripts, tissues | 137,713; 6 | 178,877; 12 |
| Bait (Pearson = 1) | `NODE_49441`, SAM-binding methyltransferase | `NODE_27464`, cytochrome P450 |
| Pearson ≥ 0.75 | 5,546 | 14,214 |
| expected by chance (normal null, rough) | about 5,900 | about 440 |
| Pearson ≥ 0.75 and expression ≥ 50 | 369 | 1,413 |
| p-value at r = 0.75 (derived) | 0.086 | 0.005 |

- **Carapichea: the correlation filter carries little information.** With 6 tissues, r ≥ 0.75 is reached by roughly 4% of unrelated profiles, about what is observed (5,546 of 136,736). Only the expression cut-off and the annotation make the 369 a usable shortlist.
- **Alangium: well above chance.** 14,214 transcripts against about 440 expected, with 12 tissues. Raw expression values are heavy-tailed, so the chance estimate is rough.
- **The *Alangium* bait is not a tyrosine decarboxylase in this table.** The author describes the bait as the ortholog of tyrosine decarboxylase, but the transcript with r = 1 is annotated as a cytochrome P450 (gene g9907, with two further isoforms at r ≥ 0.99). Transcripts annotated tyrosine (dopa) decarboxylase are co-expressed with it (for example `NODE_37865`, r = 0.90, expression 402 in leaf buds). Either the table was calculated with a different bait than described, or the P450 is one of the candidates; this should be confirmed with the author.
- **Classes.** After correction only one class is enriched: SAM-dependent methyltransferases among the *Carapichea* co-expressed transcripts (13, 3.1-fold, FDR 0.006), which is expected when the bait is itself a methyltransferase and its paralogs are co-expressed. In *Alangium*, reductases/dehydrogenases (FDR 0.06) and decarboxylases (FDR 0.21) are not significant. No strictosidine-synthase-like transcript is among the co-expressed ones in either species.

## Part 2: the paired data, sequences and experiments

The Supplementary Information of the paper (Nature Chemical Biology, article 41589_2025_1926) was added by the person who contributed the data: `MOESM3` (protein sequences of the cloned genes and of reference genes), `MOESM4` to `MOESM7` (Source Data of Figures 2 to 5) and `MOESM1` (the Supplementary Information PDF). They are not committed (the licence of the Source Data has not been checked); put them in `supplementaries/` to run `pair_ipecac.py`. Metabolomics used three individual plants and the RNA-seq one plant of the same age (Supplementary Fig. 1), so the pairing is by tissue and not by sample.

### Pairing metabolites and transcripts by tissue

`results/tissue_pairing.csv`. The six tissues of *C. ipecacuanha* (young, expanded and old leaves, stem, rhizome, roots) and the twelve of *A. salviifolium* (leaf buds, leaves 1 to 7, young and old stem, stem bark, roots) are the same in the metabolite and the transcriptome tables. The abbreviations of the transcriptome files are not explained in the deposit, so the assignment is a reading, and it is tested: the *Carapichea* bait gene (the methyltransferase with Pearson 1) correlates with secologanin, DAII, ipecoside, protoemetine and cephaeline across the tissues with r = 0.94 to 0.98 when `MR` is the rhizome and `LR` the roots, and with r between -0.12 and 0.47 when the two are swapped. The *Alangium* stem columns (`As_GS`, `As_WS`) cannot be tested this way; swapping them changes no correlation by more than 0.03.

### Genes correlated with the metabolites

`results/gene_metabolite_summary.csv`, `results/gene_metabolite_top_Ci.csv`, `results/gene_metabolite_top_As.csv`, `results/gene_metabolite_class_summary.csv`. Each transcript is correlated (Pearson, across the tissues) with the mean peak area of each metabolite, which the authors did not do. Transcripts with expression of at least 50 in some tissue are counted.

| | Carapichea (6 tissues) | Alangium (12 tissues) |
|---|---|---|
| Transcripts with expression ≥ 50 | 5,923 | 7,170 |
| r ≥ 0.75 with a metabolite, per metabolite | 269 to 772 (emetine: 2) | 17 to 868 |
| expected by chance, per metabolite (rough, normal null) | about 255 | about 18 |
| r ≥ 0.75 with at least one metabolite | 1,275 | 1,864 |

- **Carapichea: little more than chance.** With six tissues, a correlation of 0.75 is reached by chance in about 4% of transcripts, so 269 to 772 against about 255 is a weak signal for any single metabolite. The correlations are a source of candidates, not evidence.
- **Alangium: clearly above chance** for most metabolites (for example 868 for secologanic acid, 750 for protoemetine, 821 for cephaeline against about 18), with the exception of 6-O-Me-DAIIA (17).
- **Families among the correlated transcripts** (Fisher's exact test, Benjamini-Hochberg over all 18 tests): in *Carapichea*, glycoside hydrolases (20, 2.5-fold, FDR 0.002), reductases/dehydrogenases (53, 1.6-fold, FDR 0.007) and, weaker, SAM-dependent methyltransferases (22, 1.6-fold, FDR 0.07); in *Alangium*, cytochrome P450s (40, 3.2-fold, FDR < 0.0001) and decarboxylases (10, 3.0-fold, FDR 0.009). These are the enzyme families that the pathway chemistry predicts (methylation, deglycosylation, reduction, decarboxylation, oxidation), but the descriptions are family-level text.

### The cloned genes against the enzymes of PlantMetWiki

`results/sequence_identity_to_plantmetwiki.csv`. Each protein sequence of the paper's genes was aligned (BLOSUM62, free end gaps, identity over the shorter sequence) with the enzymes of its own family listed in PWY-7135.

| Gene of the paper | Enzyme in PlantMetWiki's emetine biosynthesis | Identity |
|---|---|---|
| CiDOMT1 | D3KY98, IpeOMT1 | 95.4% |
| CiDOMT2 | D3KY99, IpeOMT2 | 98.3% |
| CiDPOMT | D3KYA0, IpeOMT3 | 98.3% |
| CiDGD | B6ZKM3, IpeGLU1 | 93.6% |
| CiS6DGD | B6ZKM3, IpeGLU1 (a paralog) | 73.1% |
| *Alangium* genes (AsDOMT1-7, AsDPOMT1-2, AsDGD1-2, AsS6DGD) | the same enzymes | 17 to 46% |
| CiDR1-2, AsDR1-2 (reductases) | no reductase in the pathway | n/a |

- The *Carapichea* O-methyltransferases and glucosidases are 94 to 98% identical to the enzymes that PlantMetWiki already lists, which fits the author's remark that these sequences were published before (from plants of other sources). This links the new experiments to existing enzyme nodes.
- The *Alangium* genes are far from them (at most 46%): they are new enzymes for the same chemistry in a distant plant, not copies of the listed ones.
- The reductases have no counterpart in PWY-7135, whose steps from the aglycon to protoemetine have no enzyme listed; the reductases are candidates for those steps (the paper's products are protoemetinol and 10-O-demethylprotoemetinol, not protoemetine).
- The sequences of CiDE and CiIpS are not in the file, and the accession numbers are listed as "to be announced".

### What the experiments show

`results/reaction_evidence.csv` lists 75 comparisons of an experiment with its control (empty vector, 0 h or mock). A product counts as **higher** (or **lower**) when the mean differs at least three-fold and all three replicates of one group lie beyond all three of the other. A t-test with three plants and a heavy spread has too little power for this.

| Experiment | Result |
|---|---|
| Fig. 2g, dopamine and secologanin infiltrated into *N. benthamiana* leaves | DAII 22-fold and DAI 20-fold higher after 24 h. This is the first step of PWY-7135, for which PlantMetWiki lists only a monomer without sequence; no gene was expressed |
| Fig. 2h, dopamine and secologanic acid | DAIIA 30-fold and DAIA 28-fold higher after 24 h (compounds not in PlantMetWiki) |
| Fig. 2i, dopamine on *C. roseus* petals | DAII 328-fold and DAI 295-fold higher than mock |
| Fig. 3b, *Carapichea* genes | CiDE: DAIIA 8-fold; plus CiDOMT1: 6-O-Me-DAIIA 38-fold; plus CiS6DGD and CiDR1: 10-O-demethylprotoemetinol (about 1.1e4 against 0); plus CiDPOMT: protoemetinol (about 1.1e4 against 0) |
| Fig. 3c, *Alangium* genes | AsDOMT1 or AsDOMT2 alone: 6-O-Me-DAIIA about 34 to 38-fold; with AsS6DGD and AsDR1: 10-O-demethylprotoemetinol (2.2e4); with AsDPOMT1 or AsDPOMT2: protoemetinol (3.8e4 to 4.7e4) |
| Fig. 4c | CiIpS: ipecoside 3.7e4 against 0 |
| Fig. 4f | each of AsDOMT1-7 methylates DAIA, at the 6-O or 7-O position or both (AsDOMT3 only 6-O; AsDOMT5 mostly 7-O) |
| Fig. 5b, 5d | CiDGD removes ipecoside (0 against 1.4e4), CiS6DGD does not; AsDGD1 and AsDGD2 lower the methylated DAIA forms |

Of the compounds measured in these experiments, only DAII (stereo level) and DAI (connectivity) are in PlantMetWiki. DAIIA, DAIA, 6-O-Me-DAIIA, 6-O-Me-DAIA and ipecoside are not; protoemetinol, 10-O-demethylprotoemetinol and 7-O-Me-DAIA have no structure in the deposit, so they could not be matched.

## What this gives PlantMetWiki

- **Metabolite evidence for an existing pathway.** Six metabolites of the data set are in the pathway, each at a defined match level, with their concentrations in 6 or 12 tissues.
- **Experimental evidence for steps and for new steps.** The formation of DAII and DAI from secologanin and dopamine (the step without an enzyme), and, with expressed genes, the methylation of DAIIA by CiDOMT1, the deglycosylation by CiDGD and the formation of ipecoside by CiIpS. The acid route (DAIIA, DAIA and their methyl ethers) is not in PlantMetWiki at all.
- **A link from the new experiments to existing enzyme nodes**, through 94 to 98% identical sequences, and new enzymes from *Alangium* with no counterpart.
- **Missing nodes.** Six structures with a SMILES (mostly the acids) and three more compounds (protoemetinol, 10-O-demethylprotoemetinol, 7-O-Me-DAIA) that need structures.
- **Candidates for the steps without a gene**: the reductases CiDR1-2 and AsDR1-2, and the co-expressed and correlated transcripts (families, not functions).
- **A finding for the specification:** a match level between `connectivity` and `full` is needed ("stereo, protonation differs"), because PlantMetWiki stores charged forms of amines. The current values of MET-08 are `connectivity` and `full`.

## What is missing

1. **The link between the cloned genes and the transcripts.** The cloned genes are known by protein sequence, the expression by transcript ID (`NODE_...`), with no sequences. The transcript sequences (or the IDs of the cloned genes) would put each gene's expression and its correlation with the metabolites in the same table.
2. **Sequences of CiDE and CiIpS, and the accession numbers** ("to be announced").
3. **The bait of the *Alangium* table** (see part 1).
4. **Structures** of protoemetinol, 10-O-demethylprotoemetinol and 7-O-Me-DAIA.
5. **A decision on the evidence terms** for gene-to-reaction evidence from heterologous expression and from infiltration of substrates, and for co-expression with a bait gene; neither is in the specification yet. The RDF of the evidence is not written yet.

## Setup and run

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # pinned versions
.venv/bin/python match_ipecac.py            # part 1; uses the committed PlantMetWiki and UniProt snapshots
.venv/bin/python match_ipecac.py --refresh  # queries PlantMetWiki and UniProt again
.venv/bin/python pair_ipecac.py             # part 2; needs the files MOESM3 to MOESM7 in supplementaries/
```

The first run reads the two large workbooks (about a minute) and caches them as `.pkl` files in `data/`.
