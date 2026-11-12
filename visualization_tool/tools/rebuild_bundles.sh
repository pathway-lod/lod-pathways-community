#!/usr/bin/env bash
# Rebuild the example bundles in public/data/ (and terms.json, and the shapes for in-browser validation) from this repository's RDF, shapes and term table.
#
#   bash tools/rebuild_bundles.sh                      # run from anywhere; uses the repository root (..)
#   LODP_REPO=/other/checkout PYTHON=/path/to/python bash tools/rebuild_bundles.sh
#
# Needs Python with tools/requirements.txt (pyshacl 0.40.1, rdflib 7.6.0, owlrl 7.6.2). Takes under a minute.
# Blank-node labels change on every run; the content does not.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="${LODP_REPO:-..}"
PY="${PYTHON:-python}"
B() { "$PY" tools/build_viewer_bundle.py --repo "$REPO" --terms public/data/terms.json "$@"; }

# slide 25: one claim cut out of the annotation RDF + PlantMetWiki context + the slide's proposals
B --source "$REPO/shape_constraints/rdf/annotation.ttl" \
  --focus https://example.org/lod-pathways/pilot/annotation_MTBLS14270_neg_589_QQGLQYQXUKHWPX \
  --extra plantmetwiki=data/slide25/plantmetwiki.ttl --extra proposal=data/slide25/proposal.ttl \
  --subset data/slide25/generated_subset.ttl --out public/data/slide25.nq

# the repo's sample graph (one claim per use case), whole file
B --source "$REPO/examples/sample_evidence_graph.ttl" --all --out public/data/sample_evidence_graph.nq

# All four pilots as one plain Turtle file (no SHACL report, so the "Run SHACL validation" button can be tried on it):
# the pilot RDF of shape_constraints/rdf/ concatenated (no named blank nodes, no @base, so this is valid Turtle).
# A test dataset for the Pages site (decision D32): about 4.4 MB, 4,884 claims.
{
  echo "# All four pilots (shape_constraints/rdf/*.ttl) concatenated by visualization_tool/tools/rebuild_bundles.sh; do not edit."
  cat "$REPO"/shape_constraints/rdf/*.ttl
} > public/data/all_pilots.ttl

# Shapes and vocabulary for the "Run SHACL validation" button (validation in the browser, src/validation/):
# verbatim copies of shape_constraints/shapes/*.ttl and vocab/lodp.ttl, listed in index.json (the profile points to it).
VAL=public/data/validation
rm -rf "$VAL" && mkdir -p "$VAL"
cp "$REPO"/shape_constraints/shapes/*.ttl "$VAL"/
cp "$REPO/shape_constraints/vocab/lodp.ttl" "$VAL/vocab_lodp.ttl"
{
  printf '{\n  "comment": "Copied from shape_constraints/ by tools/rebuild_bundles.sh; do not edit.",\n  "shapes": ['
  sep=''; for f in "$REPO"/shape_constraints/shapes/*.ttl; do printf '%s"%s"' "$sep" "$(basename "$f")"; sep=', '; done
  printf '],\n  "vocab": "vocab_lodp.ttl"\n}\n'
} > "$VAL/index.json"

# Other files (e.g. a whole pilot RDF) can be bundled the same way for local tests, but only slide 25 and the
# sample graph are in the menu (public/data/datasets.json). Example:
#   B --source "$REPO/shape_constraints/rdf/bgc.ttl" --all --out /tmp/pilot_bgc.nq   # then open it with "Open file"
