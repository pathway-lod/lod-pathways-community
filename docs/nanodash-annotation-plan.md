# Design note: collaborative annotation of experiments with Nanodash

**Status:** proposal, with a spike (a short test) planned before any commitment. Nothing described here is built yet.

## Question

The specification, the shape constraints and the dashboard let a community discuss and choose ontology terms. They do not yet give people a way to **use** those terms to annotate new experiments and predictions. [Nanodash](https://github.com/knowledgepixels/nanodash) is a web client for nanopublications (signed, public statements with provenance) that builds its forms from templates. This note asks whether it can serve as the annotation front end, and what a first test should show.

## What Nanodash offers (from its documentation and code, not yet run here)

- **Templates** describe form fields and the triples they produce. Fields can be free text with a datatype, a fixed list (`nt:possibleValue`), a pattern (`nt:hasRegex`), or a choice looked up in an external service (`nt:possibleValuesFromApi`). The code includes a parser for the search service of the EBI Ontology Lookup Service.
- **Authorship and provenance:** each annotation is signed with the author's ORCID.
- **Site mode:** `NANODASH_SITE_SPACE` makes one instance the website of one space, with its own name, logo and stylesheet. Several sites on one instance and custom domains are documented as proposed.
- **SHACL alignment** of templates is a proposal in Nanodash, not an implemented feature.
- **Deployment:** a Docker image; Java 21 for building from source.

## Concerns

1. Annotations are public and permanent. They can be retracted, not deleted.
2. Form entry does not suit bulk data. Large sets have to be published programmatically.
3. A template enforces datatypes, lists and patterns. It cannot enforce the SPARQL consistency rules of the shapes or the check that a PlantMetWiki node exists; a separate validation step is needed.
4. Published annotations are immutable, while many terms of the specification are still `proposed` or `open`.
5. Maintaining a code fork of a fast-moving project is costly. Most of the work is content (templates, a space, views), which needs no code change.

## Alternatives

| Option | Strength | Weakness |
|---|---|---|
| Nanodash templates | provenance, signatures, ontology pickers, roles | public and permanent, not for bulk data, new stack |
| A form on GitHub Pages that opens a pull request with RDF | same infrastructure as the dashboard, validated by the shapes, reversible | no live collaboration, no signatures |
| RDF generated from pilot results, discussed on the dashboard | already works | no manual annotation |

## Plan

| Phase | Work | Gate |
|---|---|---|
| 0. Spike (1-2 days) | Run Nanodash locally. Build one template for a metabolite annotation claim: ontology picker for the evidence class (ECO), fixed list for the match level, pattern for the InChIKey. Fill it with the example feature of [`examples/`](../examples/) and read the resulting nanopublication. | Is the form usable by a plant scientist? Does the claim, evidence and run pattern fit the assertion, provenance and publication-information parts? Does the picker work? |
| 1. Templates from the specification | A script reads `specification/ontology_terms.csv` and the shapes and writes templates: lists and patterns from the shapes, pickers from the ontology of each term, optional and repeatable statements from the shape cardinalities. Terms that are not yet agreed stay out or are marked provisional. | A generated template reproduces the sample graph closely enough to pass the shapes. |
| 2. Validation loop | An Action reads nanopublications of the template type from the nanopublication network, converts them, runs `validate.py` with the PlantMetWiki reference check, and reports on the dashboard. | Reports are understandable to annotators. |
| 3. Space and site | A space with roles (maintainer, annotator) and views (claims by evidence type); site mode only if a branded website is needed. | |
| 4. Ingestion into PlantMetWiki | Define which signers are trusted and add a review step before loading. | Agreement of the PlantMetWiki maintainers. |
| 5. Bulk path | Publish pilot results programmatically in the same network, if wanted. | |

## Spike: status

- Docker Desktop was started. The image `nanopub/nanodash:latest` could not be pulled: the Docker daemon's connection to Docker Hub timed out through its configured proxy (`http.docker.internal:3128`), although the host reaches Docker Hub.
- Building from source needs Java 21; only Java 8 is installed on the machine used so far.
- Nothing has been published. No test registry is documented in the Nanodash repository. A private or local registry and query service can be configured (`NANOPUB_REGISTRY_INSTANCES`, `NANOPUB_QUERY_INSTANCES`, `NANODASH_MAIN_REGISTRY`, `NANODASH_MAIN_QUERY`), and the publish form has a preview that shows the nanopublication before it is published.

## Open decisions

- Whether the goal is curation of a few annotations or collection of annotations at scale.
- Whether public and permanent publication is acceptable for new experiments.
- Who hosts an instance and registers the ORCID application.
- Time available beyond the spike.
