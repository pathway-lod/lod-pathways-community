#!/usr/bin/env bash
# Rebuild the example bundles in public/data/ (and terms.json) from this repository's RDF, shapes and term table.
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

# Other files (e.g. a whole pilot RDF) can be bundled the same way for local tests, but only slide 25 and the
# sample graph are in the menu (public/data/datasets.json). Example:
#   B --source "$REPO/shape_constraints/rdf/bgc.ttl" --all --out /tmp/pilot_bgc.nq   # then open it with "Open file"
