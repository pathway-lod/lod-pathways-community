# Unresolved metabolite identities

Connectivity matching does not establish a specific stereoisomer. Each annotation
is a candidate set: its `lodp:candidateMetabolite` targets are alternatives, not
simultaneous detections. Existing `anchoredToMetabolite` and `skos:closeMatch`
links are retained for compatibility and must be read with these semantics.
No stereoisomer entities are merged. A candidate set is not guaranteed exhaustive.

The builder now emits `identityStatus "unresolved"` and a 14-character
`connectivityKey` for every annotation, even if the snapshot has only one candidate.
Shapes require candidate targets to equal anchors and share that connectivity;
connectivity annotations cannot be declared resolved. Multiple candidates cannot
be declared resolved, even for a full-key annotation. These checks validate the
representation of uncertainty, not the experimental correctness of an identity.

## Existing ambiguities

Run `python shape_constraints/audit_annotation_ambiguity.py` from the repository
root. This uses committed CSV snapshots, without downloading or changing inputs.
The resulting [CSV](annotation_ambiguity.csv) contains an annotation IRI, feature,
mode, evidence tiers, and each candidate's full InChIKey and label.

There are **303 multi-target annotations across 67 connectivity groups** out of
2,722 annotations. Of these, 290 annotations (65 groups) have differences in the
second key block; 13 annotations (2 groups) differ only in the final block.
Second-block differences flag possible stereochemical or other structural-layer
ambiguity; this is a key-based screen, not chemical curation. Final-block-only
differences flag protonation variants, not stereoisomer conflicts.

Examples in the snapshot:

| Feature | Mode | Candidate labels | Evidence tiers |
|---|---|---|---|
| 663 | neg | UDP-α-D-galactose; UDP-α-D-glucose | GNPS, consensus, SIRIUS, MS2Query exact |
| 1385 | neg | D-tryptophan; L-tryptophan | consensus, SIRIUS, MS2Query exact |
| 616 | pos | cis-zeatin; trans-zeatin | consensus, DreaMS, MS2Query exact |
| 1202 | neg | phosphate; dihydrogen phosphate | MS2Query exact |

34 of the multi-target annotations have library or consensus evidence.

These are ambiguous mappings, not contradictory measurements. For example, feature
663 supports the UDP-sugar connectivity; it does not demonstrate that both
UDP-glucose and UDP-galactose were measured, despite library and consensus support.

## Safe reporting

[annotation_coverage.rq](queries/annotation_coverage.rq) counts distinct features per
connectivity, avoiding candidate multiplication. It is suitable for the generated
annotation RDF. For pathway queries, any pathway reached via an unresolved candidate
must be labelled **possible support**; never count it as stereoisomer-resolved support.
[possible_pathway_support.rq](queries/possible_pathway_support.rq) labels candidate-derived
pathway links and deduplicates each feature/pathway pair; run it against the annotation
RDF together with PlantMetWiki.
Only a separately justified, resolved annotation should enter a resolved-identity
report. A full-key database match alone is not experimental proof of stereochemistry.

The existing pilot notebook remains a historical connectivity-level overlap analysis;
its pathway coverage and "detected metabolites" must be read at that resolution.
This change does not reclassify those historical results as confirmed detections.
External consumers that ignore identityStatus can still overinterpret legacy links;
they must adopt candidate-set semantics or the supplied aggregation query.
