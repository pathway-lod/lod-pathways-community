# CASMI 2026 (Enveda) training spectra: metabolite and pathway overlap (pilot, not run yet)

**Status.** Plan only. The data are not downloaded yet: the Kaggle competition files need a login and acceptance of the competition rules. Everything below about the data comes from the competition's dataset description, not from the files. Check it against the files once they are in `data/`.

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

1. Download into `data/` (kept out of git; commit scripts and result tables only). Print the columns and check them against the description.
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

- Whether PlantMetWiki structures are in the data at all is not known until the files are read.
- Class 1 to 3 in the test set (public spectra, known structure without spectra, novel structure) do not apply to the overlap, but they matter for how far database retrieval of a structure can go: class 2 compounds are in PubChem or COCONUT, not in the spectral libraries.
