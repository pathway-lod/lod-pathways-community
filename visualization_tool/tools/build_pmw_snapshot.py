#!/usr/bin/env python3
"""
Build the PlantMetWiki (PMW) snapshot for the global view's "PMW" layout (TEST, 2026-11-11).

Purpose
  Query the PMW SPARQL endpoint once and write a compact JSON the viewer loads instead of querying PMW live:
  every pathway (PlantCyc pathways "PC" and single orphan reactions "RC") with title, group and classes, and an
  index from data-node IRI (metabolite, protein, gene product) to the pathways it is part of. The viewer maps a
  claim's anchor IRIs through this index onto the groups of the PMW ring. See docs/pmw-structure.md.

Inputs
  - PMW SPARQL endpoint (default https://plantmetwiki.bioinformatics.nl/sparql; network access needed)
  - tools/pmw_class_groups.csv: PlantCyc pathway class -> group of the ring (hand-reviewable; generated 2026-11-11
    from name rules, see the session notes). A pathway's group = the most frequent group among its classes,
    ignoring "(bookkeeping)" classes (Super-Pathways, Metabolic-Clusters, ...); ties go to the earlier group in
    GROUPS. Only bookkeeping classes -> "Super-pathways"; RC orphan reactions -> "Single reactions".
  - --old-pc (optional): CSV pc,plantcyc_id[,title] of an older PMW release. Its bare pathway IRIs
    (.../pathways/PC<n>) are added as aliases that point to the pathway with the same PlantCyc id today, because the
    PC numbers were reassigned between releases (the repository's pilot RDF uses the old numbers).

Output
  --out JSON (default public/data/pmw_snapshot.json):
    { release, built, endpoint, partOf: predicate IRI, groups: [label], pathways: [[key, title, groupIndex, [classes], iri]],
      nodes: {iri: [pathwayIndex, ...]}, alias: {iri: pathwayIndex} }
  Pathways are sorted by group, then first class, then key, so the ring order is deterministic.

Run (from visualization_tool/; standard library only)
  python tools/build_pmw_snapshot.py --old-pc ../pilots/pairedomics_overlap/data/plantmetwiki_pc_pathways.csv
"""
import argparse, csv, datetime, io, json, re, sys, urllib.parse, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROUPS = [  # order on the ring, clockwise from 12 o'clock; must match the group names in pmw_class_groups.csv
    "Flavonoids & phenylpropanoids", "Terpenoids & sterols", "Alkaloids & N/S compounds", "Other specialized",
    "Hormones", "Lipids", "Carbohydrates & cell wall", "Amino acids & nitrogen", "Nucleotides",
    "Cofactors & vitamins", "Energy & central", "Inorganic & detox", "Super-pathways", "Single reactions",
]
BOOKKEEPING = "(bookkeeping)"
# drawing weight of one pathway per group on the ring: the 1,316 single orphan reactions would otherwise take over
# half of the circle, so they are drawn at a quarter of their count (the viewer labels the sector as scaled)
GROUP_WEIGHT = {"Single reactions": 0.25}
PAGE = 10000  # Virtuoso returns at most 10,000 rows per query, and cannot page past them (OFFSET + ORDER BY fails
              # with SR353 beyond 10,000 sorted rows), so big results are split by pathway instead (BATCH)
BATCH = 150   # pathways per data-node query (~17 nodes per pathway on average)
PFX = """PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dct: <http://purl.org/dc/terms/>
"""


