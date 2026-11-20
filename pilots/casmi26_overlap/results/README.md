# Results: PlantMetWiki and the CASMI 2026 spectral libraries

Training set of the Enveda CASMI 2026 competition (2,539,608 spectra, 275,810 unique structures) matched to PlantMetWiki compounds (2,732 with an InChIKey) on `inchikey14`, the first block of the InChIKey. Stereoisomers and charge forms of one skeleton therefore count together. Scripts and notebooks: [../casmi_overlap.py](../casmi_overlap.py), [../notebooks/00_download_and_columns.ipynb](../notebooks/00_download_and_columns.ipynb), [../notebooks/01_plantmetwiki_library_connectivity.ipynb](../notebooks/01_plantmetwiki_library_connectivity.ipynb). Plan and dataset description: [../README.md](../README.md).

## Takeaways

- **Nearly half of PlantMetWiki has reference MS/MS.** 1,258 of 2,732 compounds (46 %) match a structure in the training set; 1,145 of them are in a non-reaction pathway.
- **A few natural-product libraries carry it.** RIKEN, GNPS, MassBank, MS-DIAL and MoNA each cover about a third of PlantMetWiki (30 to 37 %) and overlap heavily with each other. The largest set, `enveda-180` (183k synthetic drug-like structures), matches none.
- **We do not need many libraries.** Five libraries already reach 1,249 of the 1,258 matched compounds. GNPS (60 compounds) and MassBank (41) add the most compounds found nowhere else.
- **Coverage is about 50 % in every pathway category.** 49 % of the compounds of primary pathways have a spectrum in at least one library, 51 % of specialized, 53 % of hormone and 59 % of other pathways. At pathway level, specialized pathways are slightly behind (median 56 % of their compounds covered, against 62 % for primary).
- **The gaps are in specific classes.** Sesquiterpenoid synthesis is lowest (at most 18 % of its compounds in any library), then glucosinolate and sterol biosynthesis (up to about a third). Interconversion, energy metabolism and cinnamate synthesis are best covered (about 60 to 75 % in the large libraries).
- **THT example.** Caffeoyltyramine is not in PlantMetWiki but has 22 reference spectra (MoNA, pluskal_ms2, RIKEN; 11 as [M+H]+). The MS/MS check that the MEANtools example lacked is possible if the feature's own MS/MS becomes available; the public MetaboLights files have none. Pathway PWY-5474 has 7 of its 21 compounds with spectra.

## Numbers

| Library | Structures | PlantMetWiki matches | in a pathway |
|---|---|---|---|
| all libraries | 275,810 | 1,258 | 1,145 |
| riken | 15,892 | 1,019 | 940 |
| gnps | 45,750 | 981 | 894 |
| massbank | 9,180 | 882 | 806 |
| msdial | 9,127 | 848 | 781 |
| mona | 11,681 | 829 | 760 |
| pluskal_ms2 | 46,821 | 502 | 478 |
| drug_plus | 2,539 | 442 | 400 |
| enveda-np-examples | 250 | 71 | 69 |
| masaryk | 416 | 46 | 43 |
| spectraverse | 9,631 | 20 | 15 |
| enveda-180 | 182,941 | 0 | 0 |

1,086 of the 1,258 matched compounds have spectra in two or more libraries. Of 1,162 non-reaction pathways, 1,125 have at least one compound with a spectrum, and 782 have 4 or more compounds with at least half of them covered.

## Tables

| File | Content |
|---|---|
| `overlap_summary.json` | totals |
| `overlap_per_library.csv` | structures, matches and pathway matches per library |
| `overlap_compounds.csv` | the 1,258 matched compounds with number of spectra, libraries, adducts, formula and name |
| `pathway_spectra_coverage.csv` | per pathway: members, members with spectra, fraction |

Figures: `../notebooks/figures/` (library coverage, overlap and network, unique contribution and cumulative coverage, category and class coverage).

## Caveats

- A match shows that a reference spectrum exists, not that it is a good one. The figures do not filter precursor error or adduct (2,360,254 of the 2,539,608 spectra are within 10 ppm; 1,223 of the 1,258 matches keep a spectrum within 10 ppm).
- Matching on the first block merges stereoisomers (for example cis and trans) and charge forms; it counts skeletons, not the same stereoisomer.
- Many matches are probably common primary metabolites or drugs (`drug_plus` matches 442), not specifically plant metabolites.
- `spectraverse` (20 matches) is almost disjoint from all other libraries (19 unique). This is unexpected for an aggregation of public libraries and has not been checked (key format or a different part of chemical space).
- The pathway category is derived from the PlantCyc classes with a priority rule (specialized, then hormones, then primary); a compound counts in every category in which it has a pathway.

## Not done

- A comparison with chance is not meaningful for identity matches, but a comparison by mass or class would show how special the 46 % is.
- It has not been tested whether the reference spectra help annotate real orphan features (README step 7).
