from rdflib import Graph, Namespace, RDF, RDFS, OWL, BNode
from rdflib.collection import Collection

SULO = Namespace("https://w3id.org/sulo/")

g = Graph()
g.parse("sulo.ttl")
print(f"SULO has length of {len(g)} triples")

def name(node):
    if isinstance(node, BNode):
        members = g.value(node, OWL.unionOf)
        if members is not None:
            return " or ".join(name(m) for m in Collection(g, members))
        return ("complex expression")
    if node ==OWL.Thing:
        return 'anything'
    return str(node).replace(str(SULO), "sulo:")

print("\nCLASSES (name | parent | definition )")
for c in sorted (g.subjects(RDF.type, OWL.Class)):
    if isinstance(c, BNode):
        continue
    parents = [name(p) for p in g.objects(c, RDFS.subClassOf) if not isinstance(p, BNode)]
    definition = g.value(c, RDFS.comment)
    print(f" {name(c):<24} | {', '.join(parents) or '(top)':<22} | {definition}")

print("\nRELATIONS (name | domain -> range)")
for p in sorted(g.subjects(RDF.type, OWL.ObjectProperty)) + sorted(g.subjects(RDF.type, OWL.DatatypeProperty)):
    domain = g.value(p, RDFS.domain)
    rng = g.value(p, RDFS.range)
    print(f'{name(p):<22} | {name(domain) if domain is not None else "-"} -> {name(rng) if rng is not None else "-"}')

print("\nCLASSES THAT EXCLUDE EACH OTHER")
for a, b in g.subject_objects(OWL.disjointWith):
    print(f" {name(a)} X {name(b)}")

for group in g.subjects(RDF.type, OWL.AllDisjointClasses):
    members = Collection(g, g.value(group, OWL.members))
    print(" " + " X ".join(name(m) for m in members))