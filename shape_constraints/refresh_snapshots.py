#!/usr/bin/env python3
"""
Snapshot which pathways and metabolites exist in PlantMetWiki, for the reference check in validate.py.

  python refresh_snapshots.py

Writes snapshots/pmw_pathway_ids.txt (PC numbers), snapshots/pmw_metabolite_inchikeys.txt (full InChIKeys)
and snapshots/SNAPSHOT_INFO.txt (date, endpoint, counts). Commit the files: they make validation reproducible.
"""

import datetime
import io
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).parent
ENDPOINT = "https://plantmetwiki.bioinformatics.nl/sparql"
QUERIES = {
    "pmw_pathway_ids.txt": ("""
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        SELECT DISTINCT ?id WHERE {
          ?pw a <http://vocabularies.wikipathways.org/wp#Pathway> ; dc:identifier ?iri .
          BIND(REPLACE(STR(?iri), "^.*/pathways/", "") AS ?id)
          FILTER(REGEX(?id, "^PC[0-9]+$"))
        }""", "id"),
    "pmw_metabolite_inchikeys.txt": ("""
        PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
        SELECT DISTINCT ?key WHERE {
          ?m a wp:Metabolite ; wp:bdbInChIKey ?ik .
          BIND(REPLACE(STR(?ik), "^.*/", "") AS ?key)
        }""", "key"),
}


def main():
    (HERE / "snapshots").mkdir(exist_ok=True)
    info = [f"endpoint: {ENDPOINT}", f"date: {datetime.date.today().isoformat()}"]
    for fname, (query, col) in QUERIES.items():
        r = requests.get(ENDPOINT, params={"query": query}, headers={"Accept": "text/csv"}, timeout=300)
        r.raise_for_status()
        values = sorted(set(pd.read_csv(io.StringIO(r.text), dtype=str)[col].dropna()))
        (HERE / "snapshots" / fname).write_text("\n".join(values) + "\n")
        info.append(f"{fname}: {len(values)} entries")
        print(fname, len(values))
    (HERE / "snapshots" / "SNAPSHOT_INFO.txt").write_text("\n".join(info) + "\n")


if __name__ == "__main__":
    main()
