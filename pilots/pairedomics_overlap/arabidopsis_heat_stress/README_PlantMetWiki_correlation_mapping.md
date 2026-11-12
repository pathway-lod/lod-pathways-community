# Arabidopsis Multi-Omics Pathway Mapping

Mapping transcriptomics, proteomics, and metabolomics features to **PlantCyc pathway identifiers** using PlantMetWiki, UniProt, and BioCyc.

This workflow was developed for *Arabidopsis thaliana* heat-stress multi-omics correlation analysis.

The pipeline annotates significant correlations with pathway associations and identifies whether two correlated molecular features belong to at least one common pathway.

## 1. Overview

The script `map_omics_to_plantmetwiki.py` supports three omics comparisons:

- Transcriptomics vs. Proteomics
- Transcriptomics vs. Metabolomics
- Proteomics vs. Metabolomics

Each feature is mapped independently to one or more PlantCyc pathways.

The mapping follows a **hierarchical evidence strategy**.

**Important:** The pipeline stops at the first successful mapping tier for each feature. If a higher-priority tier produces at least one pathway, lower-priority tiers are not used.

All pathways obtained at the successful tier are retained.

The pipeline also:

- Preserves original correlation feature names.
- Preserves all original correlation columns.
- Does not multiply correlation rows.
- Supports multiple pathways per feature.
- Records mapping evidence and provenance.
- Separates exact identifier evidence from indirect functional evidence.
- Uses cached external query results.
- Detects potentially truncated SPARQL responses.
- Produces mapping coverage and metabolite diagnostics.

---

## 2. Data Sources

### 2.1 PlantMetWiki

PlantMetWiki provides pathway information, GPML element properties, and RDF relationships.

SPARQL endpoint:

https://plantmetwiki.bioinformatics.nl/sparql

The script uses PlantMetWiki to retrieve:

- Pathway identifiers
- Pathway names
- AGI locus identifiers
- UniProt identifiers
- EC numbers
- Metabolite InChIKeys
- Metabolite-to-pathway associations

### 2.2 PlantCyc

PlantCyc provides the pathway identifiers used in the final output.

A PlantMetWiki internal pathway code, such as `PC123`, is not automatically equivalent to a PlantCyc pathway identifier.

The pipeline retrieves a pathway catalogue that links internal `PC` identifiers to PlantCyc identifiers.

This ensures that gene, protein, and metabolite pathway assignments use the same pathway identifier system.

### 2.3 UniProt

UniProt provides protein annotations and mappings between Arabidopsis genes, protein accessions, and enzyme functions.

REST API:

https://rest.uniprot.org/

Organism:

- Species: Arabidopsis thaliana
- NCBI taxonomy ID: 3702

The pipeline retrieves:

- UniProt accession
- Reviewed status
- Protein name
- Gene names
- Ordered locus names
- TAIR cross-references
- EnsemblPlants cross-references
- Araport cross-references
- EC numbers

These identifiers are used to connect transcripts and proteins to pathway annotations.

### 2.4 BioCyc

BioCyc is used as the source of metabolite identifier annotations.

The input file `metabolomics_biocyc.csv` contains metabolite names and InChIKeys.

The pipeline connects these InChIKeys to pathway memberships retrieved from PlantMetWiki.

---

## 3. Requirements

### Python

Python 3.10 or newer is recommended.

### Dependencies

Install:

```bash
pip install pandas requests
```

The script uses standard Python libraries including:

- argparse
- collections
- io
- pathlib
- re
- time

No additional Python packages are required.

An internet connection is required for initial UniProt and PlantMetWiki queries.

---

## 4. Project Structure

The expected directory structure is:

```text
arabidopsis_heat_stress/
│
├── map_omics_to_plantmetwiki.py
│
├── input/
│   ├── Significant_Transcriptomics_Proteomics.csv
│   ├── Significant_Transcriptomics_Metabolomics.csv
│   └── Significant_Proteomics_Metabolomics.csv
│
└── results/
    └── metabolomics_biocyc.csv
```

The script recursively searches the `input/` directory for:

```text
Significant_*.csv
```

After execution, it creates:

