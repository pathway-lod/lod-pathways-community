# Proposed contribution to `pathway-lod/lod-pathways-community`

Public repository: https://github.com/pathway-lod/lod-pathways-community

Scope: demonstrate a traceable, evidence-aware graph for the tomato falcarindiol pathway, including literature-derived claims, synthetic multi-omics examples, SPARQL competency questions, SHACL checks and a mapping plan for the existing LODP specification.

## Proposed changes

- `pilots/falcarindiol_evidence/`: self-contained pilot with RDF, SHACL, SPARQL, a provisional GPML2021 diagram, tests and worked examples.
- `specification/proposals/falcarindiol-omics-evidence.md`: candidate requirements for specification/ontology_terms.csv *review*, rather than editing that source of truth blindly.
- `docs/evidence-aware-pathway-curation.md`: a concise reference guide consolidating lessons 1–9.
- `.github/workflows/validate-falcarindiol-pilot.yml`: optional CI validation, isolated from existing workflows.

## Important boundaries

- The pilot does not claim new biochemistry or automatic reconstruction.
- The published gene-cluster/ACET1 examples are separate from preliminary analysis scenarios.
- Every quantitative correlation/lag number in the pilot is **synthetic demonstration data**.
- No local vocabulary term in `https://example.org/falcarindiol-demo/` is presented as an approved `lodp:` URI. Resolve these terms against the repository's existing `specification/ontology_terms.csv` and `shape_constraints/vocab/lodp.ttl` before merge.
- The GPML working examples from the teaching handbook are intentionally not bundled: cross-check with the repository's GPML2021 validation and gene/chemical identifier policies before integration.

## Installation and tests

```bash
cd pilots/falcarindiol_evidence
python -m pip install -r requirements.txt
python scripts/run.py stats
python scripts/run.py query supported_genes
python scripts/run.py query lagged_findings
python scripts/run.py validate
python scripts/run.py validate --broken
python -m unittest discover -s tests -v
```

## How to apply

1. Create a feature branch from the current main branch.
2. Copy the contents of this change-set root into the repository root, **without overwriting** any existing paths. Check for collisions and review changes with `git diff`.
3. Run the pilot tests, review the candidate-term mapping with ontology maintainers, and open a PR.
4. The suggested GitHub Actions workflow should be reviewed against current CI conventions before merging.

## Suggested PR title

`Add evidence-aware falcarindiol pilot with multi-omics provenance and SHACL checks`
