# Separate RDF/Turtle Export for Arabidopsis Multi-Omics Correlations

`export_omics_turtle_separate.py` converts annotated correlation CSVs from the Arabidopsis heat-stress pathway-mapping pipeline into **one independent Turtle (`.ttl`) file per annotated CSV**. It runs offline: no UniProt, BioCyc, or PlantMetWiki queries are made.

The exporter represents each selected correlation row as an association between two omics features, attaches correlation statistics, links feature-to-PlantCyc pathway assignments, and records mapping evidence when available.

## Requirements

- Python 3.10 or newer (recommended)
- `pandas`
- `rdflib`

```bash
pip install pandas rdflib
```

## Directory layout

Place the exporter in the project root alongside the mapping script:

```text
arabidopsis_heat_stress/
├── map_omics_to_plantmetwiki.py
├── export_omics_turtle_separate.py
└── results/
    ├── annotated_correlations/
    │   ├── Significant_Transcriptomics_Proteomics_annotated.csv
    │   ├── Significant_Transcriptomics_Metabolomics_annotated.csv
    │   └── Significant_Proteomics_Metabolomics_annotated.csv
    ├── mapping_tables/
    │   └── mapping_provenance.csv       # optional, recommended
    └── turtle/                         # created by exporter
```

The exporter searches **recursively** for `results/annotated_correlations/**/*_annotated.csv`. For each CSV it writes a `.ttl` file under `results/turtle/`, using the same relative subdirectory and filename stem. For example:

```text
results/annotated_correlations/Significant_Transcriptomics_Metabolomics_annotated.csv
    → results/turtle/Significant_Transcriptomics_Metabolomics_annotated.ttl
```

Each Turtle file has its **own fresh RDF graph**. Associations from different CSVs are not mixed. Association URIs are derived from the source file path and row index to keep observations distinct if Turtle files are later combined in a triple store.

## Run

From the project root:

```bash
python export_omics_turtle_separate.py
```

Only correlations whose two features share at least one mapped pathway:

```bash
python export_omics_turtle_separate.py --only-shared
```

Only rows with adjusted p-value **≤ 0.05**:

```bash
python export_omics_turtle_separate.py --max-padj 0.05
```

Apply both filters:

```bash
python export_omics_turtle_separate.py --only-shared --max-padj 0.05
```

Use a different project or output directory:

```bash
python export_omics_turtle_separate.py --project-dir /path/to/project --output-dir /path/to/turtle
```

Specify a stable namespace for publication:

```bash
python export_omics_turtle_separate.py --base-uri https://your-domain.org/arabidopsis-heat-stress/
```

### CLI options

| Option | Default | Description |
|---|---|---|
| `--project-dir PATH` | Directory containing exporter | Project root containing `results/` |
| `--output-dir PATH` | `PROJECT/results/turtle` | Directory for generated Turtle files |
| `--base-uri URI` | `https://example.org/arabidopsis-heat-stress/` | Namespace for local RDF resources; must start with `http://` or `https://` |
| `--only-shared` | Off | Keep rows only when the two mapped pathway sets intersect |
| `--max-padj FLOAT` | Unset | Keep rows with numeric `padj` ≤ threshold, between 0 and 1; missing/non-numeric `padj` values are excluded when filtering |

## Input CSV format

The required columns in **each annotated CSV** are:

| Column | Purpose |
|---|---|
| `Feature_1` | Original first feature name/identifier |
| `Feature_2` | Original second feature name/identifier |
| `Omics_Comparison` | Determines transcript/protein/metabolite types |
| `Feature1_mapped_pathway` | Semicolon- or comma-separated PlantCyc pathway IDs for feature 1 |
| `Feature2_mapped_pathway` | Pathway IDs for feature 2 |

Optional columns, exported if present and valid:

| Column | RDF content |
|---|---|
| `Pearson_r` | `study:pearsonR` |
| `Spearman_rho` | `study:spearmanRho` |
| `p_value` | `study:pValue` |
| `padj` | `study:adjustedPValue` |
| `n_samples` | `study:nSamples` |
| `Feature1_mapping_tier` | Fallback tier if detailed provenance is unavailable |
| `Feature2_mapping_tier` | Fallback tier for feature 2 |

Non-finite, empty, and non-numeric statistics are omitted. The exporter **recomputes** `same`, `different`, or `not_comparable` from the actual pathway columns rather than trusting an existing `pathway_relationship` field.

The `Omics_Comparison` text is recognized by matching both relevant terms, e.g. transcript/proteom, transcript/metabolom, or proteom/metabolom. Unrecognized comparisons are typed as generic features.

### Optional mapping provenance

The exporter attempts to read:

`results/mapping_tables/mapping_provenance.csv`

Required columns (if the file exists):

```text
file,row_number,feature_side,plantcyc_id,tier,via
```

Entries are matched using the **original input CSV filename** (inferred by removing `_annotated`), original 1-based CSV line number including header (`index + 2`), feature side (1 or 2), and pathway ID. An unambiguous source filename is required for matching. If detailed provenance is missing or cannot be matched, the exporter uses `Feature1_mapping_tier` / `Feature2_mapping_tier` from the annotated CSV where available. The console reports `missing_provenance` as the number of pathway assignments without matched detailed provenance, not the number of rows.

## RDF model

Each selected row creates one `study:OmicsAssociation` linked to:

