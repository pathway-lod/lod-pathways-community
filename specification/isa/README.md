# Mapping of the requirements to ISA

[`isa_mapping.csv`](isa_mapping.csv) maps each requirement of the [term table](../ontology_terms.csv) to the place where ISA records it, in ISA-Tab and in ISA-JSON.

The table was made from the term table of `main` at commit `1b4f463` (119 requirements). It also has four rows proposed in pull request #26 and not on `main` yet: TX-23 and MET-32 (developmental stage), TX-24 and MET-33 (growth conditions).

## Columns

| Column | Content |
|---|---|
| `req_id`, `use_case`, `requirement` | as in the term table |
| `terms_in_table` | the primary, local and stand-in terms of the requirement in the term table |
| `isa_coverage` | how ISA covers the requirement (see below) |
| `isa_tab` | the ISA-Tab file and field |
| `isa_json` | the ISA-JSON path |
| `notes` | what the mapping covers and what it leaves out |

## Coverage

| `isa_coverage` | Meaning | Rows |
|---|---|---|
| `isa_field` | ISA has a field for it, for example `Characteristics[Organism]`, `Factor Value[...]` or `Study Assay Measurement Type`. | 21 |
| `parameter` | ISA has no field for it. It goes into a `Parameter Value[...]` or `Comment[...]` of the protocol that produced the data. | 22 |
| `data_file` | The values are inside a data file that ISA points to, such as a count matrix or a feature table. | 22 |
| `assignment_file` | A column of the Metabolite Assignment File, an ISA data file type whose columns MetaboLights defines. | 5 |
| `not_in_isa` | A claim or its evidence, such as the attachment to PlantMetWiki, the anchor tier or the PlantCyc evidence codes. It stays in the RDF evidence model. | 53 |

ISA describes how the data were produced: the samples, the protocols, the assays and the data files. The requirements about samples, protocols and runs map to ISA. The requirements about claims and evidence do not, and ISA can only point to them as a data file.

The minimum information standard proposed in pull request #43 (issue #40) defines evidence tiers for the claims. Part of the information the tiers require, such as the tool and its version, has a place in ISA as a protocol component or parameter value.

All 14 PlantCyc rows (PMN) and 12 of the 16 BGC rows are `not_in_isa`. Of the 21 `isa_field` rows, 9 are metabolomics (MET) and 8 transcriptomics (TX) rows.

## Notes

- The name inside `Characteristics[...]` is free. MetaboLights study MTBLS1039 uses `Characteristics[Organism part]` on the Source. MIAPPE uses `Characteristics[Plant Anatomical Entity]` and `Characteristics[Plant Structure Development Stage]` on the Extract in the assay file. The table gives both for plant structure and follows MIAPPE for developmental stage.
- MIAPPE records the growth facility as `Comment[Type of Growth Facility]` and `Comment[Description of Growth Facility]` under STUDY DESIGN DESCRIPTORS, and environment parameters as parameters of the growth protocol. The table follows this for TX-24 and MET-33.
- The Metabolite Assignment File has columns for `inchi`, `database_identifier`, `reliability`, `search_engine`, `search_engine_score`, `mass_to_charge`, `retention_time`, `charge`, `modifications` and one abundance column per sample. It has no InChIKey column and no adduct column.
- Software and its version have no fixed field in ISA. The table uses protocol components and parameter values. `Study Protocol Version` is the version of a protocol, not of the software.
