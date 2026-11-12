# Proposed ontology registry additions — falcarindiol evidence-aware pathway pilot

This is **review material**, not an update to the community's authoritative ontology_terms.csv. The original uploaded CSV has 188 rows and the merged review copy has 223. The append-only candidate file contains 35 proposed rows (T198–T232). All new decisions remain `open`; external ontology mappings, IRI ontology types and labels should be checked by the project validator and maintainers before merging. The existing `https://example.org/lod-pathways/pilot/` URI is a placeholder that must not become a permanent community namespace without review.

## Highest-priority decisions

1. **Assertion representation:** Existing COM-11 already has `rdf:Statement`, COM-01 has SIO has-evidence, and COM-01 also considers SEPIO. Decide on RDF reification vs an explicit SEPIO claim/proposition model before introducing more local terms. The RDF reification triplet alone does not assert a biological fact.
2. **Claim versus evidence:** add source locator, derivation, curator association, claim status, mutant phenotype evidence, enzyme assay evidence, and evidence assessments. Genetic support for pathway involvement cannot be converted into confirmation of a specific enzyme-catalysed reaction.
3. **Time-lag evidence:** define lag finding, direction, time-axis convention, quantity/unit, zero-lag vs best-lag statistics, and effective aligned pair counts. No values from synthetic tutorials should enter curated evidence datasets.
4. **Module-specific evidence:** distinguish BGC membership (already BGC-01/02) from expression-module membership and weak module affinity; a clustering result is analysis dependent.
5. **Reproducibility:** use existing PROV `prov:used` for transcriptomics, metabolomics, and alignment manifests; enrich SHACL rather than creating duplicate provenance predicates.

## Already in the original CSV; do not duplicate

- `SO:0002357` biosynthetic gene cluster, `BFO:0000051` has part (BGC-01/02), plus `lodp:genomeAssembly` (BGC-16).
- `SIO:001257` chemical-gene association (PO-01); `STATO:0000280` Pearson and `STATO:0000201` Spearman (PO-04, TX-14); p-values (PO-05, TX-12).
- `lodp:functionalCluster` for gene-metabolite modules (PO-08), `INO:0000231` co-expression (TX-15), `lodp:mutualRank` (PO-06 and TX-16).
- `prov:wasGeneratedBy`, `prov:used`, software version metadata (COM-03/04/05).
- `ECO:0000000` evidence, SIO `has evidence` (COM-01/02).

## Representation warning

Several registry terms are listed as `element_type=property` although they appear to describe ontology classes (e.g. STATO Pearson coefficient and OBI p-value). **Audit class vs datatype/object property IRIs** in the authoritative ontology before using such identifiers as RDF predicates or in SHACL `sh:path`. For a practical RDF profile, use an explicit local data property for the numeric value (or a typed statistic result node), and use the existing ontology class as the type of the statistic.

## Suggested SHACL tests

- `claim`: exactly one subject/predicate/object or explicit proposition structure, evidence at the claim level, supported status must be backed by appropriate evidence type.
- `quantified lag`: exactly one gene/metabolite, Pearson r in [-1,1], bestLagCorrelation r in [-1,1], adjusted p in [0,1] (if reported), alignedPairCount >=3, a declared sign convention, a time-axis choice, lag >0 with unit for a nonzero lag.
- `modules`: module membership references an ExpressionModule or existing functionalCluster; affinity score has a metric and analysis provenance, and weak affinity does not assert module membership.
- `BGC`: positions are on the specified assembly; start and end ordered; do not invent coordinates missing in the source.
- `provenance`: every computed finding links to a run, its input dataset(s), and curation status; synthetic test data must not be serialized as verified results.

## Next governance steps

Review P1 rows first, decide on whether SEPIO is needed, run `check_terms.py` against all reused terms and correct class/property type mismatches, mint stable `lodp:` IRIs only after review, and create focused SHACL tests for the adopted requirements. The P2 graphical mapping and coordinates can follow in a separate PR.
