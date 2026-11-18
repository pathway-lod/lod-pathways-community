"""Which MEANtools features that have NO PlantMetWiki compound can be placed in a pathway through their correlated genes?

Orphan feature = a feature of the MEANtools tomato case study (Jeon et al. 2020 data) without a mass match to a PlantMetWiki
metabolite (results/metabolite_pathway_map.csv). Its only handle on PlantMetWiki is the genes that correlate with it.

For every gene of the correlation table (all 5,380, not only the clustered ones) the evidence tiers of the minimum-information
model are computed against PlantMetWiki (files in data/, OrthoDB for orthologs; the weights are those of
minimum_information/notebooks/weights.csv):
    membership family: locus 0.90 > UniProt entry 0.80 > EC number 0.40 (max)
    sequence family:   ortholog (same OrthoDB group as an enzyme listed in the pathway) 0.50
A feature (grouped with its adducts and isotopes into one "compound") gets, per pathway, the max of each family over its linked
genes; the score is the noisy-OR of the families. Linked genes: MR <= MAX_MR (default 10) and r > 0.
The null shuffles the gene annotation (random gene sets of the same size), so that a score is read against chance.

Run:  python orphan_features.py          (needs internet the first time for OrthoDB; results are cached in data/)
Writes results/orphan_candidates.csv, results/orphan_compounds.csv
"""
import json, re, sqlite3, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
DATA, RES = HERE / "data", HERE / "results"
sys.path.insert(0, str(HERE))
import build_gene_annotation as bga

MAX_MR = 10
W = {"locus": 0.90, "uniprot": 0.80, "ec": 0.40, "ortholog": 0.50}
SHIFTS = {"13C isotope": 1.003355, "[M+Na]+ vs [M+H]+": 21.981944, "[M+K]+ vs [M+H]+": 37.955882, "[M+NH4]+ vs [M+H]+": 17.026549,
          "[M+H-H2O]+ vs [M+H]+": -18.010565}


def uniprot_table():
    up = pd.read_csv(DATA / "uniprot_tomato.tsv.gz", sep="\t")
    up["locus"] = up.EnsemblPlants.astype(str).str.extract(r"(Solyc\d+g\d+)")[0]
    up = up.dropna(subset=["locus"])
    up["ec"] = up["EC number"].fillna("").str.split("; ")
    return up


def cached(path, fn):
    if path.exists():
        return json.loads(path.read_text())
    out = fn()
    path.write_text(json.dumps(out))
    return out


def orthologs(up):
    accs = sorted(set(up.Entry))
    g = cached(DATA / "orthodb_tomato_all.json", lambda: {k: sorted(v) for k, v in bga.orthodb_groups(accs).items()})
    enz = bga.pmw_enzymes()
    e = cached(DATA / "orthodb_pmw_enzymes.json", lambda: {k: sorted(v) for k, v in bga.orthodb_groups(enz).items()})
    return g, e


def gene_pathway_scores(genes, up):
    """DataFrame gene, pathway (PC number), tier, weight."""
    pc = pd.read_csv(DATA / "plantmetwiki_pc_pathways.csv")
    pc = pc[~pc.plantcyc_id.str.contains("RXN")]            # single-reaction diagrams (RC..., ...-RXN) are typed as pathways in PlantMetWiki: not pathways
    ec = pd.read_csv(DATA / "plantmetwiki_pathway_ec.csv").drop_duplicates()
    sol = pd.read_csv(DATA / "plantmetwiki_pathway_solyc.csv")
    pu = pd.read_csv(DATA / "plantmetwiki_pathway_uniprot.csv").drop_duplicates()
    g_og, e_og = orthologs(up)
    rows = []
    for r in sol.itertuples():
        rows.append((r.locus, r.pc, "locus"))
    u = up[up.locus.isin(genes)][["locus", "Entry", "ec"]]
    for r in u.merge(pu, left_on="Entry", right_on="uniprot").itertuples():
        rows.append((r.locus, r.pc, "uniprot"))
    ue = u.explode("ec"); ue = ue[ue.ec.str.match(r"^\d+\.\d+\.\d+\.\d+$", na=False)]
    for r in ue.merge(ec, on="ec").itertuples():
        rows.append((r.locus, r.pc, "ec"))
    og_pc = {}                                  # OrthoDB group -> pathways of the PlantMetWiki enzymes in it
    pu_map = pu.groupby("uniprot").pc.apply(set).to_dict()
    for acc, ogs in e_og.items():
        for og in ogs:
            og_pc.setdefault(og, set()).update(pu_map.get(acc, ()))
    for r in u.itertuples():
        for og in g_og.get(r.Entry, ()):
            for p in og_pc.get(og, ()):
                rows.append((r.locus, p, "ortholog"))
    d = pd.DataFrame(rows, columns=["gene", "pc", "tier"]).drop_duplicates()
    d = d[d.gene.isin(genes)]
    d["weight"] = d.tier.map(W)
    return d.merge(pc, on="pc", how="inner")


