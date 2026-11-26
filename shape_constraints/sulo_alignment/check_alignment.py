import csv
import sys
import glob

from rdflib.collection import Collection
from rdflib import Graph, Namespace, RDF, RDFS, OWL, BNode

SULO = Namespace("https://w3id.org/sulo/")
LODP = Namespace("https://example.org/lod-pathways/pilot/")

def to_iri_values(curie):
    prefix, _, local = curie.partition(":")
    namespaces  = {"lodp":LODP, "sulo":SULO}
    if prefix not in namespaces or not local:
        return None
    return namespaces[prefix][local]

def shorten_iri(iri):
    return str(iri).replace(str(LODP), "lodp:").replace(str(SULO), "sulo:")


sulo  = Graph().parse('sulo.ttl')
vocab = Graph().parse('../vocab/lodp.ttl')
alignment = Graph().parse('lodp_sulo_alignment.ttl')
data = Graph()

for path in sorted(glob.glob("../rdf/*.ttl")):
    data.parse(path)
rows = list(csv.DictReader(open('alignement.csv', encoding='utf-8-sig')))

shared = Graph()
for path in ("shared_ancestors.ttl", "shared_sulo_alignment.ttl"):
    shared.parse(path)

family = vocab + sulo + alignment + shared
def ancestors(clas):
    return set(family.transitive_objects(clas, RDFS.subClassOf))

def parent_properties(props):
    return set(family.transitive_objects(props, RDFS.subPropertyOf))

#check the pair of SULo classes that do not overlap

disjoint = set()

for a, b in sulo.subject_objects(OWL.disjointWith):
    disjoint.add(frozenset((a,b)))
for group in sulo.subjects(RDF.type, OWL.AllDisjointClasses):
    members = list(Collection(sulo, sulo.value(group, OWL.members)))
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            disjoint.add(frozenset([members[i], members[j]]))

def clash(classes_a, classes_b):
    above_a = set().union(*(ancestors(c) for c in classes_a))
    above_b = set().union(*(ancestors(c) for c in classes_b))
    for pair in disjoint:
        a,b = tuple(pair)
        if (a in above_a and b in above_b) or (b in above_a and a in above_b):
            return a, b
    return None

def allow(node):  # allow missing or owl:thing, so on in an empty list
    if node is None or node == OWL.Thing:
        return []

    if isinstance(node, BNode) and sulo.value(node, OWL.unionOf) is not None:
        return list(Collection(sulo, sulo.value(node, OWL.unionOf)))
    return [node]


classes = {c for c in vocab.subjects(RDF.type, OWL.Class) if str(c).startswith(LODP)}
relations = {p for p in vocab.subjects(RDF.type, OWL.ObjectProperty) if str(p).startswith(LODP)}
failed = []

def report(number, title, problems):
    status = "FAIL" if problems else "PASS"
    print(f"check {number} {title}".ljust(72, '.')+" "+status)

    for p in problems[:10]:
        print("     -" + p)

    if len(problems)>10:
        print(f"    ... and {len(problems) - 10} more")

    if problems:
        failed.append(number)

problems = []
in_table = {to_iri_values(r['term']) for r in rows}

for term in sorted(classes | relations):
    if term not in in_table:
        problems.append(f"{shorten_iri(term)} has no row")

for r in rows:
    if to_iri_values(r['term']) not in classes| relations:
        problems.append(f"{r['term']} is not in class or relation in the lodp.ttl file.")
    if r["confidence"] not in ('sure','discuss','inherits'):
        problems.append(f"{r['term']}: confidence should be one among sure, inherits, or discuss")
    if r['confidence'] =='sure' and not r['parent']:
        problems.append(f"{r['term']}: sure but not a parent")
    if r['confidence'] == 'inherits' and r['parent']:
        problems.append(f"{r['term']} inherits but a parent exists.")
    if not r['reason']:
        problems.append(f"{r['term']}: the reason is not given")

