# Candidate requirements: evidence-aware falcarindiol curation and temporal multi-omics

**Status: proposal for community discussion. Suggested edits to the approved `ontology_terms.csv`**

This proposal should be reconciled with use cases already included in `specification/SPECIFICATION.md`, notably existing BGC, transcriptomics and combined/multi-omics cases. Reuse established controlled terms first; propose a local `lodp:` placeholder only when a genuine gap remains.

## Competency questions

CQ1. Which genes are in a published biosynthetic gene cluster, and which genes are assigned to an expression module under a stated analysis?

CQ2. Which gene–pathway assertions are supported by genetic perturbation rather than direct enzyme assays?

CQ3. Which proposed enzyme functions have never had their substrate–product conversion characterized?

CQ4. Which transcript–metabolite findings use a positive real-time lag, and what is the sign convention?

CQ5. Which analysis software, normalization, treatment, time points and datasets produced a reported co-expression or lagged finding?

CQ6. Which apparently independent evidence records actually reuse the same input samples?

CQ7. Which biological assertions lack a publication, source locator or other required evidence metadata?

CQ8. Which GPML visual nodes correspond to biological resources without conflating the diagram element with the biological entity?

## Candidate term and validation requirements (for mapping review)

| Requirement | Candidate vocabulary / approach | Missing data policy | Review note |
|---|---|---|---|
| Identify curation event and claim provenance | PROV-O (`prov:Activity`, `prov:used`, `prov:wasGeneratedBy`, `prov:wasDerivedFrom`) | Violation for published curated claim without source | Keep curator distinct from paper author |
| Represent published gene/pathway/reaction entities | WikiPathways ontology + established biological IDs | Violation for unresolved mandatory references | Align with current PlantMetWiki schema |
| Distinguish genetic involvement from biochemical reaction confirmation | Typed claim resources + ECO evidence category | Must never infer catalytic claim from association alone | Candidate design requirement, not new ECO term |
| Identify BGC membership | Existing BGC/RO terms or established project local term | Warning for missing assembly/coordinates | BGC != co-expression module |
| Represent transcript module and membership/affinity | Existing clustering/result vocabulary when available; local placeholder otherwise | Qualitative vs quantified profiles | A single cluster assignment depends on analysis |
| Store gene–metabolite pairwise association | Local association entity with gene/metabolite links | Minimum gene, metabolite, provenance | Edge alone loses coefficients and methods |
| Specify signed-lag convention | Statistical method metadata and explicit direction | Violation for quantified lag without direction | Sampling step != clock time |
| Record lag magnitude and unit | QUDT quantity and unit | Violation for quantitative lag lacking units | Real time vs pseudotime must be separate |
| Encode correlations and adjusted p-values | STATO terms or documented local value predicates | Range [-1,1], [0,1] | State estimator, sample count and search policy |
| Capture sample/treatment alignment and replicate structure | OBI/PROV-O and workflow metadata | Warning or violation according to profile | Essential for interpretable temporal analysis |
| Preserve evidence dependence | Same dataset/analysis links (PROV-O) | Review before aggregating support | Prevent double counting related analyses |
| Validate schema vs biological truth | SHACL + independent scientific curation | Validation alone not enough | Explicit assertion graph for QA |
| Link diagram element to biological resource | Existing GPML-derived RDF mapping | IDs must resolve | Do not use `owl:sameAs` for a visual glyph |

## Suggested acceptance criteria

1. Candidate terms reviewed against `specification/ontology_terms.csv` and current `lodp:` vocabulary, with any duplicate candidates removed.
2. Competency questions represented as SPARQL fixtures with expected results.
3. SHACL tests demonstrate detection of missing provenance, out-of-range correlation and invalid lag metadata.
4. Published observations and hypothetical/synthetic examples remain unmistakably separated.
5. Two independent curators verify each publication-derived claim and source locator before the example is promoted to a validated community reference.
6. At least one second pathway or independent omics dataset exercises the same constraints before declaring the model broadly reusable.

## Future terms to discuss, rather than assume

- `LaggedGeneMetaboliteAssociation` vs generic statistical association with lag metadata.
- `ExpressionModuleAffinity` vs binary module membership.
- Evidence-dependence grouping by common input dataset.
- An explicit `notCharacterized` status for a proposed catalytic reaction (not a negation of biological activity).
