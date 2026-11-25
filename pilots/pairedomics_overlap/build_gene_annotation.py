"""Gene annotation graph for the paired-omics pilot: the links that the minimum-information tiers need.

For every tomato gene of the MEANtools associations of the evidence graph (shape_constraints/rdf/association.ttl) it writes
  lodp:uniprot      the UniProt entry of the gene (Ensembl Plants locus -> UniProt, snapshot data/uniprot_tomato.tsv.gz)
  lodp:ecNumber     the EC numbers UniProt gives to that entry
  lodp:orthologOf   a UniProt enzyme that PlantMetWiki lists in a pathway and that is in the same OrthoDB group
                    as the gene's UniProt entry (OrthoDB SPARQL endpoint, queried live)
  lodp:orthologGroup  the OrthoDB group (its id contains the taxonomic level, e.g. 42360at4069)

This is a supporting graph, not a claim graph: it does not follow the shapes of ../../shape_constraints and is not
validated by them. It is what the tiers `gene-in-plantmetwiki-pathway` (UniProt and EC branches) and
`ortholog-in-pathway-species` read.

It also writes results/feature_annotation.ttl: the MS1 (mass only) annotation of the MEANtools features that this
pilot computed (results/metabolite_pathway_map.csv), as lodp:MetaboliteAnnotation nodes in the format of
shape_constraints/rdf/annotation.ttl, so that the tiers that start from an annotated feature can run on the paired-omics
data. A mass matches several compounds, so one feature can have several annotations: this is the weakest identification level.

Run:  python build_gene_annotation.py            (needs internet; about 5 min)
Writes results/gene_annotation.ttl and results/feature_annotation.ttl
"""
import re, sqlite3, sys, time
from datetime import date
from pathlib import Path
import pandas as pd, requests

HERE = Path(__file__).parent
PMW = "https://plantmetwiki.bioinformatics.nl/sparql"
ODB = "https://sparql.orthodb.org/sparql/"
CHUNK = 150


def sparql(endpoint, query, post=False, timeout=240):
    kw = dict(headers={"Accept": "application/sparql-results+json"}, timeout=timeout)
    r = requests.post(endpoint, data={"query": query}, **kw) if post else requests.get(endpoint, params={"query": query}, **kw)
    r.raise_for_status()
    return [{k: v["value"] for k, v in b.items()} for b in r.json()["results"]["bindings"]]


def genes_of_associations():
    ttl = (HERE.parent.parent / "shape_constraints" / "rdf" / "association.ttl").read_text()     # the evidence graph the tiers read
    return sorted(set(re.findall(r"Gene/Summary\?g=(Solyc\d+g\d+)", ttl)))


def pmw_enzymes():
    rows = sparql(PMW, """PREFIX v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>
PREFIX gpml: <http://vocabularies.wikipathways.org/gpml#>
SELECT DISTINCT ?a WHERE { ?e a gpml:DataNode ; v:gpmlProperty ?b . ?b v:key "AlternativeId_Uniprot" ; v:value ?a }""")
    ok = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$")   # UniProt accession format
    return sorted({r["a"] for r in rows if ok.match(r["a"])})


def orthodb_groups(accessions):
    out = {}
    for i in range(0, len(accessions), CHUNK):
        vals = " ".join(f"<http://purl.uniprot.org/uniprot/{a}>" for a in accessions[i:i + CHUNK])
        q = f"""PREFIX odb: <http://purl.orthodb.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?u ?og WHERE {{ VALUES ?u {{ {vals} }} ?og a odb:OrthoGroup ; odb:hasMember/rdfs:seeAlso ?u }}"""
        for b in sparql(ODB, q, post=True):
            out.setdefault(b["u"].rsplit("/", 1)[-1], set()).add(b["og"].rsplit("/", 1)[-1])
        print(f"  OrthoDB {min(i + CHUNK, len(accessions))}/{len(accessions)}", file=sys.stderr)
    return out


