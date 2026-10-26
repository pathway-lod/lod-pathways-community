# Pilot: Brassicaceae LC-MS/MS annotations vs PlantMetWiki metabolites

How many metabolites annotated in the Brassicaceae metabolic fingerprinting dataset (Wolters et al. 2026) are present as metabolites in [PlantMetWiki](https://plantmetwiki.bioinformatics.nl)?

This is the first test of the MET use case (consensus from MS/MS tools) of the [specification](../../specification/SPECIFICATION.md#3-met---metabolomics-data); see also the [pipeline](../../README.md#the-pipeline).

## Inputs

| Input | Source |
|---|---|
| Annotated GNPS2 FBMN node tables (neg + pos, 14 species, leaf + root) | Zenodo [10.5281/zenodo.19391098](https://doi.org/10.5281/zenodo.19391098), file `S6_Annotation_tables_and_annotated_FBMNs.zip` |
| PlantMetWiki metabolites (`wp:Metabolite` with `wp:bdbInChIKey`), their PlantCyc pathways and pathway classes | SPARQL endpoint `https://plantmetwiki.bioinformatics.nl/sparql`, snapshots in `data/plantmetwiki_*.csv` (2026-09-29) |

## Supplementary files S1-S6

The dataset deposit (Zenodo [10.5281/zenodo.19391098](https://doi.org/10.5281/zenodo.19391098)) holds six supplementary archives. Only S6 is used by the matching. The others document how the data were acquired and processed and are the source of several MET requirements in the [specification](../../specification/SPECIFICATION.md). `python fetch_supplementary.py` downloads them (with MD5 check, resumable); [`data/supplementary/README.md`](data/supplementary/README.md) lists what each file contains and which MET requirement it feeds.

| File | Content | Used for |
|---|---|---|
| S1 | Instrument settings and mass exclusion lists, positive and negative mode (Thermo Orbitrap Exploris 120) | MET-16, MET-19 to MET-22 |
| S2 | mzmine batch files and aligned feature lists, positive and negative mode | MET-23 |
| S3 | MS2LDA configuration and results (Mass2Motifs), 385 MB | MET-27 |
| S4 | Consensus annotation reports and summary table | MET-02, MET-11 |
| S5 | Feature table of 17 species, negative mode, with SIRIUS summaries | MET-24 to MET-26 |
| S6 | Annotation tables and annotated FBMNs, 14 species | the matching in this pilot |

## Method

- Each feature can have up to six structure predictions. Each prediction is assigned an **evidence tier**, strongest first:
  1. `gnps_library`: GNPS spectral library match
  2. `consensus_inchi`: ≥ 2 of SIRIUS / MS2Query / DreaMS agree on the structure (the consensus module of Wolters et al. 2026)
  3. `sirius`: SIRIUS CSI:FingerID top hit
  4. `ms2query_exact`: MS2Query hit with precursor m/z difference ≤ 0.01 Da
  5. `dreams`: DreaMS top hit
  6. `ms2query_analog`: MS2Query analogue (different mass, so a related compound, **not** the same one; reported separately)
- Matching uses the **first InChIKey block** (connectivity only). Stereochemistry and charge are ignored, because PlantMetWiki often stores charged forms (e.g. carboxylates, sulfonates) while MS tools predict neutral structures.

## Setup and run

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # pinned versions
```

Open [`explore_results.ipynb`](explore_results.ipynb) in VS Code, select the `.venv` kernel and **Run All**. Or, from the command line:

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace explore_results.ipynb
```

- The Zenodo S6 file is downloaded on the first run and checked against its MD5 checksum.
- PlantMetWiki is read from the committed snapshots `data/plantmetwiki_*.csv` (2026-09-29), so re-runs give identical results. To use the live PlantMetWiki, delete those files and re-run.
- All matching logic is in [`match_plantmetwiki.py`](match_plantmetwiki.py). `.venv/bin/python match_plantmetwiki.py` only writes the CSVs.

## Outputs

- [`explore_results.ipynb`](explore_results.ipynb) holds the results with written interpretation. It covers:
  - evidence tiers
  - hit rate per tier and ion mode
  - cumulative coverage
  - tier agreement
  - strong matches
  - **pathway coverage** (with keyword search)
  - coverage per species
  - **primary vs specialized metabolism**
  - **gaps** (library-identified compounds missing from PlantMetWiki)
  - a name lookup
- `results/matched_plantmetwiki_metabolites.csv`: one row per matched PlantMetWiki metabolite
- `results/feature_hits.csv`: one row per feature × tier that hits PlantMetWiki

## First results (2026-09-29)

| Evidence included | Distinct PlantMetWiki metabolites detected | % of PlantMetWiki (2,732) |
|---|---|---|
| GNPS library only | 56 | 2.0 |
| + consensus | 139 | 5.1 |
| + SIRIUS | 258 | 9.4 |
| + MS2Query exact | 369 | 13.5 |
| + DreaMS | 567 | 20.8 |

- The **strong evidence** (library + consensus) covers ~140 PlantMetWiki metabolites. These are mostly primary metabolism and phenylpropanoids, plus glucosinolates such as glucotropaeolin, glucoraphanin and sinigrin.
- Single-tool predictions (SIRIUS, DreaMS) add many more matches, but each of those rests on one tool only.
- With strong evidence, 677 of 1,123 PlantCyc pathways (≥ 3 metabolites) have at least one detected metabolite.
- 129 library-identified structures are not in PlantMetWiki. Some are real gaps, others may be PlantMetWiki metabolites without an InChIKey.
- **Primary vs specialized:** the matches are *not* dominated by primary metabolism. Among strongly supported matches, 45% of metabolites occur only in specialized pathways, 27% only in primary pathways, and 25% in both. Metabolites in both are branch points (phenylalanine, tryptophan, methionine, 4-coumarate, ferulate) and common co-substrates (UDP-glucose, glutathione), and they are about 3× over-represented compared with PlantMetWiki as a whole (8.5%). The best-covered specialized classes are flavonols, anthocyanins, coumarins, hydroxycinnamates and glucosinolates.
- **Example gap:** glucosinalbin (p-hydroxybenzyl glucosinolate, typical of *Sinapis alba*) has a GNPS library match in the data but is not a PlantMetWiki metabolite.

## Caveats / next steps

- [ ] Ignoring stereochemistry can merge isomers, e.g. UDP-glucose and UDP-galactose. Check the stereo-aware (full InChIKey) matches too.
- [ ] 10% of PlantMetWiki metabolites have no InChIKey, so they can't be matched this way.
- [ ] Add species-aware matching: is the metabolite in a PlantMetWiki pathway *for the same species or genus*?
- [ ] Curate the gap list in the notebook (section 9): real gaps vs. metabolites without an InChIKey in PlantMetWiki.
- [ ] Review the hand-made class mapping in [`data/pathway_class_categories.csv`](data/pathway_class_categories.csv). PlantMetWiki only stores the most specific PlantCyc class, and the MetaCyc hierarchy needs a BioCyc account. Carotenoids and lignin count as specialized, following MetaCyc. It might be worth adding the class hierarchy to PlantMetWiki itself.
- [ ] Express the matches as RDF using the evidence model of the [specification](../../specification/SPECIFICATION.md) (ECO terms per tier).