```text
results/
│
├── metabolomics_biocyc.csv
│
├── annotated_correlations/
│   └── *_annotated.csv
│
└── mapping_tables/
    ├── plantcyc_pathway_catalog.csv
    ├── gpml_properties_parsed.csv
    ├── gpml_identifier_evidence.csv
    ├── uniprot_species_mapping.csv
    ├── rdf_metabolite_memberships.csv
    ├── gpml_metabolite_memberships.csv
    ├── metabolite_pathway_memberships.csv
    ├── metabolite_inchikey_mapping.csv
    ├── metabolite_mapping_diagnostics.csv
    ├── mapping_provenance.csv
    └── mapping_coverage.csv
```

Additional cached CSV files are stored in `mapping_tables/`.

---

## 5. Input Data

### 5.1 Correlation CSV Files

Each significant correlation table must contain:

| Column | Description |
|---|---|
| Feature_1 | First molecular feature |
| Feature_2 | Second molecular feature |
| Omics_Comparison | Type of omics comparison |
| p_value | Correlation p-value |
| padj | Adjusted p-value |
| n_samples | Number of samples |

At least one correlation coefficient column is required:

- `Pearson_r`
- `Spearman_rho`

Other columns are preserved.

The script expects feature positions to follow these conventions:

| Omics comparison | Feature_1 | Feature_2 |
|---|---|---|
| Transcriptomics–Proteomics | Transcript | Protein |
| Transcriptomics–Metabolomics | Transcript | Metabolite |
| Proteomics–Metabolomics | Protein | Metabolite |

Transcript identifiers should contain Arabidopsis AGI locus identifiers.

Example:

```text
AT1G01010
AT2G34560.1
```

Transcript isoform suffixes do not change the locus-level identifier used for pathway matching.

Protein identifiers should contain UniProt accessions or, when applicable, AGI locus identifiers.

### 5.2 BioCyc Metabolite File

Required file:

```text
results/metabolomics_biocyc.csv
```

Required columns:

| Column | Description |
|---|---|
| Query | Original metabolite name |
| InChiKey | Metabolite structural identifier |

Example:

```csv
Query,InChiKey
Glucose,WQZGKKKJIJFFOK-GASJEMHNSA-N
L-Glutamic acid,WHUUTDBJXJRKMK-VKHMYHEASA-N
```

The original `Query` values are preserved.

For name matching, the script creates an internal normalized lookup key by:

- Converting to lowercase
- Replacing underscores and hyphens with spaces
- Removing selected punctuation
- Collapsing repeated whitespace

Normalization is used only for lookup and does not replace original metabolite names.

---

## 6. Mapping Strategy

The workflow implements hierarchical feature-to-pathway resolution.

Each omics type has its own evidence priorities.

### 6.1 Transcript Mapping

Transcripts are mapped through three ordered tiers.

#### Tier 1: Direct AGI Locus Mapping

```text
Transcript
    |
    v
AGI locus
    |
    v
PlantMetWiki GPML gene identifier
    |
    v
PlantCyc pathway
```

The script extracts an AGI identifier from the transcript feature.

Example:

```text
AT1G01010.1 -> AT1G01010
```

It searches direct GPML gene identifier annotations.

If one or more pathways are found, mapping stops.

#### Tier 2: AGI to UniProt to Pathway

Used only if Tier 1 returns no pathways.

```text
AGI locus
    |
    v
UniProt accession
    |
    v
PlantMetWiki GPML UniProt identifier
    |
    v
PlantCyc pathway
```

UniProt gene cross-references provide associations between AGI loci and protein accessions.

The pipeline then searches direct UniProt pathway annotations.

If pathways are found, mapping stops.

#### Tier 3: AGI to UniProt to EC to Pathway

Used only when Tiers 1 and 2 fail.

```text
AGI locus
    |
    v
UniProt accession
    |
    v
EC number
    |
    v
PlantMetWiki EC annotation
    |
    v
PlantCyc pathway
```

This tier uses enzyme function as indirect pathway evidence.

EC-based mapping is less specific than direct locus or protein identifier mapping.

An EC number can be associated with several pathways.

#### Transcript Priority Summary

