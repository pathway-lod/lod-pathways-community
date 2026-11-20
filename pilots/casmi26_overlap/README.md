# CASMI 2026 (Enveda) training spectra: metabolite and pathway overlap (pilot, not run yet)

**Status.** Data downloaded (git-ignored `data/`), columns checked, first overlap run (steps 1 to 4 and 6 of the plan below). Steps 5 and 7 are not done. Download and first look: [notebooks/00_download_and_columns.ipynb](notebooks/00_download_and_columns.ipynb); script: [casmi_overlap.py](casmi_overlap.py); tables in `results/`. The Kaggle token is in `kaggle.env` (git-ignored; never commit it).

## First results (inchikey14 match, training set only)

- The columns match the description: `train.parquet` has 2,539,608 spectra, 18 columns, including `inchikey`, `inchikey14` and `normalized_smiles`. There are 275,810 unique `inchikey14`.
- **1,258 of 2,732 PlantMetWiki compounds (46 %) have at least one spectrum**; 1,145 of them are in a non-reaction pathway (of 2,384 PlantMetWiki compounds in pathways).
- **By library:** `enveda-180` (183k synthetic structures) matches none. The matches come from RIKEN (1,019), GNPS (981), MassBank (882), MS-DIAL (848), MoNA (829), pluskal_ms2 (502) and `drug_plus` (442, mostly primary metabolites that are also drugs). 1,086 of the 1,258 compounds have spectra in two or more libraries.
- **Pathways:** 1,125 of 1,162 non-reaction pathways have at least one compound with a spectrum; 782 have at least 4 members with at least half of them covered.
- **THT example:** caffeoyltyramine is not in PlantMetWiki but has **22 reference spectra** (MoNA, pluskal_ms2, RIKEN; 11 as [M+H]+). The pathway PWY-5474 has 7 of its 21 compounds with spectra. The structural hypothesis can therefore be checked against reference MS/MS if the MS/MS of the feature becomes available (the MetaboLights files have none).
- **Caveats:** matching on the first block merges stereoisomers (cis/trans) and charge forms; the 46 % counts skeletons, not the same stereoisomer. Spectra with a large precursor error were not removed from the counts (2,360,254 of 2,539,608 are within 10 ppm; 1,223 matches keep a good spectrum).

**Question.** Do the structures with MS/MS spectra in the training set overlap with PlantMetWiki compounds and pathways? If so, which pathways, and can the spectra give the structural evidence that MS-only features (as in the MEANtools example) lack?

Competition: <https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra>

## What the data are

- **`train.parquet`:** about 2.5 million MS/MS spectra for about 275,000 unique structures, one row per spectrum.
- **`test.parquet`:** about 1,500 spectra of about 400 molecules on a Bruker timsTOF (the file shown now is a sample of the training data; the hidden set replaces it). Not needed for the overlap.
- **InChIKeys are in the training data:** `inchikey` and `inchikey14` (first block, the 2D skeleton without stereochemistry), plus `normalized_smiles` (RDKit-standardised), `molecular_formula`, `adduct`, `precursor_error_ppm` (label-quality signal; ships uncleaned) and `ingest_lib`. The test set has no structures.
- The matching key is therefore `inchikey14`, the same first 14 characters as in the earlier metabolite overlap with PlantMetWiki.

| Source (`ingest_lib`) | Spectra | Unique structures | Relevance here |
|---|---|---|---|
| enveda-180 | 1,153,785 | 182,941 | synthetic drug-like compounds; timsTOF; likely little overlap with plant metabolites |
| pluskal_ms2 (MSnLib) | 527,581 | 46,821 | commercial screening and bioactive libraries; Orbitrap |
| **riken** | 347,171 | 15,892 | **strong focus on plant specialised metabolites; most promising** |
| **gnps** | 220,849 | 45,750 | large natural-product collection; heterogeneous |
| massbank | 101,727 | 9,180 | curated, multi-lab |
| mona | 92,416 | 11,681 | community-hosted |
| spectraverse | 50,933 | 9,631 | harmonised aggregation |
| msdial | 40,765 | 9,127 | MS-DIAL public libraries |
| drug_plus | 2,545 | 2,539 | drugs |
| **enveda-np-examples** | 1,151 | 250 | 250 common natural products, same instrument and pipeline as the test set |
| masaryk | 652 | n/a | not described |

Caveats from the description: libraries overlap in compounds (exact duplicate spectra were removed, the same compound from several libraries remains); preprocessing, collision-energy units and instrument strings differ per library; the count of adducts in the test set is given as ten in one place and seven in another. Count unique structures after merging libraries, not spectra.

## Plan

1. Download into `data/` (kept out of git; commit scripts and result tables only). Print the columns and check them against the description. **Done.**
2. Deduplicate to unique `inchikey14` per library. Drop spectra with a large `precursor_error_ppm` and report how many.
3. Match against PlantMetWiki compounds (`../metabolomics_overlap/data/`) on `inchikey14`; report full-key matches separately.
4. Report the overlap per library (expect RIKEN and GNPS to carry most of it) and the overlap with compounds in a non-reaction PlantCyc pathway.
5. Test against chance: random compounds of similar mass (or from the same library) matched to PlantMetWiki the same way.
6. List the pathways the overlapping compounds fall in and how many members of each pathway have a reference spectrum.
7. Then the use case: for an orphan feature (no PlantMetWiki mass match), do spectra of PlantMetWiki compounds or their pathway neighbours give evidence (spectral similarity, shared fragments) that mass alone does not?

## Other resources named by the competition

These are for annotation and pretraining. Only the ones marked "use" are relevant to the overlap and the use case.

| Resource | What it offers | Use here |
|---|---|---|
| **MIST-CF, SIRIUS** | molecular-formula annotation from MS/MS (learned and rule-based); fixing the formula first narrows the structure search | possible step before the mass-delta tier: a formula for an orphan feature |
| **matchms** | open library for cleaning, curation and similarity of mass spectra | use: spectral similarity between features and reference spectra |
| **GNPS propagated ("suspect") annotations** | structures transferred to unknown spectra through spectral-network similarity; excluded from `train.parquet` because the labels are inferred, not measured | a source of network-based links, with inferred labels |
| **MassIVE** | community repository of raw metabolomics runs, billions of unannotated MS/MS spectra, no structure labels | a place to look for spectra of our datasets or of PlantMetWiki compounds; raw data |
| **GeMS and DreaMS** | curated corpus of unannotated spectra mined from MassIVE and pretrained spectrum-embedding models (DreaMS) | embeddings could give a spectrum-similarity route not based on structure |
| **FragHub** | open repository that merges and harmonises the major open MS/MS libraries; overlaps heavily with the training set but may add experimental or predicted spectra | use: extra reference spectra for compounds missing in the training set |

## Open points

- The overlap does not yet say how many of the 1,258 compounds are plant-specific versus primary metabolites or drugs; the library breakdown suggests many are common metabolites.
- Class 1 to 3 in the test set (public spectra, known structure without spectra, novel structure) do not apply to the overlap, but they matter for how far database retrieval of a structure can go: class 2 compounds are in PubChem or COCONUT, not in the spectral libraries.
