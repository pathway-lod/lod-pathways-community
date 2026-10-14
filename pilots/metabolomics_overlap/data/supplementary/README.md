# Supplementary files of the Brassicaceae metabolic fingerprinting dataset

Source: Wolters et al., Zenodo record [10.5281/zenodo.19391098](https://doi.org/10.5281/zenodo.19391098)
("Systematic mass spectrometry-guided metabolic fingerprinting elucidates diversity of specialized metabolites across the Brassicaceae", version 1.0).

The archives are not committed (see `../../.gitignore`). Download them with `python ../../fetch_supplementary.py [S1 S2 ...] [--extract]`.
Each file is checked against the MD5 sum that Zenodo lists. Notes below were taken on 2026-10-14 from the files themselves, except where marked.

| File | Size | MD5 | Status |
|---|---|---|---|
| `S1_Instrument_settings_mass_exclusion_lists.zip` | 28 KB | d0d72c66ee7e370704dfa9f3fbd46696 | inspected |
| `S2_mzmine_4.5.0_batchfiles.zip` | 8.5 MB | 5e789dc9a7820724e24cab19fe051586 | inspected |
| `S3_MS2LDA_config_and_results.zip` | 385 MB | f366a08331e199863e14b12aad240afd | inspected (settings, tables, motif set) |
| `S4_HTML_summaries_consensus_annotations.zip` | 25 MB | af4496ab6a0772df16cc068d8a492056 | listed; summary table read, HTML reports not opened |
| `S5_Featuretable_batch_integration_17species_MSCluster.zip` | 12.6 MB | 5828c4282fd8ea45bf4a51c399ffe5e1 | inspected (columns) |
| `S6_Annotation_tables_and_annotated_FBMNs.zip` | 44.9 MB | ef234f42d2db0d52d1e851237bed4d5c | used by `match_plantmetwiki.py` |
| `Supplementary_figure_S1-S3.pdf` | 1.3 MB | ac99fa79c9766207fea6141825af2838 | not opened |

## S1: instrument settings and exclusion lists

Two Word files (`pos mode settings.docx`, `neg mode settings.docx`), one Thermo Orbitrap Exploris 120 method each (last modified 2023-08-25 for positive, 2023-08-24 for negative).

| Setting | Value (both modes unless stated) |
|---|---|
| Ion source | H-ESI, spray voltage 3000 V (positive) and 2500 V (negative) |
| Polarity | Positive in the positive-mode file, Negative in the negative-mode file |
| MS1 | Orbitrap resolution 60,000, scan range 90-1350 m/z, centroid |
| Selection | data-dependent, 4 dependent scans, isolation window 1.5 m/z |
| MS2 | HCD, normalised collision energies 20, 40, 100 %, Orbitrap resolution 15,000 |
| Exclusion | dynamic exclusion 7 s, 5 ppm, isotopes excluded; targeted exclusion mass list with about 100 m/z values per mode (15 min, 30 min window) |
| Run length | 30 min |

Feeds: MET-16 and MET-19 (polarity), MET-20 (instrument, source), MET-21 (acquisition method), MET-22 (exclusion list, gap).

## S2: mzmine batch files

Two `.mzbatch` files (one per mode), the aligned feature lists as `.mgf`, and the quantification tables (`*_Aligned_feature_list_quant.csv`).

- The batch files declare `mzmine_version="4.8.0"`; the archive name says 4.5.0. The file name `batch_MP23_*_4-8-0_v4_01a_251024` carries the same version.
- Steps in the batch: spectral data import, mass detection (MS1 and MS2), ADAP chromatogram builder, smoothing, minimum-search feature resolver, isotope grouper and finder, peak finder, duplicate filter, join aligner, blank subtraction, spectral library search, correlation grouping, SIRIUS export, GNPS FBMN export, ion identity networking, spectral networking.
- The mass detection step has `Polarity = Any`: polarity is not set in the batch; it follows from the data files.
- Feature counts in the quantification tables: 6,433 (negative) and 7,683 (positive).

Feeds: MET-23 (processing run), MET-13, MET-14 (feature and identifier), MET-25 (peak area).

## S3: MS2LDA configuration and results

MS2LDA topic modelling of the MS/MS spectra, one folder per mode (`ms2lda_14LR_pos_260113`, `ms2lda_14LR_neg_260114`) and the configuration `MS2LDA_neg_settings.json`.

- Settings: data-dependent acquisition, charge 1, 400 motifs, `min_df` 3, `alpha` 0.6, `eta` 0.01, seed 42, convergence on perplexity; annotation of motifs with Spec2Vec (cosine similarity >= 0.90, 5 molecules per motif) and MACCS fingerprints. Only the negative-mode settings file is in the archive; the positive-mode settings are not given.
- `*_corrected_ids_long.csv`: one row per feature and motif (`id, motif, probability, motif_index`); about 44,900 rows in positive mode. The `_wide` tables hold the same as a matrix.
- `motifset.json`: per motif, fragment and neutral-loss m/z values with weights, and automatic structure annotations (SMILES).
- Also model binaries (`ms2lda.bin`, 967 MB unzipped in total), a molecular network (`network.graphml`), convergence plots and motif figures. The archive contains a stray LibreOffice lock file (`.~lock...#`).

Feeds: MET-27 (Mass2Motif assigned to a feature).

## S4: consensus annotation reports

- Two HTML reports (positive and negative mode), one `.ods` workbook and `annotation_matching_module_251203_summary_table.csv`.
- The summary table counts features by what the tools (SIRIUS, MS2Query, DreaMS) agree on, at four levels: `inchi`, `class`, `superclass`, `pathway` (NPClassifier levels). Totals per category are 7,683 features, the same number as the positive-mode features of S2 (the table does not say which mode it covers; not confirmed). For the structure level: full agreement 49, partial 568, none 7,066. For the NPClassifier pathway level: full 1,839, partial 3,416, none 2,428.

Feeds: MET-02, MET-11 (including `lodp:matchCategory`).

## S5: aligned feature table of 17 species (negative mode)

- `17_LR_neg_250710_GNPS2_node-table.csv` (11,271 features, 164 columns) and `17LR_neg_consensus-spectra_MSCluster_specs_ms_GNPS2.mgf`.
- A folder with the SIRIUS summary tables (`structure_identifications.tsv`, `formula_identifications.tsv`, `canopus_structure_summary.tsv`, `spectral_matches.tsv`, `feature_quality.tsv` and others).
- Columns include `InChIkey2D`, `molecularFormula`, `adduct`, `ConfidenceScoreApproximate`, `CSI:FingerIDScore`, ClassyFire and NPC classes with probabilities, library match columns, `mz`, `rt`.
- No positive-mode counterpart is in S5.

Feeds: MET-24 (organism, tissue), MET-25 (abundance), MET-26 (compound class).

## S6: annotation tables

Used by the pilot (`match_plantmetwiki.py`). The two node tables (`14_LR_neg_...`, `14_LR_pos_...`) have 193 columns: per-tool prediction columns (`sirius_*`, `ms2query_*`, `dreams_*`, `canopus_*`), library match columns, consensus columns (`match_*`), `mz`, `rt`, and `ATTRIBUTE_*` columns for genus, species, tribe, tissue and accession.

Differences to the deposit text: it mentions mzmine 4.8.5; the batch files say 4.8.0.
