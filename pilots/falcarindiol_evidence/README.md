# Falcarindiol evidence-aware pathway pilot

**Proposed pilot for the `pathway-lod/lod-pathways-community` BioHackathon Project 3 workflow.**

This pilot demonstrates representation and validation of multiple kinds of evidence for a single plant specialized-metabolism pathway. It is a reference example for community discussion, **not** a final ontology standard or a complete validated pathway reconstruction.

## Scientific scope

Reference: Jeon et al., *A Pathogen-Responsive Gene Cluster for Highly Modified Fatty Acids in Tomato*, *Cell* (2020). https://doi.org/10.1016/j.cell.2019.11.037

The reported chromosome 12 biosynthetic gene cluster contains Solyc12g100240, Solyc12g100250, Solyc12g100260, and Solyc12g100270. ACET1a/ACET1b have evidence for the linoleic acid to crepenynic acid conversion. Genetic perturbation supports Solyc12g100270 involvement in falcarindiol production, whereas its precise CER1-like catalytic activity remains unconfirmed. This teaching model is intentionally a simplified subset and must be curated against the original figures and supplements before publication.

## Data separation and evidence status

| File | Status | Interpretation |
|---|---|---|
| `data/published.ttl` | Publication-derived subset; curator review still required | Paper claims, BGC membership, defined conversion, proposed function |
| `data/exploratory_scenario.ttl` | **Unverified qualitative scenario** | Weak module affinity and lag observation described during teaching, no asserted statistics |
| `data/synthetic_statistics.ttl` | **Synthetic demonstration ONLY** | Fake correlations, p-values, sample counts and time shift to test SHACL/SPARQL |
| `data/broken_additions.ttl` | **Intentionally invalid synthetic record** | Negative quality-control example |
| `diagram/falcarindiol_teaching.gpml` | **Teaching diagram, not XSD-certified** | Simplified visualization |

Please do not infer that `0.78` or `24 h` are values reported by Jeon et al. or derived from measured MATE output. No empirical correlation table was provided for this pilot.

## Quick start

```bash
python -m pip install -r requirements.txt
python scripts/run.py stats
python scripts/run.py query supported_genes
python scripts/run.py query evidence_and_claims
python scripts/run.py query qualitative_scenario
python scripts/run.py query lagged_findings
python scripts/run.py query missing_labels
python scripts/run.py gpml-check
python scripts/run.py validate
python scripts/run.py validate --broken  # should fail with exit code 1
python -m unittest discover -s tests -v
```

`pySHACL` is required for the `validate` commands. All graphs are loaded as explicitly asserted triples and validated with `inference='none'` to avoid inadvertently hiding incorrect type assertions through RDFS domain/range inference.

## Modeling pattern

1. Biological resources: genes, proteins, metabolites, pathways, chromosome BGC and reactions.
2. Scientific claims: gene–pathway association, characterized reaction claim, hypothesized catalytic role.
3. Evidence: biochemical, genetic and computational observations.
4. Computational findings: expression-module affinity, qualitative lag finding, numerical lag measurement.
5. Provenance: `dcterms:source`, `prov:wasDerivedFrom`, `prov:wasGeneratedBy`, `prov:used`.
6. Validation: claim shapes, evidence-provenance checks, statistical bound checks, lag magnitude/unit, and deliberately broken records.

Use `demo:` only as a temporary identifier system. The canonical specification is `specification/ontology_terms.csv`, while unresolved terms should be handled through `shape_constraints/vocab/lodp.ttl` and the repository's issue/dashboard workflow. Do not assert `owl:equivalentClass` or reuse existing identifier prefixes without semantic review.

## Data-quality principles

- `rdfs:domain` / `rdfs:range` support inference, not data rejection; use SHACL for explicit completeness requirements.
- `rdf:type` inference does not verify a gene's experimental function.
- An enzyme knockout phenotype can support pathway involvement without identifying the catalyzed reaction.
- A non-detection in a heterologous system is not proof of absent enzymatic function.
- Lagged correlation is an analysis result, not a causal or catalytic edge.
- Different types of evidence derived from the same samples should not be scored as statistically independent.
- A lag in sampling steps or pseudotime is not necessarily a lag in hours.
- Treat statistical significance after a lag search with appropriate multiple-testing and repeated-measures methodology.

The GPML command checks XML well-formedness and internal IDs only; it is **not** a substitute for GPML2021 XSD validation or a PathVisio round-trip.

## Reviewer checklist before adopting this into main

- Check exact paper figures and supplementary materials; add source locators to claims after verification.
- Map all genes to genome assembly and annotation release; verify gene 240/260 mapping with the study's short-read ambiguity caveat.
- Verify compound structures and canonical identifiers; avoid name-only chemical cross-references for production use.
- Reconcile proposed classes/properties with the project's existing controlled terms.
- Replace example.org IRIs with the project's canonical IRI policy.
- Add GPML2021 representation and validate against the published XSD and the repo's existing pipeline before linking graphical nodes.
- Replace preliminary scenarios with actual analysis outputs, metadata and measured statistics if these become available.
- Add license/version, frozen inputs, CI checks and release DOI when releasing the resource.
