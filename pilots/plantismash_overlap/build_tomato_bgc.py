"""Tomato biosynthetic gene clusters (plantiSMASH 2.0) with their genes as Solyc loci, for the minimum-information tiers.

The cluster graph of the evidence graphs (shape_constraints/rdf/bgc.ttl) lists only the genes of Arabidopsis clusters that
are linked to a PlantMetWiki pathway. The tiers that join co-expression (MEANtools functional clusters, tomato) with
biosynthetic gene clusters need the genes of the *tomato* clusters, with the same gene identifiers as the associations:
https://plants.ensembl.org/Solanum_lycopersicum/Gene/Summary?g=Solyc...

Steps: read the 63 tomato clusters of the cached plantiSMASH genome (data/plantismash_v2/Solanum_lycopersicum_GCF_036512215.1.json.gz),
map the RefSeq protein of each gene to UniProt with the UniProt ID mapping service (live), take the Ensembl Plants gene
(Solyc) that UniProt cross-references, and write results/bgc_tomato.ttl. About half of the proteins map (the assembly of
plantiSMASH is not the one of ITAG), so the graph is a lower bound of the genes of each cluster.

Run:  python build_tomato_bgc.py   (internet, about 1 min)
"""
import gzip, json, re, sys, time
from datetime import date
from pathlib import Path
import requests

HERE = Path(__file__).parent
GENOME = "Solanum_lycopersicum_GCF_036512215.1"


def idmapping(ids):
    job = requests.post("https://rest.uniprot.org/idmapping/run", data={"from": "RefSeq_Protein", "to": "UniProtKB", "ids": ",".join(ids)}, timeout=60).json()["jobId"]
    for _ in range(100):
        if requests.get(f"https://rest.uniprot.org/idmapping/status/{job}", timeout=30).json().get("jobStatus", "FINISHED") != "RUNNING":
            break
        time.sleep(3)
    out, url = {}, f"https://rest.uniprot.org/idmapping/uniprotkb/results/{job}?size=500&fields=accession,xref_ensemblplants"
    while url:
        r = requests.get(url, timeout=120); r.raise_for_status()
        for x in r.json()["results"]:
            loci = {re.match(r"(Solyc\d+g\d+)", c["id"]).group(1) for c in x["to"].get("uniProtKBCrossReferences", []) if c["database"] == "EnsemblPlants" and re.match(r"Solyc\d+g\d+", c["id"])}
            out.setdefault(x["from"], set()).update(loci)
        url = r.links.get("next", {}).get("url")
    return out


def main():
    clusters = json.loads(gzip.decompress((HERE / "data" / "plantismash_v2" / f"{GENOME}.json.gz").read_bytes()))
    ids = sorted({g["protein_id"] for c in clusters for g in c["genes"] if g["protein_id"]})
    m = idmapping(ids)
    print(f"{len(clusters)} clusters, {len(ids)} proteins, {len(m)} mapped to UniProt, {sum(bool(v) for v in m.values())} with a Solyc locus", file=sys.stderr)
    L = ["@prefix lodp: <https://example.org/lod-pathways/pilot/> .", "@prefix obo: <http://purl.obolibrary.org/obo/> .", "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .", "",
         f"# Tomato biosynthetic gene clusters of plantiSMASH 2.0 ({GENOME}), genes as Solyc loci; built {date.today()} by build_tomato_bgc.py.",
         "# Supporting graph, not a claim graph. About half of the cluster genes map to a Solyc locus (lower bound).", ""]
    n_cl = n_g = 0
    for c in clusters:
        loci = sorted({l for g in c["genes"] if g["protein_id"] for l in m.get(g["protein_id"], ())})
        if not loci:
            continue
        iri = f"<https://plantismash.bioinformatics.nl/precalc/v2/{GENOME}/index.html#{c['cluster']}>"
        label = c["type"].replace('"', "") + (f"; MIBiG {c['mibig_name']}" if c.get("mibig_name") else "")
        L.append(f"{iri} a obo:SO_0002357 ;\n    rdfs:label \"{label}\" ;\n    lodp:genomeAssembly \"GCF_036512215.1\" ;\n    obo:BFO_0000051 " +
                 ",\n        ".join(f"<https://plants.ensembl.org/Solanum_lycopersicum/Gene/Summary?g={l}>" for l in loci) + " .")
        n_cl += 1; n_g += len(loci)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "bgc_tomato.ttl").write_text("\n".join(L) + "\n")
    print(f"written results/bgc_tomato.ttl: {n_cl} clusters with at least one Solyc gene, {n_g} gene-cluster links", file=sys.stderr)


if __name__ == "__main__":
    main()
