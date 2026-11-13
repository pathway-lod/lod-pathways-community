# Editing the profile and the score definitions

Two files hold everything the viewer knows about the evidence vocabulary. When terms change (an ontology term
replaces a `lodp:` placeholder, a pilot adds a score), edit these files, not the code (CLAUDE.md, rule 1).

| File | What it decides |
|---|---|
| `public/profiles/lod-pathways-draft.json` | the **profile**: which classes and predicates make a node a claim, evidence, run or knowledge-graph node; prefixes; card titles; edge labels; where the snapshot, the SHACL shapes and the score CSV are |
| `public/profiles/lod-pathways-draft.scores.csv` | the **score definitions** for the global view's Score panel: which literal properties are scores, which direction is better, the colour scale |

Neither needs a rebuild of the data bundles. With `npm run dev` running, save and reload the page. The live site
changes only after the edit is merged to `main` (CLAUDE.md, "Git").

## The profile

Format: JSON (no comments; the `comment` key is the place for notes). Every term can be written as a CURIE with a
prefix from `prefixes`, or as a full IRI. Lists can hold several terms.

### Keys, and what breaks if they are wrong

The full reference is in [architecture.md](architecture.md#profile-reference-publicprofilesjson); the roles rules
are in [architecture.md](architecture.md#roles-makeroles-in-srcprofilejs). In short:

| Key | Used for | If wrong or missing |
|---|---|---|
| `prefixes` | expanding CURIEs in this file and in the score CSV; display of IRIs | a CURIE with an unknown prefix is **not expanded and matches nothing, without a warning** |
| `roles.claim.classes`, `.hasPredicates` | which nodes are claims (subclasses count, from the vocabulary in the data, graph `urn:lodviz:vocab`) | claims show as data cards; the global view has no claims |
| `roles.evidence.objectOf` | evidence = object of these predicates | evidence shows as data |
| `roles.run.classes`, `.objectOf`, `.summary` | runs; `summary` = properties joined for run and evidence titles (software + version) | runs show as data; titles fall back to labels/IRIs |
| `roles.kg.objectOf`, `.namespaces`, `.classNamespaces`, `.graphs` | knowledge-graph (purple) nodes; `objectOf` = the anchor predicates | anchors show as data |
| `roles.kg.name`, `.snapshot` | name in the middle of the global view; PlantMetWiki snapshot for the map and stub cards | no snapshot: global view falls back to the ring layout, no stub cards |
| `roles.<role>.label` | legend text | |
| `pattern.hasEvidence`, `.generatedBy`, `.anchoredTo`, `.sameEntity` | pattern checks, card titles, global-view anchors and links between claims, scores on evidence | missing checks; claims "not anchored"; scores on evidence not found |
| `terms.localNamespaces`, `.kgVocabularyNamespaces`, `.generic` | row colours (term status) | wrong colours / "not in spec" flags |
| `titles.labelProperties`, `titles.byClass` | card titles: first value found, per-class lists first | IRIs as titles |
| `predicateLabels` | edge label text | the CURIE is shown |
| `validation.index`, `.label` | in-browser SHACL (docs/validation.md); `label` is the button's tooltip | no "Run SHACL validation" button |
| `scores.definitions` | path of the score CSV (below); `scores.label` is a note, not shown | no Score button |

Paths (`snapshot`, `validation.index`, `scores.definitions`) are relative to the site root, which is `public/` in
the source tree (e.g. `profiles/lod-pathways-draft.scores.csv`).

### The same term sits in several keys

A predicate usually has more than one job. Today:

| Term | Keys |
|---|---|
| `sio:SIO_000772` (has evidence) | `roles.claim.hasPredicates`, `roles.evidence.objectOf`, `pattern.hasEvidence`, `predicateLabels` |
| `lodp:mibigMatchEvidence` | `roles.evidence.objectOf`, `pattern.hasEvidence`, `predicateLabels` |
| `prov:wasGeneratedBy` | `roles.run.objectOf`, `pattern.generatedBy` |
| `lodp:anchoredInPathway`, `lodp:anchoredToMetabolite` | `roles.kg.objectOf`, `pattern.anchoredTo` |

So when a term is renamed, **search the whole profile for it** (and the score CSV), not just one key.

### Recipes

- **A `lodp:` placeholder is replaced by an ontology term** (e.g. a real "anchored in pathway" predicate): replace
  the CURIE everywhere in the profile; add the ontology's prefix to `prefixes` if it is new. Keep the old term next to
  the new one as long as files with the old term should still work (lists may hold both).
- **A new kind of claim** (e.g. `lodp:GeneClusterClaim`): nothing to do if the vocabulary shipped with the data
  declares it `rdfs:subClassOf lodp:Claim`. For plain Turtle files without that vocabulary, add the class to
  `roles.claim.classes`.
- **A new evidence predicate**: add it to `roles.evidence.objectOf` and `pattern.hasEvidence`, and a readable name
  to `predicateLabels`.
- **Better card titles for a class**: `titles.byClass: { "<class>": ["<property>", ...] }`.
- **A new namespace in the data** (so it is shown as `x:Term`, not as a full IRI): add it to `prefixes`. Prefixes
  declared in the opened file are used too, but the profile's win.

### A second profile

The card viewer reads `?profile=<path>` (`?profile=` empty = no profile, the generic fallback). The list of
profiles is `PROFILES` in `src/App.jsx` (the chooser is hidden since D29). **The global view always uses
`profiles/lod-pathways-draft.json`** (`PROFILE` in `src/Global.jsx`) and ignores `?profile=`. A second profile
therefore needs a small code change in Global.jsx. To change the one profile in use, edit the file instead.

### Check after editing

1. The JSON parses: a broken file shows "profile: …" as an error in the header.
2. Screenshots of the check queries in CLAUDE.md (card viewer and global view). Look for claims shown as data
   cards (orange claim cards missing), "not anchored" titles, and the legend.
3. `data=sample_evidence_graph.nq&profile=` must still work (no profile).

## The score CSV

One row per score property. Comma-separated, UTF-8, first row = column names; quote fields that contain commas
(`"a, b"`, with `""` for a quote inside). Extra columns are ignored, so the order of the columns does not matter
as long as the names are right.

| Column | Values | Used for |
|---|---|---|
| `property` | CURIE (prefix from the profile or the file) or full IRI of the literal property | finding the values. **Required**; rows without it are skipped |
| `label` | text | menu, panel, `?score=` |
| `better` | `higher` or `lower` | ranking and colour direction; anything else counts as `higher` |
| `min`, `max` | numbers, `max > min` | the colour scale and the histogram. The **theoretical** range of the tool (D36), not the range in one file, so colours mean the same in every file. Values outside are drawn in the end colour and counted in the panel |
| `scale` | `linear` or `log` | `log` for p-values; needs `min > 0`; values ≤ 0 are drawn at the `min` end (see "Examples") |
| `kind` | `numeric` (or `ordinal`) | only `numeric` is read; **`ordinal` rows are skipped** (not built yet) |
| `order` | values separated by `\|`, best first | for ordinal scores later; read but not used yet |
| `attached_to` | `claim` or `evidence` | where the value sits. `evidence` = on the nodes reached from the claim through `pattern.hasEvidence`; anything other than `claim` counts as `evidence` |
| `status` | `confirmed` or `assumed` | shown in the panel next to the range |
| `note` | text | shown in the panel: source, caveats |

**Rows that are dropped without a message:** no `property`; `kind` not `numeric`; `min` or `max` empty or not a
number; `max <= min`; `scale=log` with `min <= 0`. If a score does not appear in the menu, check these first. The
menu also lists only the scores that occur in the opened file (the panel then says "none of the defined scores
occurs in this file").

Several values for one claim (several evidence nodes with the score): the best one counts.

### Examples (from the current CSV)

```csv
property,label,better,min,max,scale,kind,order,attached_to,status,note
lodp:siriusConfidenceApprox,SIRIUS approximate confidence,higher,0,1,linear,numeric,,evidence,assumed,"SIRIUS (COSMIC) approximate confidence, 0-1."
obo:OBI_0000175,correlation p-value,lower,1e-10,1,log,numeric,,evidence,assumed,"p-value; log scale needs min > 0, so 1e-10 is the floor."
```

A p-value of exactly 0 (or anything below `min`) gets the best-end colour for a `lower` score and is counted as
outside the range.

### Adding a score

1. Find the property and where it sits: `grep` the RDF (`public/data/all_pilots.ttl`) for it, and check whether the
   subject is the claim or an evidence node.
2. Look up direction and theoretical range in the term table (`../specification/ontology_terms.csv`), `lodp.ttl` or
   the tool's documentation; mark the row `assumed` if you could not confirm it.
3. Add the row. Candidates already worked out (12 numeric, 2 ordinal): [score-candidates.csv](score-candidates.csv).
   Their ranges come from the pilot data, not the tools' theoretical ranges, so check them before copying.
4. Check: `npm run shot -- shots/ --page global.html "data=all_pilots.ttl&score=<property>&top=50"` and look at the
   panel (range in the file, values outside the range, histogram) and the map.

A different CSV file can be named in the profile (`scores.definitions`); no code change is needed for that.
