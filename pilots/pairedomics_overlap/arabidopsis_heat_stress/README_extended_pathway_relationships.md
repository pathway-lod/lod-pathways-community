# Extended PlantCyc Pathway Relationships

Extend the *Arabidopsis thaliana* heat-stress multi-omics pathway-mapping workflow with **explicit pathway hierarchy** and optional **shared-reaction evidence**.

`add_extended_pathway_relationships.py` is **offline-only**. It does not contact BioCyc, PlantCyc, or other online services. It reads either an existing pathway hierarchy CSV or an official local PlantCyc `pathways.dat` file.

> **Prerequisite:** Run the basic pathway mapper first to create `results/annotated_correlations/*_annotated.csv`. If those annotated files already exist and are up to date, you do not need to rerun the mapper. This extender does not map molecular identifiers or calculate correlations.

## Installation

Python 3.9+ is recommended. The only external dependency is `pandas`:

```bash
pip install pandas
```

Place `add_extended_pathway_relationships.py` in the root of your `arabidopsis_heat_stress` project. Alternatively, specify `--project-dir`.

## Running with the official PlantCyc database

Obtain the official PlantCyc flat-file export through the Plant Metabolic Network's permitted download process, then place `pathways.dat` in your project, for example at `data/plantcyc/pathways.dat`.

```bash
python add_extended_pathway_relationships.py --plantcyc-dat data/plantcyc/pathways.dat
```

The script reads `UNIQUE-ID`, `SUPER-PATHWAYS`, and `SUB-PATHWAYS` records, validates referenced IDs against the pathways represented in the file, and writes explicit parent–subpathway links to:

```text
results/mapping_tables/pathway_hierarchy.csv
```

The output has the schema:

```csv
child_pathway_id,parent_pathway_id
SUBPATHWAY_ID,PARENT_PATHWAY_ID
```

The example IDs are placeholders, not actual biological relationships. If references cannot be resolved, the script also writes `results/mapping_tables/pathway_hierarchy_skipped.csv`. If the `.dat` file provides zero valid hierarchy links, the script exits without overwriting any existing hierarchy CSV.

**Hierarchy means pathway containment**, not pathway classification or similarity between names. The hierarchy is followed recursively when comparing pairs of pathway IDs.

## Running with an existing hierarchy CSV

If you have already produced `results/mapping_tables/pathway_hierarchy.csv`, run:

```bash
python add_extended_pathway_relationships.py
```

Or supply a different hierarchy CSV:

```bash
python add_extended_pathway_relationships.py --hierarchy data/curated_pathway_hierarchy.csv
```

Only use evidence-backed parent–subpathway links. A partial CSV may miss genuine relationships.

## Optional: shared biochemical reactions

You may provide `results/mapping_tables/pathway_reactions.csv` with the following columns:

```csv
pathway_id,reaction_id
PATHWAY_A,REACTION_1
PATHWAY_B,REACTION_1
```

These are illustrative IDs. Populate this file with **verified reaction memberships**, using consistent identifiers across pathways. The script does not generate this table from `pathways.dat`.

To supply another reaction table:

```bash
python add_extended_pathway_relationships.py --reactions data/pathway_reactions.csv
```

Both hierarchy and reaction tables may be provided together; hierarchy matches take precedence over reaction overlap.

## Inputs and outputs

```text
arabidopsis_heat_stress/
├── add_extended_pathway_relationships.py
├── data/
│   └── plantcyc/
│       └── pathways.dat                         # optional, local database
└── results/
    ├── annotated_correlations/
    │   └── *_annotated.csv                       # required: basic mapper output
    ├── mapping_tables/
    │   ├── pathway_hierarchy.csv                 # existing or generated
    │   ├── pathway_reactions.csv                 # optional
    │   └── pathway_hierarchy_skipped.csv         # optional extraction diagnostic
    └── annotated_correlations_extended/
        └── *_annotated.csv                       # output, one per input
```

