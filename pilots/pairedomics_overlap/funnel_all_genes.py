"""The funnel of notebook 06 for ALL correlated tomato genes (5,380), not only the 350 genes of the clustered associations,
with the sequence-similarity tier (EC transferred through UniRef50, sequence_transfer.py) and the position of the THT genes.

Needs results/gene_pathway_all.csv (orphan_features.py) and results/gene_seq_ec.csv (sequence_transfer.py).
Writes results/funnel_all_genes.csv  (tier, clustered_350, all_5380, THT_Solyc08g068730, THT_Solyc08g068710)
and results/funnel_combined_null.json (the combined gene + annotated-metabolite tier against a shuffled null)
"""
import json, re, sqlite3
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
DATA, RES = HERE / "data", HERE / "results"
THT = ["Solyc08g068730", "Solyc08g068710"]


def main():
    c = sqlite3.connect(DATA / "Jeon_fungal.sqlite")
    cor = pd.read_sql("select * from Jeon_fungal_correlations", c).merge(pd.read_sql("select * from Jeon_fungal_correlations_MR_edges", c), on=["metabolite", "gene"])
    cor["locus"] = cor.gene.str.extract(r"(Solyc\d+g\d+)")[0]
    allg = set(cor.locus)
    clustered = set(re.findall(r"Gene/Summary\?g=(Solyc\d+g\d+)", (HERE.parent.parent / "shape_constraints/rdf/association.ttl").read_text()))
    up = pd.read_csv(DATA / "uniprot_tomato.tsv.gz", sep="\t"); up["locus"] = up.EnsemblPlants.astype(str).str.extract(r"(Solyc\d+g\d+)")[0]
    up = up[up.locus.isin(allg)]
    gp = pd.read_csv(RES / "gene_pathway_all.csv")
    pcs = pd.read_csv(DATA / "plantmetwiki_pc_pathways.csv"); pcs = pcs[~pcs.plantcyc_id.str.contains("RXN")]
    sq = pd.read_csv(RES / "gene_seq_ec.csv").dropna(subset=["pc"]); sq = sq[sq.pc.isin(pcs.pc)]
    seq = sq[["gene", "pc"]].assign(tier="seq_ec")
    gp = pd.concat([gp[["gene", "pc", "tier"]], seq], ignore_index=True).drop_duplicates()
    tr = pd.read_csv(RES / "gene_seq_ec.csv")                                             # genes that got an EC by transfer

    def row(name, f):
        out = {"tier": name}
        for lab, S in (("clustered_350", clustered), ("all_5380", allg)):
            out[lab] = len(f & S)
        for g in THT:
            out[g] = "yes" if g in f else "no"
        return out

    sets = [
        ("genes with a MEANtools correlation/association", allg | clustered),
        ("with a UniProt entry", set(up.locus)),
        ("with an EC number of its own", set(up[up["EC number"].notna()].locus)),
        ("with an EC number transferred from a similar protein (UniRef50)", set(tr.gene)),
        ("reach a pathway: own EC (0.40)", set(gp[gp.tier == "ec"].gene)),
        ("reach a pathway: transferred EC, sequence similarity (0.50)", set(gp[gp.tier == "seq_ec"].gene)),
        ("reach a pathway: ortholog of a pathway enzyme (0.50)", set(gp[gp.tier == "ortholog"].gene)),
        ("reach a pathway: UniProt entry listed (0.80)", set(gp[gp.tier == "uniprot"].gene)),
        ("reach a pathway: Solyc locus listed (0.90)", set(gp[gp.tier == "locus"].gene)),
        ("reach a pathway: any tier", set(gp.gene)),
    ]
    rows = [row(n, f) for n, f in sets]
    # the strict combined tier: gene and an annotated (mass match) feature that correlates with it are in the same pathway
    mm = pd.read_csv(RES / "metabolite_pathway_map.csv").merge(pcs[["pc", "plantcyc_id"]], on="plantcyc_id")[["feature", "pc"]].drop_duplicates()
    sel = cor[(cor.MR <= 10) & (cor.correlation > 0)][["locus", "metabolite"]].drop_duplicates()

    def combined(gpx):
        j = sel.merge(gpx[["gene", "pc"]].drop_duplicates(), left_on="locus", right_on="gene").merge(mm, left_on="metabolite", right_on="feature")
        return j[j.pc_x == j.pc_y] if "pc_x" in j else j
    j = sel.merge(gp[["gene", "pc"]].drop_duplicates(), left_on="locus", right_on="gene").merge(mm.rename(columns={"pc": "pc_m"}), left_on="metabolite", right_on="feature")
    j = j[j.pc == j.pc_m]
    obs_genes, obs_pairs = j.locus.nunique(), len(j[["locus", "metabolite"]].drop_duplicates())
    rows.append(row("gene AND an annotated correlated feature in the same pathway (MR <= 10, r > 0)", set(j.locus)))
    pd.DataFrame(rows).to_csv(RES / "funnel_all_genes.csv", index=False)

    # null: shuffle the pathway annotation among the genes
    rng = np.random.default_rng(1)
    by_gene = gp.groupby("gene").pc.apply(set).to_dict()
    genes_ann = list(by_gene)
    all_list = sorted(allg)
    mpath = mm.groupby("feature").pc.apply(set).to_dict()
    counts = []
    for _ in range(300):
        perm = dict(zip(rng.permutation(all_list), [by_gene.get(g, set()) for g in all_list]))
        n = {l for l, m in zip(sel.locus, sel.metabolite) if perm.get(l, set()) & mpath.get(m, set())}
        counts.append(len(n))
    (RES / "funnel_combined_null.json").write_text(json.dumps({"observed_genes": obs_genes, "observed_pairs": obs_pairs, "null_mean": float(np.mean(counts)),
                                                              "null_p95": float(np.percentile(counts, 95)), "p_ge_observed": float((np.sum(np.array(counts) >= obs_genes) + 1) / 301)}))
    print(pd.DataFrame(rows).to_string()); print(open(RES / "funnel_combined_null.json").read())


if __name__ == "__main__":
    main()
