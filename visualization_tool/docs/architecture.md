# Architecture

## Pipeline

```
lod-pathways-community (repository root ..)      visualization_tool/
────────────────────────────────────────────     ──────────────────────────────────────────────────────────
shape_constraints/rdf/*.ttl  ─┐
examples/*.ttl               ─┤  tools/build_viewer_bundle.py     public/data/<name>.nq   (named graphs, see below)
data/slide25/*.ttl (here)    ─┼─ subset · pyshacl · vocab  ───►   public/data/terms.json
shape_constraints/shapes/    ─┤                                   public/data/datasets.json  (menu, hand-edited)
shape_constraints/vocab/     ─┤
specification/ontology_terms.csv ┘
                                                     browser: src/App.jsx
                                                     fetch → parseRdf → indexGraph → profile (roles, labels)
                                                     → focusSet (subset) → buildView (cards, rows, edges, problems)
                                                     → render hidden, measure → layout → ports/tracks → show
```

### Bundle format (`public/data/*.nq`)

N-Quads. The graph name says where a triple comes from (`urn:lodviz:<origin>`):

| Graph | Content | Viewer treatment |
|---|---|---|
| `urn:lodviz:generated` | triples copied unchanged from the generated pilot RDF (`--source`) | normal |
| `urn:lodviz:<role>` (e.g. `plantmetwiki`, `proposal`) | one graph per `--extra role=path` file | `proposal`: dashed (not in the RDF export yet); a profile can name graphs whose subjects are knowledge-graph nodes (`roles.kg.graphs`) |
| `urn:lodviz:report` | the pyshacl validation report (`sh:ValidationResult` …, plus the shape triples pyshacl copies in) | read as problems, never drawn |
| `urn:lodviz:vocab` | `shape_constraints/vocab/lodp.ttl` | class hierarchy (`rdfs:subClassOf`) and labels, never drawn |
| default graph | what a plain `.ttl`/`.nt` opened by the user contains | origin `loaded` |

A triple in several graphs keeps all origins (`origins: Set`). A value or row counts as *proposal* only if all its
triples come only from `proposal`.

`tools/build_viewer_bundle.py`: subset = concise bounded description (CBD: the node's triples, following blank
nodes) of each `--focus` IRI, plus the CBD of every IRI that the subset or an extra file refers to and that the
source describes (one hop: the feature, the runs). `--all` takes the whole source. Then: union of subset + extras →
`pyshacl.validate(..., ont_graph=vocab, inference="none", allow_warnings=True)` (same options as
`shape_constraints/validate.py`; the vocabulary makes e.g. `lodp:MetaboliteAnnotation` a `lodp:Claim`, so the common
claim shape applies). The reference check of `validate.py` (PlantMetWiki snapshot) is not included.
`terms.json` = the term table keyed by full IRI: `{iri: {curie, label, rows: [{req_id, role, action, decision, coverage}]}}`
(rows without an IRI are skipped).

## Source files