| Tier | Route | Evidence |
|---|---|---|
| 1 | AGI → Pathway | Direct locus |
| 2 | AGI → UniProt → Pathway | Protein identifier |
| 3 | AGI → UniProt → EC → Pathway | Functional |

Only the first successful tier contributes final pathway IDs.

---

### 6.2 Protein Mapping

Protein mapping uses three tiers.

This version includes an additional **UniProt → AGI → pathway** fallback to improve coverage.

#### Tier 1: Direct UniProt Mapping

```text
UniProt accession
    |
    v
PlantMetWiki GPML UniProt identifier
    |
    v
PlantCyc pathway
```

If a direct UniProt pathway association is available, it is used.

No lower-tier mappings are attempted.

Evidence label:

```text
protein_direct
```

#### Tier 2: UniProt to AGI to Pathway

Used only if Tier 1 fails.

```text
UniProt accession
    |
    v
AGI locus
    |
    v
PlantMetWiki GPML gene identifier
    |
    v
PlantCyc pathway
```

This is useful when a pathway contains an AGI identifier but no UniProt identifier.

The script builds bidirectional mappings:

```text
AGI -> UniProt
UniProt -> AGI
```

The mappings are derived from UniProt annotations, including:

- TAIR
- EnsemblPlants
- Araport
- Ordered locus names
- Gene names

Evidence label:

```text
protein_gene_locus
```

#### Tier 3: UniProt to EC to Pathway

Used only if Tiers 1 and 2 fail.

```text
UniProt accession
    |
    v
EC number
    |
    v
PlantMetWiki enzyme annotation
    |
    v
PlantCyc pathway
```

Evidence label:

```text
protein_ec
```

EC numbers describe enzyme activity and may occur in multiple pathways.

Consequently, this tier is considered indirect functional evidence.

#### Protein Priority Summary

| Tier | Route | Evidence |
|---|---|---|
| 1 | UniProt → Pathway | Direct protein |
| 2 | UniProt → AGI → Pathway | Gene locus |
| 3 | UniProt → EC → Pathway | Functional |

**Important:** The additional protein Tier 2 improves coverage while preserving identifier-based mapping.

---

### 6.3 Metabolite Mapping

Metabolites are mapped using InChIKeys.

Two independent PlantMetWiki data sources are combined:

1. RDF metabolite-to-pathway relationships
2. GPML `InchiKey` properties

The resulting mappings are then matched against BioCyc InChIKeys.

#### Tier 1: Full InChIKey

The first matching attempt uses the complete InChIKey.

Example:

```text
AAAAAAAAAAAAAA-BBBBBBBBBB-C
```

If a pathway is found, the mapping stops.

Evidence label:

```text
metabolite_exact_inchikey
```

#### Tier 2: InChIKey Connectivity Block

If there is no full InChIKey pathway match, the script attempts a match using the first 14 characters.

Example:

```text
AAAAAAAAAAAAAA-BBBBBBBBBB-C
AAAAAAAAAAAAAA-DDDDDDDDDD-E
```

Both share:

```text
AAAAAAAAAAAAAA
```

The first block represents molecular connectivity.

This fallback can recover pathway associations when stereochemistry, protonation, or related structural distinctions differ between databases.

Evidence label:

```text
metabolite_connectivity
```

A connectivity match is less specific than a full InChIKey match.

It should not be interpreted as proof that the complete chemical structures are identical.

#### Metabolite Priority Summary

| Tier | Route | Evidence |
|---|---|---|
| 1 | Full InChIKey → Pathway | Exact structure identifier |
| 2 | First 14 characters → Pathway | Connectivity |

To disable connectivity matching, use:

```bash
python map_omics_to_plantmetwiki.py --exact-inchikey
```

---

## 7. PlantMetWiki SPARQL Queries

The script retrieves several types of information.

### 7.1 Pathway Catalogue

The pathway catalogue connects internal PlantMetWiki `PC` identifiers to PlantCyc IDs.

Conceptually:

```text
PC identifier -> PlantCyc identifier
```

This prevents inconsistent pathway identifiers across omics types.

### 7.2 GPML Properties

The GPML property query retrieves identifiers associated with pathway elements.

Supported identifier categories include:

- AGI and TAIR gene identifiers
- UniProt identifiers
- EC numbers
- InChIKeys