report(1, "The table is complete and filled in", problems)

problems = []

for r in rows:
    if not r['parent']:
        continue

    parent = to_iri_values(r['parent'])
    official = sulo.value(parent, RDFS.label) if parent is not None else None
    if official is None:
        problems.append(f"{r['term']}: {r['parent']} does not exist in SULO")
    elif str(official).lower() != r['parent_label'].lower():
        problems.append(f"{r['term']}: {r['parent']} is called {official} now {r['parent_label']}")
    elif r['kind'] == 'class' and (parent, RDF.type, OWL.Class) not in sulo:
        problems.append(f"{r['term']} is a class but {r['parent']} is not a clas.")
    elif r['kind'] != 'class' and (parent, RDF.type, OWL.Class) in sulo:
        problems.append(f"{r['term']} is a relation but {r['parent']} is a class.")

report(2, "Every kind exists in SULO, with right lable and kind", problems)

problems = []

expected = {(to_iri_values(r['term']), to_iri_values(r['parent'])) for r in rows if r['parent']}

in_file = {(s,o) for s,p,o in alignment if p in (RDFS.subClassOf, RDFS.subPropertyOf)}
for s, o in sorted(expected - in_file):
    problems.append(f"{shorten_iri(s)} -> {shorten_iri(o)} is the table but does not exist in the file. re-run make-alignment.py script")
for s, o in sorted(in_file - expected):
    problems.append(f"{shorten_iri(s)} -> {shorten_iri(o)} is in the file but does not exist in the table, re-run make alignment and re-check.")

report(3, "RDF file matches the CSV dataset", problems=problems)

problems = []

for c in sorted(classes):
    if SULO.Object not in ancestors(c) and SULO.Process not in ancestors(c):
        problems.append(f"{shorten_iri(c)} reaches neither sulo:Object nor sulo:Process")

report(4, "Every class reaches sulo:Object or sulo:Process", problems)

problems = []

for c in sorted(classes):
    pair = clash([c],[c])
    if pair:
        problems.append(f"{shorten_iri(c)} is under both {shorten_iri(pair[0])} and {shorten_iri(pair[1])}, which exclude each other.")

report(5, "No class is under two class that exclude each other", problems)

problems, notes = [], []
types = {}
for thing, cls, in data.subject_objects(RDF.type):
    types.setdefault(thing, set()).add(cls)

for prop in sorted(relations):
    for parent in parent_properties(prop) - {prop}:
        for side, rule in (("subject", RDFS.domain)), (("object", RDFS.range)):
            needed = allow(sulo.value(parent,rule))
            if not needed:
                continue
            things = [s for s, o in data.subject_objects(prop)] if side =='subject' else [o for s, o in data.subject_objects(prop)]
            bad, ok, unknown = 0,0,0
            for thing in things:
                known = {t for t in types.get(thing, set()) if SULO.Object in ancestors(t) or SULO.Process in ancestors(t)}
                if not known:
                    unknown +=1
                elif any(n in ancestors(t) for t in known for n in needed):
                    ok += 1
                elif all(clash(known, [n]) for n in needed):
                    bad += 1
                else:
                    ok +=1

            need = " or ".join(shorten_iri(n) for n in needed)
            if bad:
                problems.append(f"{shorten_iri(prop)}: {bad} {side}s in the data can never be {need}" f"(required by its parent {shorten_iri(parent)})")
            if ok:
                notes.append(f"{shorten_iri(prop)}: {ok} {side}s as {shorten_iri(parent)} requires")
            if unknown:
                notes.append(f"{shorten_iri(prop)}:{unknown} {side}s have no SULO class yet " f"{shorten_iri(parent)} would make them {need}")
                
report(6, "The pilots data fits the parents' domain and range", problems=problems)   


print("\nNotes:")
for n in notes:
    print("     "+n)
print('\nAll checks passed' if not failed else f"\nFAILED: check {', '.join(map(str, failed))}")
sys.exit(1 if failed else 0)