# From pathway literature to FAIR, evidence-aware biological knowledge graphs

**Community learning guide and curation design note** · Companion to `pilots/falcarindiol_evidence/`

This condensed guide integrates the nine topics developed during an RDF/SPARQL/GPML/SHACL learning series. The goal is not to publish an additional pathway database, but to demonstrate a repeatable and reviewable curation workflow for linking pathway claims, their supporting experimental evidence, and subsequent multi-omics analyses.

## Scientific question

A publication often mixes observations (a loss-of-function phenotype), interpretations (a gene contributes to a pathway), and hypotheses (a CER1-like protein catalyzes a decarbonylation step). These should not be asserted as equally verified biochemical reactions. A knowledge graph must preserve which claim is supported, by which method, in which biological context and from which source.

The worked example is the tomato falcarindiol pathway described in Jeon et al., Cell (2020), DOI: https://doi.org/10.1016/j.cell.2019.11.037. Check original figures/supplements before final scientific release. The pilot's multi-omics numerical statistics are **synthetic**, not values measured in this study.

## Nine concepts consolidated

| Lesson | Topic | Practical lesson for curation |
|---|---|---|
| 1 | Literature extraction | Record separate genes, proteins, metabolites, reactions, observations, hypotheses and source locations |
| 2 | RDF and Turtle | Store graph assertions as subject–predicate–object triples using stable IRIs and distinguish literals from entities |
| 3 | RDFS and OWL | Classes, subclass hierarchies, domain/range inference and logical disjointness; ontology ≠ validation |
| 4 | SPARQL | Answer competency questions using joins, OPTIONAL, FILTER, aggregation and property paths |
| 5 | GPML2021 | Visually represent pathways; distinguish graphical element IDs from biological identifiers |
| 6 | SHACL | Validate required properties, value types, cardinality and permitted ranges |
| 7 | Provenance and evidence | Separate claims, observations, experiments, papers and curators using PROV-O, ECO and standard IDs |
| 8 | Integrated KG workflow | Load RDF, execute queries, validate data, export versioned and reproducible resources |
| 9 | Multi-omics evidence | Model BGC, co-expression, expression modules, direct and lagged gene–metabolite associations with statistical provenance |

## RDF basics

A graph assertion is a triple, e.g. `demo:Solyc12g100270 demo:encodes demo:CER1LikeProtein .` Here both the subject and object are resource IRIs. By contrast, `rdfs:label "CER1-like protein"` attaches a literal. Turtle abbreviates `rdf:type` as `a`, and a semicolon reuses the previous subject.

## Ontology and inference

In the tutorial ontology, `demo:encodes rdfs:domain demo:Gene ; rdfs:range demo:Protein .` means a reasoner can infer that the subject is a gene and the object a protein. A standard `rdflib.Graph` merely stores triples; `owlrl` must be invoked to materialize RDFS entailments. Domain/range statements do **not** reject biologically absurd inputs: an incorrect `demo:Falcarindiol demo:encodes ...` would cause RDFS to infer Falcarindiol is a gene. OWL disjointness can signal logical inconsistency, while SHACL handles data constraints.

## Distinguish claims from observations

In the pilot, the ACET1 conversion, gene 270 pathway involvement and proposed CER1-like catalytic role are **three separate claim records**. The genetic phenotype supports gene–pathway involvement, not the exact catalytic substrate–product transformation. A negative/absent heterologous-expression product is a context-dependent observation, not proof of absence of enzymatic function.

A robust publication-derived claim links a source DOI, figure/table/section locator (once verified), experiment type, original identifiers and the curation activity. Claims derived from multiple papers are separate reviewable records, not silently overwritten.

## Omics extension

Use first-class finding resources, not opaque `correlatesWith` edges, for numerical results. At minimum record gene, metabolite, analysis method, input datasets, sample and time alignment, treatment, coefficient, corrected p-value (when statistically meaningful), lag convention, magnitude, unit and software provenance.

For positive lag in the pilot, the convention is `corr(G(t), M(t+L))`, so transcript leads metabolite for `L > 0`. A temporal shift measured in pseudotime, clock hours and samples are not interchangeable. Small/unevenly sampled time series make best-lag estimates unstable and searching multiple lags requires appropriate significance procedures.

Do not combine correlated evidence from the same multi-omics dataset as if it were statistically independent. Distinguish a gene physically located in a biosynthetic cluster from one assigned to a condition-specific expression module.

## SPARQL competency queries

The pilot includes queries for supported genes, proposed/characterized claims, exploratory qualitative associations, synthetic quantified lags and incomplete labels. The exercise below retrieves the methods and sources for publication-backed claims:

