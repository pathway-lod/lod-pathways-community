"""Helpers of the notebooks: run a minimum-information tier (a SPARQL query of sparql-examples-pmw) on the evidence graphs.

The queries are read from the repository pathway-lod/sparql-examples-pmw (a sibling checkout if there is one, otherwise the
published files on GitHub). Each query runs in its own process with a time limit; the result is kept as a CSV in results/ and
a line in results/summary.csv (status, number of rows, seconds, date, PlantMetWiki release), so that the notebooks show a dated
snapshot that can be read and discussed without running anything.
"""
import csv
import datetime
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from rdflib import Graph, Namespace

HERE = Path(__file__).parent
REPO = HERE.parent.parent                                     # lod-pathways-community
RESULTS = HERE / "results"
SIBLING = REPO.parent / "sparql-examples-pmw" / "examples" / "MinimumInformationTiers"
RAW = "https://raw.githubusercontent.com/pathway-lod/sparql-examples-pmw/main/examples/MinimumInformationTiers/{}.ttl"
SH, SCHEMA, RDFS = Namespace("http://www.w3.org/ns/shacl#"), Namespace("https://schema.org/"), Namespace("http://www.w3.org/2000/01/rdf-schema#")
PMW = "https://plantmetwiki.bioinformatics.nl/sparql"

DATA = {
    "annotation": REPO / "shape_constraints/rdf/annotation.ttl",
    "association": REPO / "shape_constraints/rdf/association.ttl",
    "bgc": REPO / "shape_constraints/rdf/bgc.ttl",
    "sample": REPO / "examples/sample_evidence_graph.ttl",
}


def load_query(name):
    """The query text, its comment and keywords from the Turtle file of the tier."""
    local = SIBLING / f"{name}.ttl"
    text = local.read_text() if local.exists() else urllib.request.urlopen(RAW.format(name)).read().decode()
    g = Graph().parse(data=text, format="turtle")
    ex = next(g.subjects(SCHEMA.target, None))
    return {"name": name, "query": str(next(g.objects(ex, SH.select))), "comment": str(next(g.objects(ex, RDFS.comment))),
            "keywords": sorted(str(k) for k in g.objects(ex, SCHEMA.keywords))}


_RELEASE = []


def pmw_release():
    """The PlantMetWiki release that the live endpoint serves (taken from the IRI of a pathway)."""
    if _RELEASE:
        return _RELEASE[0]
    q = "SELECT ?x WHERE { ?x a <http://vocabularies.wikipathways.org/gpml#Interaction> } LIMIT 1"
    req = urllib.request.Request(PMW, data=urllib.parse.urlencode({"query": q}).encode(), headers={"Accept": "application/sparql-results+json"})
    iri = json.load(urllib.request.urlopen(req, timeout=60))["results"]["bindings"][0]["x"]["value"]
    _RELEASE.append(re.search(r"/Pathway/[A-Z]+[0-9]+_(r[0-9.]+_[0-9-]+)", iri).group(1))
    return _RELEASE[0]


def run(name, data, case, timeout=150, max_rows=2000):
    """Run one tier. Returns a dict with status ('rows', 'no rows' or 'timeout'), n_rows, seconds and a DataFrame."""
    q = load_query(name)
    job = json.dumps({"query": q["query"], "data": [str(DATA[d]) for d in data], "max_rows": max_rows})
    out = {"tier": name, "case": case, "date": datetime.date.today().isoformat(), "pmw_release": pmw_release(), "timeout_s": timeout}
    try:
        p = subprocess.run([sys.executable, str(HERE / "mi_worker.py")], input=job, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        out.update(status="timeout", n_rows=None, seconds=None)
        return out | {"table": pd.DataFrame(), "comment": q["comment"]}
    if p.returncode != 0:
        lines = p.stderr.strip().splitlines()
        out.update(status="error: " + (lines[-1][:200] if lines else ("killed by the system (probably out of memory)" if p.returncode == -9 else f"process ended with code {p.returncode}")), n_rows=None, seconds=None)
        return out | {"table": pd.DataFrame(), "comment": q["comment"]}
    r = json.loads(p.stdout)
    table = pd.DataFrame(r["rows"], columns=r["vars"])
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / f"{name}.csv", index=False)
    out.update(status="rows" if r["n_rows"] else "no rows", n_rows=r["n_rows"], seconds=r["seconds"])
    return out | {"table": table, "comment": q["comment"]}


def record(result):
    """Keep the result of a tier: one small JSON file per tier in results/status/ and results/summary.csv rebuilt from them
    (so that notebooks run at the same time do not overwrite each other)."""
    status = RESULTS / "status"
    status.mkdir(parents=True, exist_ok=True)
    cols = ["tier", "case", "status", "n_rows", "seconds", "timeout_s", "date", "pmw_release"]
    (status / f"{result['tier']}.json").write_text(json.dumps({c: result.get(c) for c in cols}))
    rows = [json.loads(p.read_text()) for p in status.glob("*.json")]
    with open(RESULTS / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["case"], r["tier"])))


def local_count(data, query):
    """A quick count on the local graphs (for the denominators): the first value of the first row."""
    job = json.dumps({"query": query, "data": [str(DATA[d]) for d in data], "max_rows": 1})
    p = subprocess.run([sys.executable, str(HERE / "mi_worker.py")], input=job, capture_output=True, text=True, timeout=120)
    return int(json.loads(p.stdout)["rows"][0][0])
