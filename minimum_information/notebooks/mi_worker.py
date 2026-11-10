"""Worker: load Turtle files into an in-process Oxigraph store and run one SPARQL query. Called by mi.py in a subprocess
so that a query that does not finish can be stopped. Input (JSON on stdin): {"query": str, "data": [paths], "max_rows": int}.
Output (JSON on stdout): {"vars": [...], "rows": [[...]], "n_rows": int, "seconds": float}."""
import json
import sys
import time

import pyoxigraph as ox

job = json.load(sys.stdin)
store = ox.Store()
for path in job["data"]:
    store.load(path=path, format=ox.RdfFormat.TURTLE)
t0 = time.time()
res = store.query(job["query"])
names = [v.value for v in res.variables]
rows, n = [], 0
for sol in res:
    n += 1
    if len(rows) < job["max_rows"]:
        rows.append([None if sol[v] is None else sol[v].value for v in res.variables])
print(json.dumps({"vars": names, "rows": rows, "n_rows": n, "seconds": round(time.time() - t0, 1), "triples": len(store)}))