```sparql
PREFIX demo: <https://example.org/falcarindiol-demo/>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?claim ?status ?source WHERE {
  ?claim a demo:ScientificClaim ;
         demo:status ?status ;
         prov:wasDerivedFrom ?source .
}
```

The query accesses explicitly asserted `ScientificClaim` typing. In general, SPARQL does not automatically invent RDFS entailments unless the graph or query service makes them available.

## SHACL quality control

Shapes may require each gene to have a label, each curated claim to have a source, and each quantitative lag result to have a valid coefficient in [-1,1] plus positive quantity/unit. `sh:qualifiedValueShape` can require at least one biochemical evidence record for a characterized reaction claim, without disallowing additional computational support.

An SHACL-conforming graph is not scientifically verified. For instance, an incorrectly typed enzyme assay can satisfy a class-based rule. Independent manual curation, chemical identity checks, and tests of experimental interpretation are still necessary. For quality checks consider validating an explicitly asserted graph using `inference='none'` to avoid RDFS-induced classifications hiding mistakes.

## GPML2021 and visualization

GPML describes the layout and graphical interactions of a pathway. Its DataNode IDs are not identical to biological IRIs. Record an explicit depiction mapping between graphical nodes and KG resources; do **not** assert `owl:sameAs` between a drawing glyph and a metabolite. A graphical conversion arrow is not automatically a complete atom-balanced biochemical reaction. Include `CitationRef` where available and verify GPML files with the PathVisio2021 schema before release.

## FAIR implementation and reproducibility

- Give each dataset/release persistent IDs, stable biological identifiers and versions.
- Link sources to publications using DOIs and controlled identifiers.
- Archive quantitative omics matrices and processing outputs separately; reference them from RDF.
- Use RO-Crate/JSON-LD for workflow and research-object packaging where helpful.
- Release a versioned ontology profile, RDF Turtle files, SHACL shapes, SPARQL competency queries, GPML diagrams, curation decisions, and pipeline tests.
- Prefer project-standard vocabularies: reconcile candidate terms with the existing specification before adding a local `lodp:` term.

## Educational and publication value

This may support an F1000Research case study on evidence-aware pathway curation or a distinct PLOS Computational Biology Quick Tips tutorial about using RDF, SPARQL, GPML and SHACL in pathway research. A publishable methodological claim requires an independently reviewed gold-standard curation table, reproducible execution, precise source locators, and limited but meaningful evaluation beyond a single hand-written graph.

## Exercises with model answers

**1. RDFS inference.** If `encodes` has domain Gene and range Protein, and `Gene270 encodes Prot270`, which types are inferred? **Answer:** `Gene270 rdf:type Gene` and `Prot270 rdf:type Protein` in an RDFS entailment graph; no enzyme activity is inferred.

**2. Missing label SPARQL.** How to find unlabeled genes? **Answer:** `?gene a demo:Gene . FILTER NOT EXISTS { ?gene rdfs:label ?label . }`.

**3. Experimental evidence.** How to prohibit computational predictions from being the *only* evidence for a characterized enzyme reaction? **Answer:** SHACL qualified count requiring `demo:BiochemicalEvidence` for `demo:supportedBy`; preserve other evidence classes as supplementary support.

**4. Missing evidence.** Why does SHACL reject a curated reaction lacking required `supportedBy` although RDF is open-world? **Answer:** Validation checks a configured completeness policy over the provided data graph; open-world logical semantics alone do not enforce completeness.

**5. Multi-omics direction.** Is a positive lag always transcript leading metabolite? **Answer:** No: the direction depends on the explicitly recorded lag definition and timestamp alignment; the pilot uses `corr(G(t), M(t+L))`.

**6. Conflicting findings.** Two algorithms place gene 270 in different expression modules. **Answer:** Retain both as separate analysis-specific findings, each linked to its input data, software, parameters and condition; do not overwrite.

**7. Biological inference.** Does a correlation between gene 270 and falcarindiol prove CER1-like catalysis of the final pathway step? **Answer:** No. It motivates an evidence-backed hypothesis, while direct catalytic annotation must remain unconfirmed until biochemical evidence is available.

## Next development steps

1. Community review of candidate ontology mappings using `specification/ontology_terms.csv` and dashboard issues.
2. Validate scientific claims against the paper with at least two curators and source locators.
3. Replace synthetic omics statistics with deposited measured outputs, sample metadata and lag-analysis parameters.
4. Add proper GPML representation and test with current project XSD validation.
5. Test transferability to one more plant specialized-metabolism pathway.