def write_feature_annotation():
    mm = pd.read_csv(HERE / "results" / "metabolite_pathway_map.csv")[["feature", "adduct", "key14", "ppm_error"]].drop_duplicates()
    L = ["@prefix lodp: <https://example.org/lod-pathways/pilot/> .", "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .", "",
         f"# MS1 (mass only) annotation of the MEANtools features, built {date.today()} by build_gene_annotation.py from results/metabolite_pathway_map.csv.",
         "# The mass matches the first InChIKey block (connectivity layer) of one or more PlantMetWiki metabolites; no MS/MS, no retention time.", ""]
    for r in mm.itertuples():
        L.append(f'lodp:annotation_mass_{r.feature}_{r.key14} a lodp:MetaboliteAnnotation ;\n    lodp:feature lodp:feature_MTBLS1039_{r.feature} ;\n'
                 f'    skos:closeMatch <https://identifiers.org/inchikey/{r.key14}> ;\n    lodp:matchLevel "mass_match" ;\n    lodp:adduct "{r.adduct}" ;\n    lodp:ppmError {r.ppm_error} .')
    (HERE / "results" / "feature_annotation.ttl").write_text("\n".join(L) + "\n")
    print(f"written results/feature_annotation.ttl: {len(mm)} annotations of {mm.feature.nunique()} features", file=sys.stderr)


def main():
    genes = genes_of_associations()
    up = pd.read_csv(HERE / "data" / "uniprot_tomato.tsv.gz", sep="\t")
    up["locus"] = up.EnsemblPlants.astype(str).str.extract(r"(Solyc\d+g\d+)")[0]
    up = up.dropna(subset=["locus"])
    up["rank"] = (up.Reviewed != "reviewed").astype(int)          # prefer reviewed entries
    up = up.sort_values(["locus", "rank"]).drop_duplicates("locus").set_index("locus")
    have = [g for g in genes if g in up.index]
    print(f"{len(genes)} genes in the associations, {len(have)} with a UniProt entry", file=sys.stderr)

    enzymes = pmw_enzymes()
    print(f"{len(enzymes)} UniProt enzymes in PlantMetWiki pathways", file=sys.stderr)
    g_acc = {g: up.loc[g, "Entry"] for g in have}
    g_og = orthodb_groups(sorted(set(g_acc.values())))
    e_og = orthodb_groups(enzymes)
    og_to_enz = {}
    for e, ogs in e_og.items():
        for og in ogs:
            og_to_enz.setdefault(og, set()).add(e)

    L = ["@prefix lodp: <https://example.org/lod-pathways/pilot/> .",
         "@prefix uniprot: <http://purl.uniprot.org/uniprot/> .", "",
         f"# Gene annotation graph for the paired-omics pilot, built {date.today()} by build_gene_annotation.py.",
         "# Sources: UniProt (snapshot data/uniprot_tomato.tsv.gz), OrthoDB SPARQL endpoint, PlantMetWiki enzymes (live).",
         "# Supporting graph, not a claim graph: not validated by the shapes.", ""]
    n_orth = 0
    for g in have:
        acc = g_acc[g]; iri = f"<https://plants.ensembl.org/Solanum_lycopersicum/Gene/Summary?g={g}>"
        po = [f"lodp:uniprot uniprot:{acc}"]
        ec = up.loc[g, "EC number"]
        if isinstance(ec, str):
            po += [f'lodp:ecNumber "{e.strip()}"' for e in ec.split(";") if e.strip()]
        shared = {}
        for og in g_og.get(acc, set()):
            for e in og_to_enz.get(og, ()):
                shared.setdefault(e, set()).add(og)
        for e, ogs in sorted(shared.items()):
            po.append(f"lodp:orthologOf uniprot:{e}")
            po += [f'lodp:orthologGroup "{og}"' for og in sorted(ogs)]
        n_orth += bool(shared)
        L.append(f"{iri} " + " ;\n    ".join(po) + " .")
    (HERE / "results" / "gene_annotation.ttl").write_text("\n".join(L) + "\n")
    write_feature_annotation()
    print(f"written results/gene_annotation.ttl: {len(have)} genes, {n_orth} with at least one ortholog among the PlantMetWiki enzymes", file=sys.stderr)


if __name__ == "__main__":
    main()
