import glob
from collections import Counter
from rdflib import Graph, RDFS, RDF, OWL

LODP = "https://example.org/lod-pathways/pilot/"

vocab = Graph()
vocab.parse("../vocab/lodp.ttl")

data = Graph()
for path in sorted(glob.glob("../rdf/*.ttl")): # used to find the file iin the upper level that ends in .ttl
    data.parse(path)
print(f"Vocabulary: {len(vocab)} triples. Pilot data: {len(data)} triples.")

#How often is that class used
class_usage = Counter(o for o in data.objects(None, RDF.type))
property_usage = Counter(p for p in data.predicates())

def shorten_iri(iri):
    return str(iri).replace(LODP, "lodp:")


for kind, label in ((OWL.Class, "CLASSES"), (OWL.ObjectProperty, "OBJECT PROPERTIES"), (OWL.DatatypeProperty, "DATATYPE PROPERTIES")):
    terms = sorted(t for t in vocab.subjects(RDF.type, kind) if str(t).startswith(LODP))
    print(f"\n{label}: {len(terms)}")


    for t in terms:
        used = class_usage[t] if kind == OWL.Class else property_usage[t]
        parents = " ".join(shorten_iri(p) for p in vocab.objects(t, RDFS.subClassOf))
        print(f' {shorten_iri(t):<34} used  {used:>5} x {("parent: " + parents) if parents else " "}')