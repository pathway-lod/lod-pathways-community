#!/usr/bin/env python3
"""
Validate RDF files against the LOD-pathways shapes before adding them to the knowledge graph.

  python validate.py rdf/bgc.ttl rdf/association.ttl          # text report
  python validate.py rdf/*.ttl --strict                         # warnings also fail
  python validate.py file.ttl --no-references                   # skip the PlantMetWiki existence check

Two layers of checking:
  1. SHACL shapes (shapes/*.ttl) check structure, value ranges, controlled lists and consistency.
     sh:Violation  -> must be fixed, the data is not added
     sh:Warning    -> well formed but weakly supported, flagged for review
  2. A reference check (not expressible in SHACL) tests that the PlantMetWiki pathways and
     metabolites a claim is anchored to exist in a dated snapshot (snapshots/, see refresh_snapshots.py).

Exit code: 0 = no violations, 1 = violations (or warnings with --strict), 2 = usage error.
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyshacl
from rdflib import RDF, Graph, Namespace, URIRef

HERE = Path(__file__).parent
SHAPES_DIR = HERE / "shapes"
VOCAB = HERE / "vocab" / "lodp.ttl"
SNAPSHOTS = HERE / "snapshots"

SH = Namespace("http://www.w3.org/ns/shacl#")
LODP = Namespace("https://example.org/lod-pathways/pilot/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
PMW_PATHWAY = "http://rdf-plantmetwiki.bioinformatics.nl/pathways/"
INCHIKEY = "https://identifiers.org/inchikey/"

SEVERITY = {str(SH.Violation): "Violation", str(SH.Warning): "Warning", str(SH.Info): "Info"}


def load_graph(paths):
    g = Graph()
    for p in paths:
        g.parse(str(p), format="turtle")
    return g


def load_shapes(shapes_dir=SHAPES_DIR):
    return load_graph(sorted(Path(shapes_dir).glob("*.ttl")))


def _short(term, g):
    s = str(term)
    for pre, ns in (("pmw:", PMW_PATHWAY), ("lodp:", str(LODP)), ("obo:", str(OBO))):
        if s.startswith(ns):
            return pre + s[len(ns):]
    return s if len(s) < 110 else s[:107] + "..."


def shape_label(shapes, node):
    """Readable name of a (possibly blank) source shape: 'Claim: lodp:anchorTier'."""
    if node is None or node == "":
        return ""
    if isinstance(node, URIRef):
        return shapes.value(node, SH.name) and str(shapes.value(node, SH.name)) or _short(node, shapes)
    owner = next(shapes.subjects(SH.property, node), None)
    owner_name = str(shapes.value(owner, SH.name)) if owner is not None and shapes.value(owner, SH.name) else ""
    path = shapes.value(node, SH.path)
    if path is not None and not isinstance(path, URIRef):       # sequence path (a b)
        items = list(shapes.items(path))
        path = " / ".join(_short(i, shapes) for i in items) if items else path
    elif path is not None:
        path = _short(path, shapes)
    if not owner_name:                                           # constraint nested in sh:or / sh:sparql
        parent = next(shapes.subjects(None, node), None)
        owner_name = str(shapes.value(parent, SH.name)) if parent is not None and shapes.value(parent, SH.name) else ""
    return f"{owner_name}: {path}" if path else (owner_name or "constraint")


def _context(data, node):
    """For a blank node (an evidence node), name the claim or BGC that owns it."""
    if isinstance(node, URIRef):
        return node
    owners = [s for s, _, _ in data.triples((None, None, node))]
    return owners[0] if owners else node


def check_references(data):
    """Anchors must exist in PlantMetWiki (snapshot). Returns a list of result dicts."""
    out = []
    pw_file, met_file = SNAPSHOTS / "pmw_pathway_ids.txt", SNAPSHOTS / "pmw_metabolite_inchikeys.txt"
    if not (pw_file.exists() and met_file.exists()):
        print("note: snapshots/ missing, reference check skipped (run refresh_snapshots.py)", file=sys.stderr)
        return out
    pathways = set(pw_file.read_text().split())
    metabolites = set(met_file.read_text().split())
    for pred in (LODP.anchoredInPathway, RDF.object):
        for s, _, o in data.triples((None, pred, None)):
            if isinstance(o, URIRef) and str(o).startswith(PMW_PATHWAY) and str(o)[len(PMW_PATHWAY):] not in pathways:
                out.append({"severity": "Violation", "shape": "reference check", "focus": s, "value": o,
                            "message": "The PlantMetWiki pathway does not exist in the snapshot."})
    for s, _, o in data.triples((None, LODP.anchoredToMetabolite, None)):
        if str(o).startswith(INCHIKEY) and str(o)[len(INCHIKEY):] not in metabolites:
            out.append({"severity": "Violation", "shape": "reference check", "focus": s, "value": o,
                        "message": "The PlantMetWiki metabolite (InChIKey) does not exist in the snapshot."})
    return out


def validate(paths, shapes_dir=SHAPES_DIR, references=True):
    """Validate one or more Turtle files. Returns a dict with the results and the data graph."""
    data = load_graph(paths) if not isinstance(paths, Graph) else paths
    shapes = load_shapes(shapes_dir)
    vocab = Graph().parse(str(VOCAB), format="turtle")
    _, report, _ = pyshacl.validate(data, shacl_graph=shapes, ont_graph=vocab, inference="none",
                                    allow_warnings=True, meta_shacl=False, advanced=False)
    results = []
    for r in report.subjects(RDF.type, SH.ValidationResult):
        sev = SEVERITY.get(str(report.value(r, SH.resultSeverity)), "Violation")
        focus = report.value(r, SH.focusNode)
        results.append({
            "severity": sev,
            "shape": shape_label(shapes, report.value(r, SH.sourceShape)),
            "focus": _context(data, focus),
            "value": report.value(r, SH.value),
            "message": str(report.value(r, SH.resultMessage) or ""),
        })
    if references:
        results += check_references(data)
    return {"results": results, "data": data,
            "violations": sum(r["severity"] == "Violation" for r in results),
            "warnings": sum(r["severity"] == "Warning" for r in results)}


def format_report(res, max_examples=3):
    data, results = res["data"], res["results"]
    claims = sum(1 for _ in data.subjects(RDF.type, LODP.BGCPathwayLink)) \
        + sum(1 for _ in data.subjects(RDF.type, LODP.GeneMetaboliteAssociation)) \
        + sum(1 for _ in data.subjects(RDF.type, LODP.MetaboliteAnnotation)) \
        + sum(1 for _ in data.subjects(RDF.type, LODP.PathwayMembershipClaim))
    bgcs = sum(1 for _ in data.subjects(RDF.type, OBO.SO_0002357))
    lines = [f"{len(data)} triples; {claims} claims, {bgcs} BGC nodes",
             f"{res['violations']} violations, {res['warnings']} warnings", ""]
    grouped = defaultdict(list)
    for r in results:
        grouped[(r["severity"], r["message"])].append(r)
    for sev in ("Violation", "Warning", "Info"):
        items = [(k, v) for k, v in grouped.items() if k[0] == sev]
        if not items:
            continue
        lines.append(f"--- {sev.upper()}S ---")
        for (_, msg), rows in sorted(items, key=lambda kv: -len(kv[1])):
            lines.append(f"[{len(rows)}x] {msg}")
            lines.append(f"      shape: {rows[0]['shape']}")
            for r in rows[:max_examples]:
                v = f" (value: {_short(r['value'], None)})" if r["value"] is not None else ""
                lines.append(f"      at {_short(r['focus'], None)}{v}")
            if len(rows) > max_examples:
                lines.append(f"      ... and {len(rows) - max_examples} more")
        lines.append("")
    if not results:
        lines.append("Conforms: no violations and no warnings.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="Turtle files to validate together")
    ap.add_argument("--shapes", default=str(SHAPES_DIR), help="directory with the shape files")
    ap.add_argument("--strict", action="store_true", help="warnings also make the exit code 1")
    ap.add_argument("--no-references", action="store_true", help="skip the PlantMetWiki existence check")
    ap.add_argument("--max-examples", type=int, default=3)
    args = ap.parse_args(argv)
    missing = [f for f in args.files if not Path(f).exists()]
    if missing:
        print("not found:", ", ".join(missing), file=sys.stderr)
        return 2
    res = validate(args.files, args.shapes, references=not args.no_references)
    print(format_report(res, args.max_examples))
    return 1 if res["violations"] or (args.strict and res["warnings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