def sparql(endpoint, query):
    data = urllib.parse.urlencode({"query": PFX + query}).encode()
    req = urllib.request.Request(endpoint, data=data, headers={"Accept": "text/csv", "User-Agent": "lodviz-snapshot"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def capped(endpoint, query):
    rows = sparql(endpoint, query)
    if len(rows) >= PAGE:
        sys.exit(f"query hit the {PAGE}-row limit, split it: {query[:80]}...")
    print(f"  {len(rows)} rows", file=sys.stderr)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", default="https://plantmetwiki.bioinformatics.nl/sparql")
    ap.add_argument("--groups", default=HERE / "pmw_class_groups.csv")
    ap.add_argument("--old-pc", help="CSV pc,plantcyc_id of an older release (bare PC IRIs become aliases)")
    ap.add_argument("--out", default=HERE.parent / "public" / "data" / "pmw_snapshot.json")
    a = ap.parse_args()

    class_group = {r["class"]: r["group"] for r in csv.DictReader(open(a.groups, encoding="utf-8"))}
    unknown = sorted({g for g in class_group.values() if g not in GROUPS and g != BOOKKEEPING})
    if unknown:
        sys.exit(f"groups in {a.groups} not in GROUPS: {unknown}")

    print("pathways ...", file=sys.stderr)
    pws = capped(a.endpoint, """SELECT ?pw ?title ?pwy WHERE { ?pw a wp:Pathway ; dc:title ?title
        OPTIONAL { ?pw v:plantcycId ?pwy } } ORDER BY ?pw""")
    print("classes ...", file=sys.stderr)
    cls = capped(a.endpoint, """SELECT ?pw ?c WHERE { ?pw a wp:Pathway ; v:gpmlProperty ?gp .
        ?gp v:key ?k ; v:value ?c FILTER(STRSTARTS(?k, "Type")) } ORDER BY ?pw ?c""")
    print("data nodes ...", file=sys.stderr)
    nodes, iris = [], sorted(r["pw"] for r in pws)
    for i in range(0, len(iris), BATCH):
        vals = " ".join(f"<{x}>" for x in iris[i:i + BATCH])
        nodes += capped(a.endpoint, f"""SELECT DISTINCT ?m ?pw WHERE {{ VALUES ?pw {{ {vals} }}
            ?m dct:isPartOf ?pw ; a ?t VALUES ?t {{ wp:Metabolite wp:Protein wp:GeneProduct }} }}""")

    classes = defaultdict(list)
    for r in cls:
        classes[r["pw"]].append(r["c"])
    release = Counter(re.sub(r"^.*/(PC|RC)\d+_", "", r["pw"]) for r in pws).most_common(1)[0][0]

    recs = []
    for r in pws:
        iri, cs = r["pw"], sorted(set(classes.get(r["pw"], [])))
        is_rc = "/pathways/RC" in iri
        if is_rc:
            g = "Single reactions"
        else:
            votes = Counter(class_group.get(c, BOOKKEEPING) for c in cs)
            votes.pop(BOOKKEEPING, None)
            g = min(votes, key=lambda x: (-votes[x], GROUPS.index(x))) if votes else "Super-pathways"
        key = r["pwy"] or re.sub(r"^.*/pathways/((?:PC|RC)\d+)_.*$", r"\1", iri)
        recs.append((GROUPS.index(g), cs[0] if cs else "", key, r["title"], cs, iri))
    recs.sort(key=lambda x: (x[0], x[1].lower(), x[2]))
    index = {rec[5]: i for i, rec in enumerate(recs)}

    node_map = defaultdict(list)
    for r in nodes:
        if r["pw"] in index:
            node_map[r["m"]].append(index[r["pw"]])

    alias = {}
    if a.old_pc:
        by_key = {rec[2]: i for i, rec in enumerate(recs)}
        base = "http://rdf-plantmetwiki.bioinformatics.nl/pathways/"
        for r in csv.DictReader(open(a.old_pc, encoding="utf-8")):
            if r.get("plantcyc_id") in by_key:
                alias[base + r["pc"]] = by_key[r["plantcyc_id"]]

    out = {
        "release": release, "built": datetime.date.today().isoformat(), "endpoint": a.endpoint,
        "aliasSource": Path(a.old_pc).name if a.old_pc else None,
        "partOf": "http://purl.org/dc/terms/isPartOf",  # how data nodes are linked to their pathways (query above)
        "groups": GROUPS, "groupWeight": [GROUP_WEIGHT.get(g, 1) for g in GROUPS],
        "pathways": [[k, t, g, cs, iri] for g, _, k, t, cs, iri in recs],
        "nodes": node_map, "alias": alias,
    }
    Path(a.out).write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    per_group = Counter(rec[0] for rec in recs)
    print(f"release {release}: {len(recs)} pathways, {len(node_map)} data nodes, {len(alias)} aliases -> {a.out}",
          file=sys.stderr)
    for i, g in enumerate(GROUPS):
        print(f"  {per_group[i]:5d}  {g}", file=sys.stderr)


if __name__ == "__main__":
    main()