### 7.3 RDF Metabolite Membership

The RDF query retrieves metabolite-to-pathway relationships.

It uses:

```sparql
?m a wp:Metabolite ;
   wp:bdbInChIKey ?ik ;
   dcterms:isPartOf ?pw .
```

The linked pathway is required to have a PlantCyc identifier.

### 7.4 GPML Metabolite Membership

The pipeline also extracts InChIKeys from GPML properties.

This serves as a complementary source when RDF metabolite membership is incomplete.

### 7.5 Query Partitioning

Some PlantMetWiki queries may return approximately 10,000 rows because of endpoint result limits.

The script detects suspiciously large responses and recursively divides the queries.

GPML property queries are partitioned by `PC` pathway prefixes.

Metabolite queries are partitioned by InChIKey prefixes.

The threshold is configured using:

```python
SPARQL_LIMIT_WARNING = 9500
```

A response near this threshold is treated as potentially truncated.

The script attempts smaller queries rather than silently accepting incomplete results.

Partitioning is a safeguard; it does not independently guarantee endpoint completeness.

---

## 8. Running the Pipeline

### Standard execution

From the project directory:

```bash
python map_omics_to_plantmetwiki.py
```

### Refresh external data

```bash
python map_omics_to_plantmetwiki.py --refresh
```

This re-runs the external UniProt and PlantMetWiki queries instead of reusing cached responses.

### Strict metabolite matching

```bash
python map_omics_to_plantmetwiki.py --exact-inchikey
```

This disables the 14-character InChIKey fallback.

### Refresh and exact InChIKey matching

```bash
python map_omics_to_plantmetwiki.py --refresh --exact-inchikey
```

### Specify a project directory

```bash
python map_omics_to_plantmetwiki.py \
    --project-dir /path/to/arabidopsis_heat_stress
```

On Windows PowerShell:

```powershell
python map_omics_to_plantmetwiki.py --refresh
```

---

## 9. Output Files

### 9.1 Annotated Correlation Files

Location:

```text
results/annotated_correlations/
```

Each original correlation file produces an annotated CSV.

The following columns are added:

| Column | Description |
|---|---|
| Feature1_mapped_pathway | PlantCyc pathways for Feature_1 |
| Feature2_mapped_pathway | PlantCyc pathways for Feature_2 |
| shared_pathway_ids | Pathways shared by both features |
| pathway_relationship | Same, different, or not comparable |
| Feature1_mapping_tier | Selected evidence tier for Feature_1 |
| Feature2_mapping_tier | Selected evidence tier for Feature_2 |
| pathway_mapping_status | Whether both, one, or neither feature mapped |

Multiple pathway IDs are stored as semicolon-separated values.

The script does not expand multiple pathway associations into additional correlation rows.

### 9.2 Pathway Relationship

Possible values:

| Value | Meaning |
|---|---|
| same | The two features share at least one pathway |
| different | Both have pathway mappings but share none |
| not_comparable | At least one feature has no pathway mapping |

In case biological feature is mapped to more than 1 pathway, all pathways are listed, and the comparison of sets of asssociated IDs is performed between features.

A shared pathway does not necessarily imply a direct molecular interaction.

### 9.3 Mapping Status

Possible values:

| Value | Meaning |
|---|---|
| both_mapped | Both features have pathway assignments |
| feature1_only | Only Feature_1 mapped |
| feature2_only | Only Feature_2 mapped |
| neither_mapped | Neither feature mapped |
| unknown_comparison | Omics comparison type was not recognized |

---

## 10. Mapping Tables

All mapping tables are stored in:

```text
results/mapping_tables/
```

### plantcyc_pathway_catalog.csv

Contains internal PlantMetWiki pathway codes and corresponding PlantCyc identifiers.

### gpml_properties_parsed.csv

Contains GPML properties retrieved from PlantMetWiki.

### gpml_identifier_evidence.csv

Contains gene, protein, and EC identifier evidence extracted from GPML.

### uniprot_species_mapping.csv

Contains Arabidopsis UniProt mappings, including:

```text
uniprot_id
gene_id
ec_number
```

These relationships are used in both transcript and protein mapping.

