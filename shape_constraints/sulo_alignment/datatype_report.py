# SULO has one datatype property sulo:hasValue and it is functional i.e. a thing can have at most oine value. According to their paper, no other data property is admitted. Our vocabulary has 45 datatype properties : scores, tiers, names, identifiers.

#This file measures if nothing in our datatype has two values, if it does we do not follow the SOLID principle.

import csv
import glob
from collections import Counter

from rdflib import Graph, RDF, RDFS, OWL,Literal

LODP = "https://example.org/lod-pathways/pilot/"
NUMBER_TYPES = ('decimal','float','integer','double')

vocabs = Graph().parse("../vocab/lodp.ttl")
data = Graph()

for path in sorted(glob.glob("../rdf/*.ttl")):
    if path:
        data.parse(location=path, format="turtle")

properties = sorted(p for p in vocabs.subjects(RDF.type, OWL.DatatypeProperty) if str(p).startswith(LODP))

values_per_thing = Counter()
for s, p, o in data:
    if p in properties and isinstance(o, Literal):
        values_per_thing[s] +=1

two_or_more_values = sum(1 for n in values_per_thing.values() if n >= 2)

rows = []

for p in properties:
    value_type = str(vocabs.value(p, RDFS.range) or "").split("#")[-1]
    local = str(p).replace(LODP, "")
    rows.append({
        "property":"lodp:" + local,
        "label":str(vocabs.value(p, RDFS.label) or ""),
        "used_in_data":len(list(data.subject_objects(p))),
        "value_types":value_type,
        "solid_class":"sulo:Quantity" if value_type in NUMBER_TYPES else "sulo:InformationObject",
        "new_class_name":"lodp:" + local[0].upper() + local[1:]
    })

with open("datatype_properties_SULO_SOLID.csv", 'w', newline="", encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

print(f"{len(properties)} datatype properties: {sum(1 for r in rows if r['used_in_data'])} are used in data.")
print(f"{sum(r['solid_class'] == 'sulo:Quantity' for r in rows)} hold numbers (-> sulo:Quantity),"f"{sum(r['solid_class'] != 'sulo:Quantity' for r in rows)} hold codes or text (-> sulo:InformationObject).")
print(f"{len(values_per_thing)} things carry value {two_or_more_values} of them carry two or more.")
print("Wrote data types in 'datatype_properties_SULO_SOLID.csv' file.")