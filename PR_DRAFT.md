# Proposed pull request

**Title:** Add evidence-aware falcarindiol pilot with multi-omics provenance and SHACL tests

## Summary

Adds a reviewable, standalone pilot for turning biological pathway knowledge in Jeon et al. (Cell 2020) into claim-level RDF, integrating literature genetic/biochemical support with separate qualitative and synthetic multi-omics analyses. Demonstrates SPARQL competency questions, SHACL validations, provenance, and distinction between confirmed reaction and a proposed CER1-like function.

## Why

The community specification already supports aligning plant pathways and evidence. This pilot tests gaps around expression modules, lagged gene–metabolite associations, temporal units, statistical metadata, evidence dependence and provenance without forcing custom terms into the existing source-of-truth CSV before community review.

## Proposed file changes

- New `pilots/falcarindiol_evidence/` with paper example, explicitly non-empirical teaching scenarios, ontology, SHACL, SPARQL queries, executable tests.
- New `specification/proposals/falcarindiol-omics-evidence.md` containing candidate requirements and eight competency questions.
- New `docs/evidence-aware-pathway-curation.md` summarizing nine related learning modules and worked exercises.
- New optional isolated GitHub Actions workflow validating the pilot.

## Scientific guardrails

- No invented numerical results are attributed to the paper or to the user's experimental analyses.
- Gene 270 pathway involvement and proposed CER1-like catalytic function are separately modeled.
- Correlation and lag findings retain method, sign convention, datasets and analysis links; not proof of enzyme function.
- Proposed local terms are placeholders pending reconciliation with `ontology_terms.csv` and `lodp:`.

## Checks

- RDF and SHACL Turtle parsing using RDFLib.
- SPARQL competency query execution.
- Unit tests for key evidence and status distinctions.
- pySHACL positive and negative validation (to be verified on GitHub Actions).

## Review requested

1. Confirm that this pilot fits the existing use-case taxonomy and chosen terms.
2. Review publication-derived statements and source figures/supplements.
3. Approve or revise the candidate terminology, especially lag/time-unit semantics.
4. Decide whether this should feed the existing `TX` / `COM` use cases or stay as a separate worked pilot.
5. Assess how to connect a GPML2021 diagram and real MATE outputs after schema review.
