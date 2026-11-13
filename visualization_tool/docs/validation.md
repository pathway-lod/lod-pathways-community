# SHACL validation in the browser

The card viewer can validate the loaded file against the repository's SHACL shapes in the browser ("Run SHACL
validation" in the header, where a file without a report used to say "no SHACL report"). Nothing is uploaded; it
works on GitHub Pages. Decision D31 (2026-11-12). Built and checked 2026-11-12. Everything needed to maintain it is in this file; the upstream status of the
shacl-engine bugs is in "Upstream status" below.

## What the user sees

1. A file without a SHACL report shows **Run SHACL validation** and an estimate ("about 12 s").
2. While it runs: a progress bar, the current step ("cross-check 3 of 17"), elapsed time "of about …", **Cancel**.
   The bar is time-based (the steps are very uneven) and never fills before the result is there.
3. Afterwards the summary shows `SHACL: n violations, m warnings`, the cards show the results as for the bundled
   examples (✕ / !, messages, missing required properties as dashed rows), and **Save data + report (.nq)** writes
   the loaded data plus the report as one N-Quads file. Opening that file again ("Open Turtle file…") shows the report
   without running the validation again. The tooltip of "validated here in … s" gives the time per step.

The whole file is validated, also when only a selection (e.g. from the global view) is shown: shapes such as "the run
of an evidence node is a lodp:Run" need nodes outside the selection. Files that bring their own report (the bundled
examples, a saved `.validated.nq`) show no button.

Why data + report in one file and not the report alone: the report points at evidence nodes, which are blank nodes.
Blank-node labels change every time a Turtle file is parsed, so a separate report could not be matched to the data
again. N-Quads keep the labels; the viewer's bundles use the same format for the same reason (CLAUDE.md rule 6).

## Where things are

| Path | Role |
|---|---|
| `src/ValidationControl.jsx` | the header control (button, progress, save) |
| `src/validation/run.js` | main thread: loads the shapes named in the profile, starts the worker, merges the report into the quads (`urn:lodviz:report`), time estimate |
| `src/validation/worker.js`, `worker-shim.js` | Web Worker around engine.js (the page stays responsive; Cancel terminates it). The shim gives Comunica's browser code a `window` and a fast `setImmediate` |
| `src/validation/engine.js` | `validate({dataNq, shapes, vocab, onProgress})`: shacl-engine plus the corrections below; returns the report as N-Quads. Runs in Node too |
| `public/data/validation/` | copies of `shape_constraints/shapes/*.ttl` and `vocab/lodp.ttl` + `index.json`, written by `tools/rebuild_bundles.sh` (so the Pages workflow refreshes them on every deploy). Do not edit |
| profile `"validation": {"index", "label"}` | where the shapes are; no entry = no button (the core knows no shapes, rule 1) |
| `tools/validate.mjs` | the same validator on the command line (Node ≥ 22), for comparing with `shape_constraints/validate.py` |

The validator is [shacl-engine](https://github.com/rdf-ext/shacl-engine) **1.1.3, pinned exactly** (engine.js imports
files from its `lib/`), with its SPARQL plugin replaced, and Comunica 5.4.1 (`query-sparql-rdfjs-lite`) for SPARQL.
They are only in the worker chunk (about 1.9 MB, loaded on the first click); the viewer itself grew by about 5 KB.

## Corrections to shacl-engine 1.1.3 (all in engine.js)

Found by comparing with pyshacl (the validator of `shape_constraints/validate.py` and of the bundles). Without them,
shacl-engine found 54 of 83 expected problems in the repository's shape tests and reported false violations on valid data.

1. **Several `sh:sparql` on one shape** (a bug): shacl-engine compiles them as one constraint whose query is empty, so
   every focus node gets a false violation and the real constraints never run. engine.js compiles each `sh:sparql`
   node on its own. Also skips SPARQL constraints with `sh:deactivated true` (stock 1.1.3 ignores that, a second bug).
   See "Upstream status".
2. **Subclasses**: shacl-engine follows `rdfs:subClassOf` (for `sh:targetClass`, `sh:class`) only in the shapes graph;
   the vocabulary is therefore added to the shapes as well as to the data (pyshacl reads it from the data).
3. **Message of a SPARQL constraint**: shacl-engine prefers the shape's `sh:message`; engine.js uses the constraint's
   own, as pyshacl does. Note: shacl-engine is the one that follows the spec here (SHACL §2.1.5: a shape's
   `sh:message` applies to all its results); pyshacl differs. We follow pyshacl so both validators agree. The cleaner
   fix is in our shapes (no shape-level `sh:message` next to SPARQL constraints, seen in the BGC link shapes).

