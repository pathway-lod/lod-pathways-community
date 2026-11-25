# Serving the evidence graphs from a SPARQL endpoint (Oxigraph): plan

**Status: documentation only. Nothing here is implemented in the repositories.** Written to keep the idea for later. The only part tested so far is running the queries in a local, in-process store (`pyoxigraph`) that loaded the evidence graphs and called PlantMetWiki, Rhea and UniProt with `SERVICE`; the server and tunnel steps below were not run.

## Why

The [minimum information tiers](README.md) are written as SPARQL queries in [`sparql-examples-pmw`](https://github.com/pathway-lod/sparql-examples-pmw) (site: <https://pathway-lod.github.io/sparql-examples-pmw/>). They compute the connectivity to PlantMetWiki themselves, but they start from **our evidence graphs** (the Turtle files in [`../shape_constraints/rdf/`](../shape_constraints/rdf/) and [`../examples/`](../examples/)). A public endpoint such as PlantMetWiki cannot read files on our machines, so the queries have a placeholder `schema:target` (`https://pathway-lod.github.io/sparql-examples-pmw/evidence-graph`) and today they run only in a local store with `run_examples.py`. An endpoint that holds the evidence graphs would let anyone run the queries, and would give them a real target.

## Idea

Run [Oxigraph](https://github.com/oxigraph/oxigraph) as a small SPARQL server, load the evidence graphs into it, and let the queries use it as their entry point. The queries reach PlantMetWiki, Rhea, UniProt and OrthoDB with `SERVICE` from there.

## Steps

1. **Start the server**
   ```bash
   oxigraph serve --location /tmp/evidence-store --bind 127.0.0.1:7878
   ```
   Endpoint: `http://127.0.0.1:7878/query`; a query page is at <http://127.0.0.1:7878/>.
2. **Load the Turtle files** into the default graph (one graph for all pilots) or into a named graph per file:
   ```bash
   for f in shape_constraints/rdf/annotation.ttl shape_constraints/rdf/association.ttl \
            shape_constraints/rdf/bgc.ttl examples/sample_evidence_graph.ttl; do
     curl -X POST -H 'Content-Type: text/turtle' --data-binary @$f 'http://127.0.0.1:7878/store?default'
   done
   ```
   For a named graph per file use `?graph=<IRI>` instead of `?default`; queries then need `GRAPH` or `FROM`. With the four files above the local store held 87,823 triples.
3. **Query**
   ```bash
   curl -H 'Accept: application/sparql-results+json' --data-urlencode "query@query.rq" http://127.0.0.1:7878/query
   ```
4. **Point the queries at it**: replace the placeholder `schema:target` of the files in `examples/MinimumInformationTiers/` with the endpoint URL once it is stable.

## Sharing it

| Option | What it takes | Remarks |
|---|---|---|
| Local server for one person | the steps above | the simplest; nothing is shared |
| Temporary public link | a tunnel in front of the local server (for example `cloudflared tunnel --url http://127.0.0.1:7878` or `ngrok http 7878`) | works while the machine and tunnel run; Oxigraph has no authentication by default, so keep it read-only and short-lived |
| Permanent endpoint | the same server on a small VM (an institute server or a cloud instance), HTTPS, read-only, reloaded from the repository on a schedule | needs someone to own it; the placeholder target is then replaced |
| No server | query the Turtle files over HTTP with Comunica (the SIB site already uses it in the browser), together with the PlantMetWiki endpoint | needs the files on a public branch; the joins run in the client and the heavy queries are slow; `SERVICE` with these queries was not checked |
| Static results | a Jupyter notebook per case that runs the queries and keeps the output (see below) | no server; the results are a snapshot that the team can read and comment on |

GitHub Pages cannot run an endpoint (static files only).

## Static results in notebooks (complement or alternative)

A notebook per case (metabolomics, paired omics, gene clusters) could run each query against a local store or the endpoint and **keep the results in the notebook output**, so that the team can discuss counts without running anything: how many features, associations or clusters pass each tier, and examples of hits. Suggested content:

- a table of the tiers with the number of results, the run time, the date and the PlantMetWiki release (the queries depend on a live endpoint, so the results are a dated snapshot);
- the first rows of each result;
- the queries that did not finish (the notes in their comments) and what was tried, for example a `LIMIT` or a cached lookup of the PlantMetWiki metabolites;
- the results saved as CSV next to the notebook, so that a long query is not repeated.

Existing pilots already follow this pattern (`explore_results.ipynb` in three of them).

**Implemented** (first version, 2026-11-10): see [`notebooks/`](notebooks/). They run the queries in a local in-process store, not through an endpoint.

## Test results to date (local in-process store, 2026-11-10)

| Query | Result |
|---|---|
| `annotation-matches-plantmetwiki` | 2,015 features with a match, about 63 s |
| `gene-in-plantmetwiki-pathway` | 0 rows on the 1,293 associations of the MEANtools pilot (none of its genes is listed by Solyc locus in PlantMetWiki); the 2 pathways PC70 and PC968 that were found at first come from the single association of the sample graph |
| `gene-and-metabolite-in-same-pathway`, `coexpressed-in-cluster-one-in-pathway` | 0 rows (the data are missing in the graph) |
| `structure-similarity`, `coexpressed-in-cluster-both-in-pathway` | did not finish within the time limit |
| `rhea-step-between-metabolites` | did not finish; in one run the local store was killed by the system (probably out of memory) |
| `ortholog-in-pathway-species`, `gene-catalyses-the-transformation`, `ortholog-plus-ml-prediction` | 0 rows (written against the proposed data model) |
| `shared-chemical-class`, `similarity-link`, `coexpressed-in-same-cluster` | not run; they need data that the graphs do not have |

## Open questions

1. **Who hosts it**, and where? Institute server, cloud, or only local?
2. **How is it refreshed**? The graphs are generated by `shape_constraints/build_rdf.py` from the pilot results; the load would have to follow.
3. **Access**: public and read-only, or restricted? Any limit on query time, since the federated queries are heavy?
4. **One graph or one named graph per pilot**, and which IRIs?
5. **License and size** of the evidence graphs (the pilots' source data have different licenses; the ipecac supplementary files, for example, are not committed).
6. **Does the SIB tester need an endpoint** for these queries, or is the placeholder enough?