| File | Role | Key exports |
|---|---|---|
| `src/rdf.js` | vocabulary-free core | `parseRdf` (N3.js; format from file extension; collects the file's `@prefix`es), `indexGraph`, `focusSet`, `turtleOf`, `makeCompact`, `expand`, `typesOf`, `valueOf`, `objectsOf`, `key` |
| `src/profile.js` | everything vocabulary-specific | `loadProfile`, `makeRoles`, `makeLabels`, `titleFor`, `termInfo`, `patternChecks` |
| `src/model.js` | cards / rows / edges, problems attached | `buildView` |
| `src/layout.js` | positions and edge routing | `layout`, `handlesFor`, `assignPorts`, `assignTracks`, `assignVTracks`, `LAYOUTS` (details: docs/layout.md) |
| `src/App.jsx` | state, controls, ReactFlow graph, export, legend | `Graph` (also used by the global view), `ROLE_COLOR` |
| `src/Global.jsx`, `src/global-main.jsx`, `global.html` | global view **test**: all claims on a Cytoscape.js canvas, click → `Graph` in a side panel | |
| `src/globalLayout.js` | vocabulary-free ring layout for the global view | `globalLayout` |
| `src/CardNode.jsx` | one card (header, IRI, rows, badges, problems) | |
| `src/TrackEdge.jsx` | edge between neighbouring columns: own vertical track (`data.centerX`), spread ports (`data.sOff`, `data.tOff`), label at the target | |
| `src/VTrackEdge.jsx` | edge leaving a card's bottom/top (KG trees, same-column links): spread ports (`data.sOff`, `data.tOff` as x offsets), own horizontal track (`data.trackY`), label beside the arrowhead | |
| `src/LaneEdge.jsx` | edge that skips a column: over a lane above all cards (`data.laneY`) | |
| `src/styles.css` | all styling (role colours `--data` … `--run`, term-status colours `.st-*`) | |
| `public/profiles/lod-pathways-draft.json` | the profile for today's `lodp:` draft | |
| `tools/build_viewer_bundle.py`, `tools/rebuild_bundles.sh` | data bundles | |
| `tools/screenshot.mjs` | build + headless screenshot (visual check) | |

## Data structures

`indexGraph(quads)` → `g`:
- `g.out: Map<key, triple[]>` (by subject), `g.inc: Map<key, triple[]>` (by non-literal object). A triple is
  `{s, p, o, origins: Set<string>}` with N3 terms. `key(term)` = IRI, or `_:` + blank-node label.
- `g.results`: SHACL results `{focus, path, value, severity: violation|warning|info, message, source: 'SHACL'}`;
  `g.hasReport`.
- `g.supers(cls)`: the class and all its superclasses (from `rdfs:subClassOf` in any graph).
- `g.vocabLabels`, `g.filePrefixes`, `g.quads`.

`buildView(g, keep, {P, roleOf, L, terms, runsAsCards})` → `{cards: Map, edges: []}`:
- A **card** exists for every subject in the subset `keep` (runs only with `runsAsCards`):
  `{id, role, title, iri, state: data|proposal, rows, issues}`.
- A **row** is one predicate of the card: `{pred, isType, values, issues, reqs, status, unlisted, state, missing?}`;
  a value is `{text, state, note?, href?, ref?}` (`ref` = run shown inline). Links to other cards are not rows but edges.
- An **edge** is one source→target pair (several predicates merged): `{id, source, target, preds, label, state}`.
- **Problems** (SHACL results and pattern checks) are attached: focus is a card and the result has a path → that
  row (or a new dashed *missing* row); no path → the card footer; focus not shown (an inline run) → the rows that
  refer to it.

## Roles (`makeRoles` in src/profile.js)

First rule that matches, in this order:

1. **kg** (existing knowledge-graph node, purple): a triple of the node is in a graph listed in `roles.kg.graphs`,
   or the IRI is in `roles.kg.namespaces`, or a type is in `roles.kg.classNamespaces`, or the node is the object of
   a predicate in `roles.kg.objectOf` (the anchors).
2. **claim** (orange): a type is (a subclass of) a class in `roles.claim.classes`, or the node has a predicate in
   `roles.claim.hasPredicates`.
3. **evidence** (green): object of a predicate in `roles.evidence.objectOf`.
4. **run** (grey): a type is (a subclass of) `roles.run.classes`, or object of `roles.run.objectOf`.
5. **data** (blue): everything else (in practice the submitter's data, e.g. MS features).

Consequence worth knowing: a BGC is a *claim* (it has evidence), so the BGC-pathway link claim → BGC is a
claim-to-claim edge.

## Profile reference (`public/profiles/*.json`)

| Key | Meaning |
|---|---|
| `prefixes` | CURIE prefixes for display and for the profile's own CURIEs; the file's `@prefix`es fill gaps. `obo:` IRIs are always shown as `ECO:0001580` |
| `roles.claim.classes`, `.hasPredicates` | see Roles |
| `roles.evidence.objectOf` | see Roles |
| `roles.run.classes`, `.objectOf`, `.summary` | `summary`: predicates joined for the inline run text and evidence titles (e.g. software + version) |
| `roles.kg.objectOf`, `.namespaces`, `.classNamespaces`, `.graphs` | see Roles |
| `roles.kg.name` | name of the knowledge graph, shown in the middle of the global view (default "knowledge graph") |
| `roles.<role>.label` | legend text |
| `pattern.hasEvidence`, `.generatedBy`, `.anchoredTo` | used by the pattern checks and titles |
| `terms.localNamespaces` | placeholder namespaces (orange; "not in spec" when not in the term table) |
| `terms.kgVocabularyNamespaces` | the knowledge graph's own vocabulary (purple, never "not in spec") |
| `terms.generic` | rdf/rdfs/owl/xsd: never flagged |
| `titles.labelProperties`, `titles.byClass` | card titles: first value found; per-class lists win |
| `predicateLabels` | edge label overrides (e.g. `sio:SIO_000772` → "has evidence") |

Card titles (`titleFor`): claim `<type> · → <anchor labels>` (or `not anchored`); evidence `Evidence · <run summary>`;
run `<run summary>`; others `<type> · <label>`.

Term status (`termInfo`), only with the term table: `reuse` (green), `review` (teal), `local`/`request` (orange),
`unlisted` (grey, "not in spec"), `kg` (purple), `none` (no colour). Badge = the requirement IDs (`req_id`) of the
term's rows.

Pattern checks (`patternChecks`), vocabulary from the profile: claim without evidence, claim without anchor,
evidence without provenance (only when the file has no SHACL report: the shapes say it better); node not connected
to any claim (always).

## Subset (`focusSet`)

Files with more than 60 subjects open on their first claim (`MAX_ALL` in App.jsx). For one claim the subset is: the
claim, the nodes it points to and the nodes those point to (evidence → run), knowledge-graph nodes reached from kept
knowledge-graph nodes (metabolite → pathways), and non-claim nodes that point to kept data nodes.
It does **not** include nodes that point *into* an anchor (e.g. GAME17 → α-tomatine) nor claims that point to the
focused claim.

## Rendering (src/App.jsx, `Graph`)

Two passes, because the layout needs the real card heights:
1. All cards are rendered at (0,0) with `opacity: 0`; ReactFlow measures them.
2. When `useNodesInitialized()` is true: `layout()` → positions; `handlesFor` (sides, lanes) → `assignPorts`
   (spread connection points) → `assignTracks` / `assignVTracks` (bend positions) → edges (`track` between columns / `vtrack` for top-bottom
   links / `lane`); duplicate labels at the same arrowhead are dropped; `fitBounds` over cards **and** lanes.

The `ReactFlowProvider` is keyed by `viewKey` (data, focus, all display options); changing any of them remounts and
repeats both passes. Edge-label widths for the gap sizes are measured with a canvas (`labelWidth`).

Export: PNG/SVG of the whole graph with html-to-image. The SVG embeds HTML (`foreignObject`): fine in browsers,
not editable in Inkscape/Illustrator.

## Claims ordered by SHACL problems (App.jsx, D34)

With a SHACL report (bundled, or from "Run SHACL validation"), `claimProblems` counts for every claim the violations
and warnings whose focus node is in the claim's `focusSet` (what the view of that claim shows); `claimGroups` splits
the claims into violation / warning / ok, file order inside. `claims` (Show menu, "all claims" paging, first claim of
a big file) is the concatenation; the menu shows `<optgroup>`s with the counts in front of each entry (first 2000
claims). Shared nodes (a run, a dataset) count for every claim that shows them: one run without a version puts every
claim of that tool into the warnings group (all_pilots: 1 run warning -> about 140 annotation claims). Without a report
the order is the file order, as before.

## URL parameters

`data` (file in public/data, default `slide25.nq`), `focus` (claim IRI), `profile` (profile path; empty = none),
`runs=1` (runs as cards), `layout=slide`, `terms=0` (term table off).
Global view (`global.html`): `data` (default `sample_evidence_graph.nq`), `focus` (claim IRI opened in the detail panel),
`layout` (`kg` = knowledge-graph map, default when the profile names a snapshot; `ring` = anchor ring),
`pick` (`node:<IRI>`: start with the claims that share this node picked; map only).
Screenshots of it: `npm run shot -- shots/ --page global.html "data=..."`.

## Global view (test, `global.html`)

Answers two questions before the global view is designed properly: is Cytoscape.js fast enough for thousands of
claims, and does global → detail work. Claims = role `claim`; anchors = objects of the profile's `pattern.anchoredTo`
predicates. `globalLayout` (deterministic, no forces): claims sorted by first anchor, then IRI, on an outer ring;
each anchor at the circular mean angle of its claims on an inner ring, on the rim of a disk that stands for the
knowledge graph; claims without anchor in a separate wedge. Cytoscape uses `preset` positions, `haystack` edges and
`hideEdgesOnViewport`. Click a claim → `buildView(focusSet(claim))` → `Graph` from App.jsx in a side panel; click
an anchor → list of its claims. Big local test files go into `public/data/local/` (git-ignored) and open with
`?data=local/<file>`.

Seen on the metabolomics pilot (2,722 claims, 673 anchors): it renders, but the claim ring becomes a solid line and
the edges a haze, so the real global view needs grouping (e.g. one node per anchor). Long anchor labels overlap
where anchors bunch. Interactive speed is not measured yet (headless screenshots use virtual time).

### Knowledge-graph map (test, 2026-11-11, `?layout=kg`)

The default layout of the global view when the profile names a snapshot (`roles.kg.snapshot`). Shows where the
file's claims land in PlantMetWiki (PMW):
- **Inner ring = PMW, the same for every file.** Band of 14 groups (13 PlantCyc class groups + "Single reactions"),
  sector size = pathways in the group (single reactions drawn at ¼ of their 1,316, labelled); fill = share of the
  group's pathways reached (one purple ramp, gray = none). Outside it, one tick per pathway (2,478), dark = many
  claims. Pathway titles appear when zoomed in.
- **Outer ring = all claims** (Cytoscape nodes, click → cards as before), in blocks by their primary group, then
  "only very common anchors" (all anchors in > 50 pathways) and "not found in PlantMetWiki". The claim ring is rotated
  so blocks sit near their sector. Each block has a bracket and a label "<group> · n claims" (curved along the
  block; radial for blocks too small for that). A foldable "How to read this" box (`KgLegend` in Global.jsx, starts folded)
  explains the placement rule.
- **Ribbons** from each block to every group its claims reach (width = summed weight; strong = own group). Drawn as
  polar spirals so they never cut through the disk. Hover a claim → lines to each pathway it reaches. Click a
  group or pathway (on the canvas) → side panel with its pathways/claims; other claims are dimmed.
- **Mapping** (`src/kgMap.js`, pure): anchor IRI → snapshot `nodes` (metabolite/protein/gene product IRIs),
  pathway IRI, or `alias` (old bare `PC<n>` IRIs → today's pathway via PlantCyc id). An anchor in n pathways gives
  1/n to each; anchors in more than 50 pathways (water, H+, ...) are hubs and do not place a claim. Primary group =
  largest weight. Drawing: `src/kgDraw.js`, a canvas under the Cytoscape canvas, redrawn on every pan/zoom.
- **Snapshot**: `public/data/pmw_snapshot.json` (1.3 MB, 220 kB gzipped), built by `tools/build_pmw_snapshot.py`
  from the live endpoint; class → group table `tools/pmw_class_groups.csv` (397 rows, generated from name rules,
  meant to be reviewed by hand). Virtuoso returns at most 10,000 rows and cannot page past them with ORDER BY, so
  the data-node query is split into batches of 150 pathways.
- **Links between claims** (`src/siblings.js`, pure, no vocabulary): two claims are siblings when they point at
  the same node, directly or through one of their evidence nodes (skipping runs, other claims, `rdf:type` and
  `rdf:predicate`). Pilots: competing annotations of one feature (275 features, 567 claims), same metabolite or
  pathway anchor, same paper. Each link has a kind, from how the claims reach the node (Martin, 2026-11-11):
  purple = same knowledge-graph annotation (node with role kg, or reached by a predicate in the profile's
  `pattern.sameEntity`, e.g. `skos:closeMatch` to another identifier of the anchored compound); blue = same data point
  (the claim points at it directly); grey = same source (reached only through evidence, e.g. the cited paper).
  Opened claim: halo, sibling arcs in these colours (nodes shared by > 30 claims are listed, not drawn) and a "Shares with other claims"
  bar over the cards ([select all n] picks that node). Hover: lighter arcs. Claims whose data node has other claims
  get a dark ring. Shift-click collects a hand-picked set. Picks (group, pathway, shared node, set) dim the other
  claims, put halos on the picked ones and list them in the side panel.
- **Open as cards / back** (`src/handoff.js`): every pick in the side panel has "Open these n claims in detail view →" (the detail view = the card viewer), and
  the header starts with "← Detail view" (mirrors "← Global view" in the card viewer; a hand-off without claims: the whole file, no selection). The
  global view writes one record `{source, name, text, claims, title}` to IndexedDB (database `lodviz`) and goes to
  `./?handoff=1` (`&data=` too for bundled data). The card viewer reads it, shows the union of the claims' focus
  sets (`focusSetMany` in rdf.js) 100 claims per page (`SUBSET_PAGE`, page in `viewKey`), with a bar (title, claims
  i-j of n, previous/next) and the option "selection from the global view" in Show. The same paged mode is
  available for any file as "all claims, 100 per page" in Show, in the menu's order (see "Claims ordered by SHACL
  problems" below; big files, where "everything" is disabled, still
  open on their first claim by default). TTL exports the whole selection
  (all pages), never the stubs. Layout in selection mode (compact only): `layoutGrid` in layout.js, each connected
  graph laid out with `layout()` and the graphs packed in rows, largest first (see docs/layout.md). Knowledge-graph
  stubs (`src/kgStubs.js`): anchors the file does not describe get cards from the snapshot (pathway: title, PWY id,
  group, classes; other anchors: "in n pathways" + part-of edges to pathways anchored in the view; pathways shared by
  >= 2 non-hub anchors of the view, at most 30, are added with their part-of edges), in a copy of the graph index,
  origin `plantmetwiki`, flag `stub`; the snapshot's `partOf` predicate is used for the edges. "← Global view" in the card
  viewer header goes to `global.html?handoff=1`, which reloads the same data (file text for files opened from disk)
  and picks the same claims again. IndexedDB, not the URL: hundreds of IRIs are too long for a URL, and a file opened
  from disk cannot be reopened by URL. Both pages ignore fetch responses for a source that is no longer current.
  Known limit: claims that all share one node (e.g. 100 claims of one pathway) are ONE graph, laid out as one very
  tall column of claim blocks around that node.
- **Removing it** (if the map does not work out): delete `src/kgMap.js`, `src/kgDraw.js`,
  `tools/build_pmw_snapshot.py`, `tools/pmw_class_groups.csv`, `public/data/pmw_snapshot.json`, the `snapshot` line
  in the profile, and the blocks marked "TEST 2026-11-11" / `useKg` in `src/Global.jsx`. Or just open `?layout=ring`.

## Open work

Known limits:
- No automated tests (pure functions in rdf.js, profile.js, model.js, layout.js would be easy to cover with vitest).
- SVG export is HTML-in-SVG; no static/CLI image generation without a browser (options discussed with Martin:
  A = render script around tools/screenshot.mjs; B = single-file HTML; C = native SVG renderer in Node reusing
  rdf/profile/model/layout with estimated card heights — C is the clean way for paper figures).
- Subset misses incoming knowledge-graph nodes and incoming claims (see Subset); including them needs a limit.
- Many claims in "everything": the column layout gets tall and crossings are only reduced locally; ELK (layered,
  with partitions per role) is the candidate if this matters.
- Shared side cards are placed after the first claim's block, not exactly centred between the claims.
- With many edges in one gap the tracks get dense (gap width follows labels, not edge count).
- In-browser validation (docs/validation.md): results are not shown in the global view yet, and are lost when going
  back to it (save the `.nq`); the PlantMetWiki reference check of validate.py is not included.
- No dark mode.

Candidate features (discussed, not built):
- "Requirements not covered" panel: requirements of the term table a card should fulfil but has no term for
  (e.g. MET-04 has no term yet; 9 of 188 term-table rows have no IRI).
- Different colours/roles for kinds of data (features, genes, samples) via the profile.

Findings about the data (found while building the viewer, 2026-11-10; to be fixed in the RDF and term table, not here):
- PlantMetWiki PC numbers changed after the 2026-10-01 snapshot (1162 → 2478 pathway IRIs; e.g. PC1159 is now
  coenzyme A biosynthesis, α-tomatine is PC968), so `pmw:PC<n>` anchors in the pilot RDF and sample graph probably
  point to the wrong pathways.
- `lodp:identificationTier`, `lodp:precursorMzDifference`, `lodp:libraryCompoundName` are in `lodp.ttl` and the
  RDF but not in `ontology_terms.csv` (the viewer shows "not in spec").
- `lodp:run_gnps_library` has no version (SHACL warning).