- `study:feature1` and `study:feature2`: `study:OmicsFeature` nodes, with original `rdfs:label` and omics type.
- `study:hasEvidence`: a `study:CorrelationEvidence` node containing available numeric statistics.
- `study:hasPathwayAssignment`: `study:PathwayAssignment` nodes linking a particular feature to a PlantCyc pathway with its feature side and mapping evidence.
- `study:supportedBySharedPathway`: links to PlantCyc identifiers **only when both feature pathway sets contain the same ID**.
- `prov:wasDerivedFrom`: a dataset resource identifying the source annotated CSV.

`study:sourceRowNumber` records the original CSV line number including the header. Local association, evidence, and assignment URIs contain deterministic hash fragments based on the source path and row index.

### Identifiers and RDF vocabulary

- Local resources and predicates use the namespace supplied by `--base-uri` (prefix `study:`).
- PlantCyc pathway URIs: `https://identifiers.org/plantcyc/{ID}`.
- Transcript features with recognizable AGI loci may have `skos:closeMatch` links to `https://identifiers.org/tair.locus/{AGI}`.
- Protein features that are themselves UniProt accession strings may have `skos:closeMatch` links to `https://identifiers.org/uniprot/{accession}`. Protein features that are AGI identifiers may instead have TAIR locus links.
- Metabolite features receive an external InChIKey link **only if the original feature label itself is a valid full InChIKey**. The exporter does not infer a metabolite InChIKey from the separate BioCyc file.
- `prov:`, `dcterms:`, `skos:`, `rdfs:`, `rdf:`, and `xsd:` provide standard predicates and data types.

External identifier links use `skos:closeMatch`, **not** `owl:sameAs`: a transcript measurement, protein feature, or metabolite feature is not necessarily identical to the external database entity.

### Example Turtle (illustrative)

```turtle
@prefix study: <https://example.org/arabidopsis-heat-stress/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

study:association/example123
    a study:OmicsAssociation ;
    study:feature1 study:feature/transcript/exampleGene ;
    study:feature2 study:feature/metabolite/exampleMet ;
    study:pathwayRelationship "same" ;
    study:supportedBySharedPathway
        <https://identifiers.org/plantcyc/PWY-1234> ;
    study:hasEvidence study:evidence/example123 .

study:evidence/example123
    a study:CorrelationEvidence ;
    study:pearsonR "0.85"^^xsd:double ;
    study:adjustedPValue "0.01"^^xsd:double .
```

This is a schematic example; the actual exporter generates hash-based resource identifiers and additional statements.

## Pathway relationship logic

| Relationship | Condition |
|---|---|
| `same` | Both features share at least one PlantCyc pathway ID |
| `different` | Both have nonempty pathway sets, but the intersection is empty |
| `not_comparable` | One or both features have no mapped pathways |

Pathway co-annotation is **not** evidence of a direct molecular interaction or causal relationship.

## Validation and console output

After writing each `.ttl` file, the exporter **parses it again using RDFLib**, which checks Turtle syntax. It reports, for each input file:

- `input_rows`: number of CSV data rows read;
- `exported_associations`: rows that passed filters;
- `shared_associations`: exported rows with one or more shared pathway IDs;
- `pathway_assignments`: feature-to-pathway assignment resources created;
- `missing_provenance`: assignment resources without matched detailed evidence;
- `triples`: statements in the parsed output graph.

If a CSV has no rows passing the filters, it can still produce a valid Turtle file containing only dataset/class declarations.

## Troubleshooting

**No input files:** Confirm the files are under `results/annotated_correlations/` and their names end with `_annotated.csv`.

**Missing required columns:** Run the pathway mapping script first, then check the required column names in the annotated CSVs.

**`missing_provenance` is high:** Check `mapping_provenance.csv`, especially `file` values, row numbers and whether different input directories contain files with identical basenames. The fallback tier can still be exported without detailed `via` evidence.

**No associations exported:** Remove `--only-shared` or increase/remove `--max-padj`, and inspect the pathway columns and adjusted p-values.

**No shared-pathway links:** Shared links are added only for exact PlantCyc ID intersections. A correlation may still have two separate pathway assignments and be classified `different`.

**Published identifiers point to `example.org`:** Pass `--base-uri` with a persistent namespace controlled by your project before publishing.

## Limitations

1. The default `study:` classes and predicates are a **local study vocabulary**, not a formally published ontology. Define/document it before public reuse.
2. The script does not independently validate whether a PlantCyc pathway assignment is biologically correct; it exports mapping results already present in the CSVs.
3. The exporter does not query external services or enrich missing mappings.
4. Protein isoform accessions may be normalized for the external identifier link; the original feature label is still preserved.
5. Feature nodes are reusable for equal feature type + label within an RDF graph, but **associations remain distinct per CSV row**.
6. The exporter does not copy all arbitrary source CSV columns into RDF; it exports the documented feature, mapping, and statistics fields.

## Relationship to the mapping pipeline

Run `map_omics_to_plantmetwiki.py` first. That script resolves feature-to-pathway annotations and produces the annotated correlation CSVs and provenance file. Run this exporter second to create independent Turtle graphs suitable for RDFLib, SPARQL tools, and triple stores.

Original MEANtools community reference: [match_meantools.py](https://github.com/pathway-lod/lod-pathways-community/blob/main/pilots/pairedomics_overlap/match_meantools.py).
