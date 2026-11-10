# Decisions

Dated record of how the viewer got its current form and why. Most were decided with Martin Engst (project owner)
while building the prototype on 2026-11-10. Add new entries at the end; when a decision is reversed, add a new entry
that says so rather than editing the old one.

| # | Date | Decision | Reason |
|---|---|---|---|
| D1 | 2026-11-10 | **Cards, not triples**: one card per resource, literal values as rows inside, only resource-to-resource links as edges | Generic RDF views (force-directed, literals and `rdf:type` as nodes) get "muddy"; the target look is slides 24/25 of the 2026-11-03 community call, which are cards in columns |
| D2 | 2026-11-10 | JavaScript, React + ReactFlow (`@xyflow/react`), N3.js; built with Vite | Martin's suggestion (he uses ReactFlow); easy to embed in a web page later (e.g. the project's specification dashboard) |
| D3 | 2026-11-10 | Always show a **subset**, by default one claim and its neighbourhood | The pilot RDF has ~4,900 claims; a whole-graph view is useless |
| D4 | 2026-11-10 | Audience: **data submitters** first; should also serve any work with PlantMetWiki evidence RDF | Martin: a good view shows people what to upload and where their metadata has gaps |
| D5 | 2026-11-10 | The viewer does **not query PlantMetWiki**; context is fetched once and stored as a file | Martin, for the prototype |
| D6 | 2026-11-10 | First data = **exactly the RDF of slide 25**: generated parts verbatim, PlantMetWiki parts from the endpoint, the slide's dashed/grey parts as a separate `proposal` graph | Martin. The slide itself is hand-made SVG (make_slide_figure_v2.py in lod-pathways-community), so it had to be turned into RDF first |
| D7 | 2026-11-10 | The slide's "Agreement across tools" card has **no link** in the RDF (an orphan) | Martin noticed a link that is not on the slide; it had been a modelling choice of mine |
| D8 | 2026-11-10 | **Vocabulary-free core + profile** (JSON) that maps terms to roles; class hierarchy from the vocabulary shipped with the data; generic fallback without a profile | Martin: the ontologies of PlantMetWiki and of the evidence will be known later; the viewer must work with any data that fits the model, not just the slide |
| D9 | 2026-11-10 | **SHACL report computed beforehand** with pyshacl and shipped in the bundle; no validation in the browser | Most annotation rules are `sh:sparql` constraints, which browser SHACL libraries (rdf-validate-shacl) do not support; pyshacl with the repo's own shapes gives the real results |
| D10 | 2026-11-10 | Bundles as **N-Quads with named graphs** `urn:lodviz:<origin>` | Origin of each triple (generated / PlantMetWiki / proposal) must be visible; N-Quads keeps blank-node labels shared between data and report |
| D11 | 2026-11-10 | Overlays are optional: term table (badges, term status), SHACL report, pattern checks (only without report, except orphans) | The specification is still changing; the viewer must work with any of them missing |
| D12 | 2026-11-10 | **Hand-written deterministic layout**, not force-directed and not (yet) ELK | Predictable pictures that encode the evidence pattern; ELK kept as the option for large subsets |
| D13 | 2026-11-10 | KG (purple) cards that link to each other form a vertical group with the anchor on top | Martin |
| D14 | 2026-11-10 | Claims centred on their evidence cards (block layout), linked claims adjacent | Martin: untangle the edges |
| D15 | 2026-11-10 | **Compact column order is the default**: runs · data + evidence · claims · knowledge graph; slide order kept as an option | Martin's idea: with evidence and data on the left, anchors go straight to the right and KG groups no longer need to sit side by side |
| D16 | 2026-11-10 | Each edge on its own track in the gap; connection points spread along the card side; gap width = widest label | Martin: no overlapping arrows; labels must fit |
| D17 | 2026-11-10 | Data shared by two claims is placed between their blocks | Martin: minimise edge overlaps on slide 25; accepted that with many claims this cannot be solved in general |
| D18 | 2026-11-10 | Own repository, private: github.com/Tontolda/RDF_viewer_prototype | Martin. The bundled team data has no license yet, so it stays private |
| D19 | 2026-11-10 | Only **slide 25 and the sample graph** ship as examples; the full pilot bundles (9.3 MB) and the plain-Turtle copy of the sample graph removed from the menu and the repo | Martin, preparing to host the viewer on GitHub Pages in lod-pathways-community (on a branch). Big files can still be opened with "Open file" |
| D20 | 2026-11-10 | **Moved into lod-pathways-community** as `visualization_tool/` (branch `visualization-tool`), published with the repository's existing GitHub Pages site under `/visualization_tool/` | Martin: other project members should test it with their own data; the repository now has an MIT license, so the example data can be public. One Pages site per repository, so the viewer is added to the existing workflow |
| D21 | 2026-11-10 | Two levels: a **global view** of all claims of a file, and the current cards as the **detail view** opened from it. First sketch: knowledge graph in the middle, claims around it, unanchored data visible separately | Martin: users must see large amounts of data at once; details on demand. "Linked" = the claim has an anchor property in the file; checking anchors against PlantMetWiki is not the viewer's task (other objectives), so D5 stays |
| D22 | 2026-11-10 | Global view test with **Cytoscape.js** (canvas), not ReactFlow and not sigma.js | ReactFlow (DOM) does not scale to thousands of nodes. Cytoscape.js has deterministic preset/concentric layouts, compound nodes for grouping, CSS-like styles, and its JSON opens in Cytoscape desktop, which many biologists know; sigma.js (WebGL) only wins above ~10k nodes (pilots: ~4,800 claims in total) |
