#!/usr/bin/env python3
"""
Build a data bundle for the evidence graph viewer (visualization_tool/ in lod-pathways-community).

Purpose
  Take a SUBSET of the generated pilot RDF (one or more claims and what they point to), add extra Turtle files
  (PlantMetWiki context, proposals), validate the union with the SHACL shapes of this repository, and
  write everything as N-Quads with one named graph per origin, so the viewer knows where each triple comes from:
      urn:lodviz:generated     triples copied verbatim from the generated RDF (--source)
      urn:lodviz:<role>        triples of each --extra file (e.g. plantmetwiki, proposal)
      urn:lodviz:report        the pyshacl validation report (sh:ValidationResult ...)
      urn:lodviz:vocab         the vocabulary (shape_constraints/vocab/lodp.ttl): class hierarchy and labels for the viewer
  N-Quads (not TriG) keeps blank-node labels identical between the data and the report.
  Also writes terms.json from specification/ontology_terms.csv (IRI -> requirement IDs, action, decision, label).

Inputs
  --repo       root of lod-pathways-community (shapes, vocabulary, term table);
               default: $LODP_REPO, else the repository this folder is in (visualization_tool/..)
  --source     generated Turtle file (e.g. ../shape_constraints/rdf/annotation.ttl)
  --focus      IRI(s) of the claim(s) to extract; their CBD plus the CBD of every IRI they (or the extras) point to
  --all        take the whole source instead of a subset (the viewer then picks one claim at a time)
  --extra      role=path, repeatable
  shapes, vocab and term table are read from the repository (not modified)

Outputs
  --out        N-Quads bundle (e.g. public/data/slide25.nq)
  --terms      terms JSON      (e.g. public/data/terms.json)
  --subset     optional: the extracted generated subset as Turtle, for reading

Run (from visualization_tool/, with Python that has tools/requirements.txt; pyshacl 0.40.1, rdflib 7.6.0):
  python tools/build_viewer_bundle.py \
      --source ../shape_constraints/rdf/annotation.ttl \
      --focus https://example.org/lod-pathways/pilot/annotation_MTBLS14270_neg_589_QQGLQYQXUKHWPX \
      --extra plantmetwiki=data/slide25/plantmetwiki.ttl \
      --extra proposal=data/slide25/proposal.ttl \
      --subset data/slide25/generated_subset.ttl \
      --out public/data/slide25.nq \
      --terms public/data/terms.json
  tools/rebuild_bundles.sh rebuilds both example bundles.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import pyshacl
from rdflib import BNode, Dataset, Graph, URIRef

import os

VIEWER = Path(__file__).resolve().parent.parent
DEFAULT_REPO = Path(os.environ.get("LODP_REPO", VIEWER.parent))
NS = "urn:lodviz:"


def repo_paths(repo):
    repo = Path(repo)
    paths = {"shapes": repo / "shape_constraints" / "shapes", "vocab": repo / "shape_constraints" / "vocab" / "lodp.ttl",
             "terms": repo / "specification" / "ontology_terms.csv"}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        sys.exit("not a lod-pathways-community clone (missing " + ", ".join(missing) + "); give --repo")
    return paths


def cbd(g, node, out, seen):
    """Concise bounded description: all triples of node, following blank-node objects."""
    if node in seen:
        return
    seen.add(node)
    for p, o in g.predicate_objects(node):
        out.add((node, p, o))
        if isinstance(o, BNode):
            cbd(g, o, out, seen)


def extract(source, focus, extras):
    sub, seen = Graph(), set()
    for f in focus:
        if (URIRef(f), None, None) not in source:
            sys.exit(f"focus IRI not found as a subject in the source: {f}")
        cbd(source, URIRef(f), sub, seen)
    # one hop: every IRI the subset or the extra files point to (or describe) that the source describes
    refs = {o for _, _, o in sub if isinstance(o, URIRef)}
    for g in extras.values():
        refs |= {t for trip in g for t in (trip[0], trip[2]) if isinstance(t, URIRef)}
    for r in refs:
        if (r, None, None) in source:
            cbd(source, r, sub, seen)
    for pfx, ns in source.namespaces():
        sub.bind(pfx, ns)
    return sub


def terms_json(terms_csv):
    terms = defaultdict(lambda: {"curie": "", "label": "", "rows": []})
    with open(terms_csv, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["iri"]:
                continue
            t = terms[r["iri"]]
            t["curie"], t["label"] = r["curie"], t["label"] or r["label"]
            t["rows"].append({k: r[k] for k in ("req_id", "role", "action", "decision", "coverage")})
    return terms


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    ap.add_argument("--repo", default=str(DEFAULT_REPO))
    ap.add_argument("--source", required=True)
    ap.add_argument("--focus", nargs="+")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--extra", action="append", default=[], help="role=path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--terms", required=True)
    ap.add_argument("--subset")
    a = ap.parse_args(argv)
    paths = repo_paths(a.repo)

    source = Graph().parse(a.source, format="turtle")
    extras = {}
    for e in a.extra:
        role, path = e.split("=", 1)
        extras[role] = Graph().parse(path, format="turtle")

    if not a.all and not a.focus:
        sys.exit("give --focus IRI(s) or --all")
    subset = source if a.all else extract(source, a.focus, extras)
    if a.subset:
        Path(a.subset).parent.mkdir(parents=True, exist_ok=True)
        subset.serialize(a.subset, format="turtle")

    union = Graph()
    for g in [subset, *extras.values()]:
        for t in g:
            union.add(t)
    shapes = Graph()
    for p in sorted(paths["shapes"].glob("*.ttl")):
        shapes.parse(p, format="turtle")
    vocab = Graph().parse(paths["vocab"], format="turtle")
    conforms, report, text = pyshacl.validate(union, shacl_graph=shapes, ont_graph=vocab, inference="none",
                                              allow_warnings=True, meta_shacl=False, advanced=False)

    ds = Dataset()
    for name, g in [("generated", subset), *extras.items(), ("report", report), ("vocab", vocab)]:
        ng = ds.graph(URIRef(NS + name))
        for t in g:
            ng.add(t)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    ds.serialize(a.out, format="nquads")
    Path(a.terms).write_text(json.dumps(terms_json(paths["terms"]), ensure_ascii=False, indent=1), encoding="utf-8")

    n_res = len(list(report.subjects(predicate=URIRef("http://www.w3.org/ns/shacl#focusNode"))))
    print(f"subset: {len(subset)} triples; extras: " + ", ".join(f"{k} {len(v)}" for k, v in extras.items()))
    print(f"SHACL: conforms={conforms}, {n_res} results")
    print(text.split("\n", 3)[-1][:3000] if n_res else "")
    print(f"wrote {a.out} and {a.terms}")


if __name__ == "__main__":
    main()
