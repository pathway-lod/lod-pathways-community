import csv
import glob

from rdflib import Graph, RDF, RDFS, URIRef

PREFIXES = {
    "ECO":"http://purl.obolibrary.org/obo/ECO_",
    "SO":"http://purl.obolibrary.org/obo/SO_",
    "edam":"http://edamontology.org/",
    "sulo":"https://w3id.org/sulo/"
}

def to_iri(curie):
    prefix, _, local = curie.partition(":")
    return URIRef(PREFIXES[prefix] + local)

def shorten_iri(iri):
    for prefix, start in PREFIXES.items():
        if str(iri).startswith(start):
            return prefix + ":" + str(iri)[len(start):]

    return str(iri)

sulo = Graph().parse("sulo.ttl")
chains = Graph().parse('shared_ancestors.ttl')
rows = list(csv.DictReader(open("shared_top_class.csv", encoding='utf-8-sig')))

top = {to_iri(r['term']):to_iri(r['parent']) for r in rows}
for r in rows:
    if(to_iri(r['parent']), RDF.type, None) not in sulo:
        raise SystemExit(f"{r['parent']} does not exist in sulo")

data = Graph()
for path in sorted(glob.glob("../rdf/*.ttl")):
    data.parse(path)

used = sorted(c for c in set(data.objects(None, RDF.type)) if (c, RDFS.subClassOf,None) in chains)
print(f"{len(used)} borrowed class to place")

def above_in_sulo(cls):
    return set(sulo.transitive_objects(cls, RDFS.subClassOf))

placed = 0

for term in used:
    above = set(chains.transitive_objects(term, RDFS.subClassOf))
    found = {top[a]: a for a in above if a in top}

    answers = [p for p in found if not any (p !=q and p in above_in_sulo(q) for q in found)]

    if len(answers) == 1:
        placed += 1
        parent = answers[0]
        print(f"    {shorten_iri(term):<22} {shorten_iri(parent):<24} via {shorten_iri(found[parent])}")
    elif len(answers) >1:
        print(f"    {shorten_iri(term):<22} ? conflict: {", ".join(shorten_iri(p) for p in answers)}")
    else:
        roots  = [a for a in above if (a, RDFS.subClassOf, None) not in chains]
        print(f"    {shorten_iri(term):<22} ? no decided top class. top classes: {", ".join(shorten_iri(r) for r in roots)}")

with open("shared_sulo_alignment.ttl", "w", encoding="utf-8") as f:
    f.write("# Top classes of shared ontologies placed in SULO\n")
    f.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n\n")
    for r in rows:
        f.write(f"#{r['confidence']}: {r['reason']}\n")
        f.write(f"<{to_iri(r['term'])}> rdfs:subClassOf <{to_iri(r['parent'])}> . #{r['parent_label']}\n\n")

print(f"\n{len(used)} shared classes: {placed} placed automatically from {len(rows)} hand made top class rows, {len(used) - placed} still needs a row")