### rdf_metabolite_memberships.csv

Contains metabolite-to-pathway associations derived from RDF relationships.

### gpml_metabolite_memberships.csv

Contains metabolite-to-pathway associations extracted from GPML InChIKey properties.

### metabolite_pathway_memberships.csv

Combines RDF and GPML metabolite pathway evidence.

### metabolite_inchikey_mapping.csv

Contains the original BioCyc metabolite queries and InChIKeys.

### metabolite_mapping_diagnostics.csv

Reports metabolite matching results and selected evidence tiers.

Possible labels:

```text
exact_inchikey
connectivity_14
missing_biocyc_inchikey
not_in_plantmetwiki
```

### mapping_provenance.csv

Provides detailed feature-to-pathway evidence.

Columns include:

| Column | Description |
|---|---|
| file | Source correlation file |
| row_number | Source CSV row number |
| feature_side | Feature_1 or Feature_2 |
| feature_original | Original feature identifier |
| plantcyc_id | Assigned PlantCyc pathway |
| tier | Selected mapping evidence |
| via | Identifier or evidence route |
| is_shared | Whether the pathway is shared |

This file is particularly important for reviewing indirect EC-based mappings.

### mapping_coverage.csv

Summarizes pathway relationship counts for each annotated correlation file.

It contains the number of rows and counts for relationship categories such as:

```text
same
different
not_comparable
```

---

## 11. Evidence Interpretation

Mapping evidence should be interpreted according to its origin.

### Transcript evidence

| Evidence label | Interpretation |
|---|---|
| gene_locus | Direct AGI locus association |
| gene_uniprot | Gene-to-protein identifier mapping |
| gene_ec | Indirect EC functional association |

### Protein evidence

| Evidence label | Interpretation |
|---|---|
| protein_direct | Direct UniProt pathway association |
| protein_gene_locus | UniProt-to-AGI locus association |
| protein_ec | Indirect EC functional association |

### Metabolite evidence

| Evidence label | Interpretation |
|---|---|
| metabolite_exact_inchikey | Complete InChIKey match |
| metabolite_connectivity | First 14 characters match |

**The mapping tier is evidence provenance, not an experimentally validated confidence probability.**

Direct identifier matches and indirect EC-based associations should not be interpreted as equivalent evidence.

---

## 12. UniProt–BioCyc Cross-References

UniProt may provide cross-references to BioCyc database entries.

These cross-references can link a UniProt protein record to a corresponding BioCyc biological entity.

However, a BioCyc cross-reference does not necessarily identify a pathway.

A possible mapping chain is:

```text
UniProt accession
    |
    v
BioCyc gene/protein entry
    |
    v
BioCyc reaction
    |
    v
BioCyc pathway
```

Additional database relationships are required to resolve the pathway.

**The current pipeline does not use UniProt–BioCyc cross-references as an automatic mapping tier.**

This avoids treating database entity identifiers as pathway identifiers without validation.

---

## 13. Troubleshooting

### 13.1 No Transcript Pathways

Check:

1. Whether transcript names contain valid AGI identifiers.
2. Whether GPML gene properties contain the corresponding locus.
3. Whether UniProt provides a locus-to-protein association.
4. Whether the corresponding UniProt accession or EC number maps to a pathway.

Useful files:

```text
gpml_identifier_evidence.csv
uniprot_species_mapping.csv
mapping_provenance.csv
```

### 13.2 No Protein Pathways

Check whether the protein identifier is a valid UniProt accession or AGI locus.

Then inspect the three protein mapping tiers:

```text
protein_direct
protein_gene_locus
protein_ec
```

If direct UniProt mapping fails, the pipeline attempts UniProt-to-AGI mapping.

If that also fails, it attempts EC-based mapping.

Also verify that UniProt returned the expected gene cross-reference columns.

### 13.3 Zero Metabolite Mappings

Check:

```text
rdf_metabolite_memberships.csv
gpml_metabolite_memberships.csv
metabolite_pathway_memberships.csv
metabolite_mapping_diagnostics.csv
```

If the RDF table is empty but the GPML table contains mappings, the pipeline can still use GPML evidence.

