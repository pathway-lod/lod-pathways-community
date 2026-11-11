import csv

rows = list(csv.DictReader(open('alignement.csv', encoding='utf-8-sig')))

lines = [
    "# Alignment of the lodp: vocabulary to SULO. Made by this file from alignment.csv.",
    "",
    "@prefix lodp: <https://example.org/lod-pathways/pilot/> .",
    "@prefix sulo: <https://w3id.org/sulo/> .",
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> ."
    "",
    "<https://example.org/lod-pathways/pilot/sulo-alignment> a owl:Ontology ;",
    '   rdfs:label "Alignment of the lodp: vocabulary to SULO (draft)" ;',
    "   owl:imports <https://w3id.org/sulo/sulo.ttl>  .",
    "",
]

written = 0

for row in rows:
    if not row["parent"]:
        continue
    if row['kind']=='class':
        relation='rdfs:subClassOf'
    else:
        relation='rdfs:subPropertyOf'
    lines.append(f"# {row['confidence']}: {row['reason']}")
    lines.append(f"{row['term']} {relation} {row['parent']} .  # {row['parent_label']}")
    lines.append("")
    written+=1

with open("lodp_sulo_alignment.ttl", 'w', encoding='utf-8') as f:
    f.write("\n".join(lines))

print(f"{written} of {len(rows)} rows have a parent -> wrote lodp_sulo_alignment.ttl")