## Speed

shacl-engine runs every SPARQL constraint once per focus node with a new query engine each time: 17 min for the
54k-triple annotation pilot. engine.js instead

- runs a SPARQL constraint **once over the whole data** and looks its rows up per focus node, when that gives the same
  rows (`isSafe`: SELECT projecting `$this`, `$this` in a top-level triple pattern, no subquery, VALUES, aggregate,
  GROUP BY, LIMIT/OFFSET, and no UNION inside (NOT) EXISTS or MINUS, see below); otherwise per node, as before;
- uses **one Comunica engine** for the whole run;
- gives Comunica a source that returns **arrays, not streams**, and `countQuads`. shacl-engine's source wraps every
  match in readable-stream, whose browser stand-in for `process.nextTick` uses `setTimeout` (≥ 4 ms per step in a
  browser); with one stream per `FILTER NOT EXISTS` row this made the cross-checks 6× slower in the browser than in Node.

**Comunica bug** (5.4.1): `$this p ?a . FILTER NOT EXISTS { { $this q ?a } UNION { $this r ?a } }` returns the right rows
with `$this` pre-bound, but none with `$this` unbound (`MINUS { … UNION … }` too; two separate `FILTER NOT EXISTS` work).
That is why such queries stay per node. Today this is 1 of the 18 queries (association: "lodp:anchorTier does not match any side tier").

Measured 2026-11-12 (Edge headless on one laptop; whole pilot files): annotation 54k triples 11 s, association 27k
6.5 s, bgc 7.5k 1.8 s, a 30-claim file 1.7 s (mostly starting the worker). pyshacl needs 347 s / 91 s / 15 s for the
same files. The estimate in run.js (`1 s + 0.2 ms per triple`) is fitted to these numbers.

## How to check a change

There are no automated tests. After changing `src/validation/`, the shapes or the dependencies:

1. Same results as pyshacl: `node tools/validate.mjs <file>` and `python shape_constraints/validate.py <file> --no-references`
   on the pilot files and on broken copies of the sample graph (the cases of `shape_constraints/tests/test_shapes.py`).
   On 2026-11-12 all 83 test cases and the 4 pilot files gave identical results (severity, message, focus node,
   path, value).
2. In a browser: open a file without a report (e.g. a pilot RDF bundled locally, see CLAUDE.md), click the button,
   check the progress bar, the marks on the cards, the saved `.nq` and that reopening it shows the report.

## Upstream status (checked 2026-11-12)

| Problem | Spec | Upstream | Here |
|---|---|---|---|
| Several `sh:sparql` on one shape: none runs, every focus node gets one fused violation | §5.2: each `sh:sparql` value is its own constraint | **not reported**; same code on `master` (`6418118`) and branch `experimental`. Patch ready, not submitted: [upstream/shacl-engine-multiple-sparql.patch](upstream/shacl-engine-multiple-sparql.patch) (against `master` `6418118`, adds `test/assets/sparql/multiple.ttl`; 155/155 upstream tests pass with it, the new test fails without) | correction 1 |
| `sh:deactivated true` on a SPARQL constraint ignored | §5.3 | **not reported**; would be a two-line follow-up to the patch | correction 1; only the literal `"true"` is recognised, `"1"^^xsd:boolean` would slip through |
| `rdfs:subClassOf` read from the shapes graph only | SHACL instance definition uses the data graph | already reported: rdf-ext/shacl-engine issue #84 (open) | correction 2 |
| Comunica 5.4.1: `NOT EXISTS { … UNION … }` with `$this` unbound returns no rows | | not reported | such queries run per node (see Speed) |

Posting the issue/PR upstream is a decision for the maintainers of this viewer (not done as of 2026-11-13). If
shacl-engine releases a fix, re-run "How to check a change" before unpinning: engine.js imports files from its `lib/`.

## Open

- The global view does not show validation results yet; a validation done in the card viewer is lost when going back
  (the hand-off carries the file text, not the report). Saving and reopening the `.nq` keeps it.
- The PlantMetWiki reference check of `validate.py` (do the anchored pathways/metabolites exist?) is not SHACL and is
  not included.
- Node < 22 cannot load Comunica (its `undici`); only `tools/validate.mjs` needs Node, the browser does not.