If both sources contain mappings but none overlap BioCyc, inspect the InChIKey formats and the first 14 characters.

If BioCyc InChIKeys are missing, pathway matching cannot proceed for those metabolites.

### 13.4 SPARQL Truncation

If a query produces approximately 10,000 rows, the script attempts recursive partitioning.

If an individual partition remains too large, the script raises an exception rather than accepting potentially incomplete data.

### 13.5 Unexpected Results After Code Changes

Run:

```bash
python map_omics_to_plantmetwiki.py --refresh
```

This avoids reuse of previously cached external query responses.

### 13.6 Unknown Omics Comparison

The script recognizes comparison labels containing the relevant omics terms.

Examples:

```text
Transcriptomics_Proteomics
Transcriptomics_Metabolomics
Proteomics_Metabolomics
```

Other labels may be classified as:

```text
unknown_comparison
```

---

## 14. Biological Limitations

Several limitations should be considered when interpreting the output.

### Pathway Coverage

PlantMetWiki may not contain every Arabidopsis gene, protein, or metabolite.

An unmapped feature does not necessarily lack a biological pathway.

### EC Ambiguity

EC numbers describe enzyme activities rather than unique proteins.

The same EC activity can occur in multiple pathways.

Consequently, EC-based mapping may assign several possible pathways to one feature.

### InChIKey Connectivity

The first 14 characters of an InChIKey represent molecular connectivity.

Connectivity matching can increase coverage but may group chemically distinct stereoisomers or protonation forms.

### Gene–Protein Relationships

Some genes encode multiple isoforms or protein products.

The script maps transcript features primarily at AGI locus level.

Protein isoform-specific distinctions are not explicitly modeled.

### Pathway Membership

Pathway co-annotation is not proof of a physical interaction, causal relationship, or shared regulation.

Two features mapped to the same pathway may participate in different reactions or processes.

### Database Updates

PlantMetWiki, PlantCyc, UniProt, and BioCyc annotations can change over time.

For reproducibility, record the query date and preserve the mapping tables used for analysis.

---

## 15. Recommended Quality Control

After each run:

1. Review `mapping_coverage.csv`.
2. Count unique mapped transcripts and proteins.
3. Examine how many mappings use each tier.
4. Review EC-derived mappings separately.
5. Inspect `metabolite_mapping_diagnostics.csv`.
6. Check mappings for a sample of known Arabidopsis genes and proteins.
7. Compare pathway assignments against biological knowledge.

In particular, an increase in mapped features should not automatically be interpreted as improved accuracy.

A more specific identifier-based pathway assignment is generally preferable to a broader functional association.

---

## 16. Reproducibility

For reproducible analyses, retain:

- The Python script version
- Input correlation CSV files
- BioCyc metabolite annotation file
- Cached PlantMetWiki results
- Cached UniProt results
- Generated mapping tables
- Mapping provenance file
- Query execution date

Using `--refresh` may change mapping results if external database content has been updated.

---

## 17. References

### Original pathway-mapping implementation

Pathway LOD Community — MEANtools matching implementation:

https://github.com/pathway-lod/lod-pathways-community/blob/main/pilots/pairedomics_overlap/match_meantools.py

### PlantMetWiki

https://plantmetwiki.bioinformatics.nl/

### UniProt

https://www.uniprot.org/

UniProt REST API:

https://rest.uniprot.org/

### BioCyc

https://biocyc.org/

### PlantCyc

https://plantcyc.org/

### WikiPathways

https://www.wikipathways.org/

---

## 18. Summary

The pipeline integrates transcriptomics, proteomics, and metabolomics pathway annotations for Arabidopsis thaliana.

Its main features are:

- Hierarchical transcript pathway mapping
- Improved protein mapping through AGI loci
- Direct UniProt and indirect EC-based associations
- RDF and GPML metabolite mapping
- Exact and connectivity-based InChIKey matching
- Canonical PlantCyc pathway identifiers
- Automated SPARQL partitioning
- Mapping provenance and diagnostics
- Preservation of original correlation data

The central principle is:

**Use the most specific available evidence and stop at the first successful mapping tier.**

All pathways returned at that tier are retained, while weaker alternatives are excluded from the final feature annotation.
