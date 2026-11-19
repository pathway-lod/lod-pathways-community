"""Sequence-similarity tier for ALL correlated tomato genes (not only the clustered ones): EC transfer through UniRef50.

A UniRef50 cluster groups proteins that are >= 50 % identical (>= 80 % overlap) to the cluster representative. If a tomato protein shares
its cluster with UniProt entries that carry an EC number, the EC is transferred to the gene (tier 'seq_ec', sequence family, weight 0.50);
the gene reaches a PlantMetWiki pathway if that EC is on a reaction of the pathway. This is the same idea as the global-alignment check
of notebook 06 (identity >= 40 %), made cheap enough for 5,380 genes; the thresholds are not identical (UniRef50 is 50 % to the
representative, not pairwise). Clusters with more than MAX_CLUSTER members are skipped (large superfamilies would transfer any EC).

Run:  python sequence_transfer.py        (needs internet, a few minutes; caches in data/uniref50_*.json)
Writes results/gene_seq_ec.csv: gene, ec, pc, n_members_with_ec, cluster, cluster_size
"""
import json, re, sqlite3, sys, time
from pathlib import Path
import pandas as pd, requests

HERE = Path(__file__).parent
DATA, RES = HERE / "data", HERE / "results"
API = "https://rest.uniprot.org"
MAX_CLUSTER = 3000


def idmap_uniref50(accs):
    """UniProt accession -> (cluster id, size)."""
    out = {}
    for i in range(0, len(accs), 3000):
        job = requests.post(f"{API}/idmapping/run", data={"from": "UniProtKB_AC-ID", "to": "UniRef50", "ids": ",".join(accs[i:i + 3000])}).json()["jobId"]
        for _ in range(200):                                          # wait until the job is done
            t = requests.get(f"{API}/idmapping/uniref/results/stream/{job}", params={"format": "tsv", "fields": "id,count"}, timeout=600).text
            if t.startswith("From"):
                break
            time.sleep(3)
        for line in t.splitlines()[1:]:
            f = line.split("\t")
            if len(f) == 3 and f[2].isdigit():                       # skip malformed lines of the stream
                out[f[0]] = (f[1], int(f[2]))
    return out


def main():
    up = pd.read_csv(DATA / "uniprot_tomato.tsv.gz", sep="\t")
    up["locus"] = up.EnsemblPlants.astype(str).str.extract(r"(Solyc\d+g\d+)")[0]
    c = sqlite3.connect(DATA / "Jeon_fungal.sqlite")
    genes = set(pd.read_sql("select distinct gene from Jeon_fungal_correlations", c).gene.str.extract(r"(Solyc\d+g\d+)")[0])
    up = up[up.locus.isin(genes)]
    cache = DATA / "uniref50_tomato.json"
    if cache.exists():
        gcl = json.loads(cache.read_text())
    else:
        gcl = idmap_uniref50(sorted(set(up.Entry))); cache.write_text(json.dumps(gcl))
    print(f"{len(gcl)} tomato proteins mapped to {len({v[0] for v in gcl.values()})} UniRef50 clusters", file=sys.stderr)

    clusters = sorted({v[0] for v in gcl.values() if v[1] <= MAX_CLUSTER})
    ccache = DATA / "uniref50_ec_members.json"
    if ccache.exists():
        mem = json.loads(ccache.read_text())
    else:
        ents = {}                                                    # accession -> EC string
        ecache = DATA / "uniref50_ec_entries.json"
        if ecache.exists():
            ents = json.loads(ecache.read_text())
        for i in range(0, len(clusters), 25) if not ents else []:
            q = "(" + " OR ".join(f"uniref_cluster_50:{x}" for x in clusters[i:i + 25]) + ") AND ec:*"
            r = requests.get(f"{API}/uniprotkb/stream", params={"query": q, "fields": "accession,ec", "format": "tsv"}, timeout=300)
            r.raise_for_status()
            for line in r.text.splitlines()[1:]:
                a, ec = line.split("\t"); ents[a] = ec
            if (i // 25) % 20 == 0:
                print(f"  clusters {i}/{len(clusters)}  entries with EC {len(ents)}", file=sys.stderr)
        ecache.write_text(json.dumps(ents))
        emap = idmap_uniref50(sorted(ents))
        mem = {}
        for a, ec in ents.items():
            if a in emap:
                mem.setdefault(emap[a][0], []).append([a, ec])
        ccache.write_text(json.dumps(mem))
    rows = []
    mine = set(up.Entry)
    for locus, d in up.groupby("locus"):
        for acc in d.Entry:
            cl = gcl.get(acc)
            if not cl or cl[0] not in mem:
                continue
            ecs = {}
            for a, ec in mem[cl[0]]:
                if a in mine or a == acc:
                    continue                                          # tomato entries themselves do not count as evidence
                for e in ec.split("; "):
                    if re.match(r"^\d+\.\d+\.\d+\.\d+$", e):
                        ecs[e] = ecs.get(e, 0) + 1
            for e, n in ecs.items():
                rows.append((locus, e, n, cl[0], cl[1]))
    df = pd.DataFrame(rows, columns=["gene", "ec", "n_members_with_ec", "cluster", "cluster_size"]).drop_duplicates()
    ecp = pd.read_csv(DATA / "plantmetwiki_pathway_ec.csv").drop_duplicates()
    out = df.merge(ecp, on="ec", how="left")
    out.to_csv(RES / "gene_seq_ec.csv", index=False)
    print(f"{df.gene.nunique()} genes get a transferred EC; {out.dropna(subset=['pc']).gene.nunique()} reach a PlantMetWiki pathway", file=sys.stderr)


if __name__ == "__main__":
    main()