Required columns in each annotated CSV:

- `Feature1_mapped_pathway`
- `Feature2_mapped_pathway`

Multiple pathway IDs can be separated by commas or semicolons. The script compares **all IDs from Feature 1 against all IDs from Feature 2**; it does not stop at the first listed ID.

The script preserves all original columns (including `pathway_relationship`) and adds:

| Added column | Meaning |
| --- | --- |
| `pathway_relationship_extended` | Highest-priority relationship supported by the supplied data |
| `extended_related_pathway_pairs` | Supporting `Feature1Pathway\|Feature2Pathway` pairs, separated by semicolons |
| `extended_shared_reaction_ids` | Shared reaction IDs if a reaction-level match is identified |

Original CSVs are **not modified**. Extended CSVs are written under `results/annotated_correlations_extended/` with the same filenames and relative subdirectory structure as the inputs.

## Relationship categories

Comparison follows this order:

| Label | Interpretation |
| --- | --- |
| `same_pathway` | One or more identical pathway IDs on the two features |
| `hierarchy_related` | One mapped pathway is a direct or indirect ancestor/descendant of another |
| `shared_reaction` | Different pathways share a reaction ID in the supplied reaction-membership file |
| `no_extended_match` | No match found **within the provided evidence**; not proof of biological unrelatedness |
| `not_evaluated` | Neither usable hierarchy nor reaction-membership evidence was provided |
| `not_comparable` | One or both features have no mapped pathway IDs |

The relationship column is priority-ranked: `same_pathway` > `hierarchy_related` > `shared_reaction`. For example, when exact overlap exists, lower-priority relationships are not added to the supporting-pairs column.

**Coverage limitation:** A small or incomplete hierarchy/reaction CSV can produce `no_extended_match` even when a relationship exists elsewhere in PlantCyc. Interpret this label only in the context of the files and database release used.

## Command-line options

```bash
python add_extended_pathway_relationships.py --help
```

| Option | Purpose |
| --- | --- |
| `--project-dir PATH` | Project root (defaults to script's directory) |
| `--plantcyc-dat PATH` | Read local PlantCyc `pathways.dat` and generate hierarchy CSV |
| `--hierarchy PATH` | Read hierarchy CSV, or set its output path in `.dat` mode |
| `--reactions PATH` | Optional pathway-to-reaction CSV |
| `--output-dir PATH` | Output directory for extended correlation CSVs |

Relative paths are resolved against `--project-dir`.

## Troubleshooting

- **No annotated CSV files:** Run the basic mapping script or check `--project-dir`.
- **No hierarchy relationships:** Check that the official `pathways.dat` contains explicit `SUPER-PATHWAYS` or `SUB-PATHWAYS` fields, or supply a curated hierarchy CSV.
- **Many `not_evaluated` rows:** Neither relationship file is available or both are empty; provide hierarchy or reaction memberships.
- **Many `no_extended_match` rows:** The supplied relationships do not establish overlap; check data coverage and identifier consistency.
- **No `shared_reaction` results:** Reaction membership is optional and must be supplied separately; hierarchy matches take precedence.

## Scientific interpretation

The extended labels describe overlap or relatedness between **pathway annotations**, not causal mechanisms. A correlation between a protein and a metabolite is statistical evidence, and shared pathways or reactions do not prove a direct molecular interaction. Mapping confidence remains defined by the original mapper's AGI, UniProt, EC, and InChIKey evidence tiers; this script does not change those tiers.

Record the PlantCyc release/date and the origin of any curated hierarchy or reaction files when reporting your results.

## Relationship to the Turtle exporter

The separate Turtle exporter currently reads `results/annotated_correlations/` by default. It **does not automatically read** `results/annotated_correlations_extended/` or serialize the new extended columns. To include them in RDF, its input-directory handling and predicate serialization would need to be updated.
