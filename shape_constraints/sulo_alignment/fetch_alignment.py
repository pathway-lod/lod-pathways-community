import os
import glob
import urllib.request
from rdflib import Graph, RDF, RDFS, URIRef

LODP = 'https://example.org/lod-pathways/pilot/'
SULO = 'https://w3id.org/sulo/'

data = Graph()

for path in sorted(glob.glob("../rdf/*.ttl")):
    data.parse(path)

print(f'{len(data)} triples in the pilot data.')

used = sorted(c for c in set(data.objects(None, RDF.type)) if isinstance(c, URIRef) and not str(c).startswith((LODP, SULO)))
print(f"{len(used)} borrowed classes are used in the pilot data")

SOURCES = {
    "http://purl.obolibrary.org/obo/ECO_":"https://raw.githubusercontent.com/evidenceontology/evidenceontology/master/eco.owl",
    "http://purl.obolibrary.org/obo/SO_":"https://raw.githubusercontent.com/The-Sequence-Ontology/SO-Ontologies/master/Ontology_Files/so.owl",
    "http://edamontology.org/":"https://raw.githubusercontent.com/edamontology/edamontology/main/EDAM_dev.owl"
}

os.makedirs("downloads", exist_ok=True)


out = Graph()

for start, url in SOURCES.items():
    terms = [t for t in used if str(t).startswith(start)]
    if not terms:
        continue

    path = os.path.join("downloads", url.rsplit("/", 1)[-1])
    if not os.path.exists(path):
        print(f"downloading {url}")
        urllib.request.urlretrieve(url,path)

    onto = Graph().parse(path)

    for term in terms:
        for ancestor in onto.transitive_objects(term, RDFS.subClassOf):
            if not isinstance(ancestor, URIRef):
                continue

            label = onto.value(ancestor, RDFS.label)
            if label is not None:
                out.add((ancestor, RDFS.label, label))
            for parent in onto.objects(ancestor, RDFS.subClassOf):
                if isinstance(parent, URIRef):
                    out.add((ancestor, RDFS.subClassOf, parent))
    print(f"  {len(terms)} terms from {path}")

for term in used:
    if not str(term).startswith(tuple(SOURCES)):
        print(f"    no source known for {term}")

out.serialize("shared_ancestors.ttl" ,format='turtle')
print(f'wrote {len(out)} triples to shared_ancestors.ttl')