def compound_groups(feats):
    """Group features that are adducts / isotopes of one compound: RT within 6 s, known mass shift, abundance r >= 0.9."""
    t = pd.read_csv(DATA / "xcms_feature_table.csv", index_col=0)
    t = t.loc[t.index.intersection(feats)]
    ab = np.log1p(t.drop(columns=["mzmed", "rtmed"]))
    parent = {f: f for f in t.index}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, a in enumerate(t.index):
        for b in t.index[i + 1:]:
            if abs(t.rtmed[a] - t.rtmed[b]) > 6:
                continue
            dm = abs(t.mzmed[a] - t.mzmed[b])
            if not any(abs(dm - abs(s)) < 0.004 for s in SHIFTS.values()):
                continue
            if np.corrcoef(ab.loc[a], ab.loc[b])[0, 1] >= 0.9:
                parent[find(a)] = find(b)
    return {f: find(f) for f in t.index}, t


def main(max_mr=MAX_MR):
    c = sqlite3.connect(DATA / "Jeon_fungal.sqlite")
    cor = pd.read_sql("select * from Jeon_fungal_correlations", c).merge(
        pd.read_sql("select * from Jeon_fungal_correlations_MR_edges", c), on=["metabolite", "gene"])
    cor["locus"] = cor.gene.str.extract(r"(Solyc\d+g\d+)")[0]
    mm = pd.read_csv(RES / "metabolite_pathway_map.csv")
    annotated = set(mm.feature)
    orphans = sorted(set(cor.metabolite) - annotated)
    grp, t = compound_groups(set(cor.metabolite))
    print(f"{cor.metabolite.nunique()} features, {len(annotated)} with a PlantMetWiki mass match, {len(orphans)} orphans", file=sys.stderr)

    up = uniprot_table()
    genes = sorted(set(cor.locus))
    gp = gene_pathway_scores(set(genes), up)
    gp.to_csv(RES / "gene_pathway_all.csv", index=False)
    print(f"{len(genes)} genes, {gp.gene.nunique()} reach a pathway, {gp.pc.nunique()} pathways", file=sys.stderr)

    sel = cor[(cor.MR <= max_mr) & (cor.correlation > 0) & cor.metabolite.isin(orphans)]
    sel = sel.assign(compound=sel.metabolite.map(lambda f: grp.get(f, f)))
    print(f"{len(sel)} orphan feature-gene links with MR <= {max_mr}, r > 0", file=sys.stderr)

    # family maxima per gene and pathway
    gp["family"] = np.where(gp.tier == "ortholog", "sequence", "membership")
    fam = gp.groupby(["gene", "pc", "family"]).weight.max().unstack("family").fillna(0.0)
    pcs = {p: i for i, p in enumerate(fam.index.get_level_values("pc").unique())}
    all_genes = pd.Index(genes)
    M = np.zeros((len(all_genes), len(pcs))); S = np.zeros_like(M)
    gi = {g: i for i, g in enumerate(all_genes)}
    for (g, p), r in fam.iterrows():
        M[gi[g], pcs[p]] = r.get("membership", 0); S[gi[g], pcs[p]] = r.get("sequence", 0)

    rng = np.random.default_rng(1)
    names = gp.drop_duplicates("pc").set_index("pc").pathway.to_dict()
    out, comp_rows = [], []
    for comp, d in sel.groupby("compound"):
        gl = sorted(set(d.locus)); idx = [gi[g] for g in gl]
        m, s = M[idx].max(0), S[idx].max(0)
        score = 1 - (1 - m) * (1 - s)
        n = len(idx)
        ok = np.where(score > 0)[0]
        if not len(ok):
            comp_rows.append(dict(compound=comp, n_links=len(d), n_genes=n, best=0)); continue
        # null: n random genes of the table (annotation shuffled); chunks keep the memory small
        NP, parts = 1000, []
        for _ in range(NP // 250):
            R = rng.integers(0, len(all_genes), size=(250, n))
            parts.append(1 - (1 - M[R].max(1)) * (1 - S[R].max(1)))       # (250, pathways)
        nscore = np.vstack(parts)
        p_any = (np.sum(nscore.max(1) >= score.max()) + 1) / (NP + 1)       # chance of a pathway this good anywhere
        for k, j in enumerate(ok):
            p_emp = (np.sum(nscore[:, j] >= score[j]) + 1) / (NP + 1)
            gg = [g for g in gl if M[gi[g], j] > 0 or S[gi[g], j] > 0]
            tiers = sorted(set(gp[(gp.pc == list(pcs)[j]) & gp.gene.isin(gg)].tier))
            out.append(dict(compound=comp, features=";".join(sorted(f for f, g in grp.items() if g == comp)),
                            pc=list(pcs)[j], pathway=names.get(list(pcs)[j]), score=round(float(score[j]), 3), w_membership=m[j], w_sequence=s[j],
                            n_genes_link=n, n_genes_pathway=len(gg), genes=",".join(gg[:6]), tiers=",".join(tiers), p_pathway=round(float(p_emp), 4), p_any=round(float(p_any), 4)))
        comp_rows.append(dict(compound=comp, n_links=len(d), n_genes=n, best=float(score.max())))
    cand = pd.DataFrame(out).sort_values(["score", "n_genes_pathway"], ascending=False)
    suf = "" if max_mr == MAX_MR else f"_mr{max_mr}"
    cand.to_csv(RES / f"orphan_candidates{suf}.csv", index=False)
    pd.DataFrame(comp_rows).to_csv(RES / f"orphan_compounds{suf}.csv", index=False)
    print(f"{cand.compound.nunique()} of {sel.compound.nunique()} orphan compounds have a candidate pathway", file=sys.stderr)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else MAX_MR)
