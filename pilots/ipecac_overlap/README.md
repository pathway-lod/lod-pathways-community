# Pilot: ipecac alkaloid biosynthesis (Colinas et al.) vs PlantMetWiki

Which metabolites and which pathway steps of *Ipecac alkaloid biosynthesis in two evolutionarily distant plants* (Colinas, Morweiser, Dittberner et al., O'Connor lab) are already in [PlantMetWiki](https://plantmetwiki.bioinformatics.nl), and where could the data add evidence to a pathway?

This pilot belongs to the PO (paired omics) and MET use cases of the [specification](../../specification/SPECIFICATION.md). It is a first pass: the deposit holds the transcript side and the metabolite structures, but not yet the metabolite measurements, so the pairing itself is still to do (see [What is missing](#what-is-missing)).

## Inputs

| Input | Source |
|---|---|
| SMILES of the 12 metabolites of Figure 2 | Zenodo [10.5281/zenodo.23661892](https://doi.org/10.5281/zenodo.23661892), `smiles.xlsx` |
| Expression and Pearson correlation of 137,713 transcripts of *Carapichea ipecacuanha* (Ci), 6 tissues | same record, `Ci_transcriptome_pearson.xlsx` |
| Expression and Pearson correlation of 178,877 transcripts of *Alangium salviifolium* (As), 12 tissues | same record, `As_transcriptome_pearson.xlsx` |
| PlantMetWiki metabolites, the pathway *emetine biosynthesis* (PlantCyc PWY-7135) and its enzymes | SPARQL endpoint, snapshots in `data/plantmetwiki_*.csv` (date in `data/SNAPSHOT_INFO.txt`) |
| Names and EC numbers of the enzymes of PWY-7135 | UniProt REST, snapshot `data/uniprot_pwy7135_enzymes.tsv` |

The three Zenodo files are downloaded on the first run and checked against the MD5 sums that Zenodo lists.

**What the transcript tables are.** The author's description (personal communication): the transcriptomes are de novo assemblies from short reads. The Pearson value is the correlation of a transcript's expression across the tissues with a *bait* gene; metabolite data were not used as bait and the transcriptome was not correlated with the metabolome. The author's cut-offs were Pearson ≥ 0.75 and an expression of at least 50 in the tissue of highest expression of the genes (leaf buds in *Alangium*, young leaf in *Carapichea*). Candidates were then filtered by their eggNOG-mapper description. The IDs are those of the assembly; there are no UniProt identifiers and no sequences in the deposit.

## Method

- **Metabolites.** The SMILES are converted to InChIKeys with RDKit. PlantMetWiki nodes with the same first block (connectivity) are found, and the match level is read from the key blocks: `full` (all three equal), `stereo (protonation differs)` (blocks 1 and 2 equal), `connectivity` (block 1 only), `none`. PlantMetWiki stores charged forms of amines (keys ending in `-O` or `-P`), while the paper's structures are neutral (`-N`), so a full-key comparison fails for alkaloids.
- **Pathway.** The conversions of PWY-7135, their enzymes (UniProt accession, name, EC) and which of the paper's metabolites are the substrates and products.
- **Genes.** Transcripts with Pearson ≥ 0.75 and expression ≥ 50 are selected. The reported Pearson values were reproduced from the expression columns (raw values, bait row as reference; largest difference 7e-16). The p-value is not in the deposit; it is derived from r and the number of tissues (two-sided t-test) and is only an indication.
- **Classes.** The eggNOG description is searched for enzyme-family words (methyltransferase, cytochrome P450, decarboxylase and so on) and each class is tested for enrichment among the selected transcripts against all annotated transcripts (Fisher's exact test, Benjamini-Hochberg over all 18 tests). These are family-level hypotheses, not annotations of a function.

## Results

### Metabolites

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

### The pathway in PlantMetWiki

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

### Genes

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

## What this gives PlantMetWiki

- **Metabolite evidence for an existing pathway.** Six metabolites of the data set are in the pathway, each at a defined match level (a claim with `matchLevel` connectivity, stereo or full, as in the [specification](../../specification/SPECIFICATION.md), MET-08).
- **A list of missing intermediates.** Six structures, mostly the acid forms, that PlantMetWiki's emetine pathway does not have.
- **A list of steps without a gene** (three of eight).
- **A candidate list of co-expressed genes** (369 and 1,413 transcripts), usable for the unlabelled steps once the transcripts can be linked to sequences.
- **A finding for the specification:** a match level between `connectivity` and `full` is needed ("stereo, protonation differs"), because PlantMetWiki stores charged forms of amines. The current values of MET-08 are `connectivity` and `full`.

## What is missing

1. **The metabolite measurements.** The deposit has only the SMILES. The peak areas per tissue (Source Data of Figure 2 in the paper) would pair each metabolite with the expression of the same tissues, so that gene-metabolite correlations, which the authors did not calculate, can be computed and aligned in the graph as in the [MEANtools pilot](../meantools_overlap/). Source Data of Figures 3b-c and 4 (heterologous expression in *N. benthamiana*, each row a gene combination, each point one plant) would give experimental evidence for single reactions.
2. **Sequences or accessions.** To link a transcript to a UniProt entry, and so to a PlantMetWiki enzyme, the sequences of the assembled transcripts, or the accession numbers of the cloned genes, are needed.
3. **The bait of the *Alangium* table** (see above).
4. **A decision on the evidence terms** for gene-to-reaction evidence from heterologous expression (an experimental evidence class) and for co-expression with a bait gene; neither is in the specification yet.

## Setup and run

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # pinned versions
.venv/bin/python match_ipecac.py            # uses the committed PlantMetWiki and UniProt snapshots
.venv/bin/python match_ipecac.py --refresh  # queries PlantMetWiki and UniProt again
```

The first run reads the two large workbooks (about a minute) and caches them as `.pkl` files in `data/`.
