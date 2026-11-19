"""Orphan features, model v2: specificity-weighted gene tiers + a mass tier (orphan_features.py is the baseline v1).

Why v2: in v1 only 1 of 71 orphan compounds had a best pathway better than a shuffled-gene null (3.5 expected by chance) and the
top candidates were co-induced sterol/glycoalkaloid genes whose products do not fit the feature mass. Two changes, both drafts:

1. Specificity weighting of the gene tiers. A gene that reaches k pathways through a tier says less about each of them:
       w_eff = w / (1 + log2 k)            (k = pathways reached by that gene through that tier; k = 1 keeps w)
2. A mass tier from the compound itself (the only handle a feature has besides its genes):
   - mass-delta (relatedness family, weight 0.20): the neutral mass differs by a specific conjugation (acetyl, hexose, pentose,
     deoxyhexose, caffeoyl, feruloyl, coumaroyl, sulfate, glucuronide) from a metabolite of the pathway (<= 5 ppm,
     features of one compound are tried as [M+H]+ and [M+Na]+).
   - mass-defect gate (a multiplier, not a tier): the relative mass defect (RMD, ppm) of the compound must lie within the RMD range
     of the pathway's metabolites without the cofactors (+- RMD_MARGIN); otherwise the score is multiplied by GATE_OUT (0.5).

Score = gate x noisy-OR(membership_eff, sequence_eff, mass_delta). Candidates need gene evidence. The null shuffles the gene annotation
(random gene sets of the same size; the compound's own mass terms stay fixed).

Run:  python orphan_features_v2.py        -> results/orphan_candidates_v2.csv, results/orphan_compare_v1_v2.csv
"""
import sqlite3, sys
from pathlib import Path
import numpy as np, pandas as pd
from rdkit import Chem
from rdkit.Chem.rdMolDescriptors import CalcMolFormula
from rdkit.Chem.Descriptors import ExactMolWt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import orphan_features as v1

DATA, RES = v1.DATA, v1.RES
W_MASS, GATE_OUT, RMD_MARGIN, PPM = 0.20, 0.5, 75.0, 5.0
H, NA = 1.007276, 22.989218
DELTAS = {"acetyl": 42.010565, "hexose": 162.052824, "pentose": 132.042259, "deoxyhexose": 146.057909, "caffeoyl": 162.031694,
          "feruloyl": 176.047344, "coumaroyl": 146.036779, "sulfate": 79.956815, "glucuronide": 176.032088}   # specific conjugations only (2H, O, CH2, H2O are too generic: they hit by chance)
DELTA_LIST = sorted(set(DELTAS.values()) | {-d for d in DELTAS.values()})     # the compound itself (delta 0) is a mass match: those features are not orphans
MAX_PATHWAYS_PER_METABOLITE = 20          # cofactors and common metabolites (ATP, CoA, NADPH ...) are left out of the mass profile of a pathway


def pathway_masses():
    """plantcyc_id -> array of neutral exact masses of the PlantMetWiki metabolites of the pathway (>= 100 Da)."""
    ik = pd.read_csv(DATA / "plantmetwiki_metabolite_inchi.csv")
    mass = {}
    for r in ik.itertuples():
        try:
            m = Chem.MolFromInchi(r.inchi, sanitize=False)
            if m is not None:
                Chem.SanitizeMol(m); mass[r.inchikey[:14]] = ExactMolWt(m)
        except Exception:
            pass
    pw = pd.read_csv(HERE.parent / "metabolomics_overlap" / "data" / "plantmetwiki_metabolite_pathways.csv", dtype=str)
    pw = pw[~pw.plantcyc_id.str.contains("RXN")]
    pw["m"] = pw.inchikey.str[:14].map(mass)
    pw = pw.dropna(subset=["m"]); pw = pw[pw.m >= 100]
    pw = pw[pw.groupby(pw.inchikey.str[:14]).plantcyc_id.transform("nunique") <= MAX_PATHWAYS_PER_METABOLITE]
    return {k: np.sort(g.m.drop_duplicates().to_numpy()) for k, g in pw.groupby("plantcyc_id")}


def rmd(m):
    return (m - round(m)) / m * 1e6


def mass_terms(neutrals, masses):
    """For one compound (list of candidate neutral masses) and one pathway's metabolite masses: (delta hit, in RMD range)."""
    hit = False
    for n in neutrals:
        for d in DELTA_LIST:
            x = n - d
            i = np.searchsorted(masses, x)
            for j in (i - 1, i):
                if 0 <= j < len(masses) and abs(masses[j] - x) / x * 1e6 <= PPM:
                    hit = True
    r = np.array([rmd(m) for m in masses]); lo, hi = r.min() - RMD_MARGIN, r.max() + RMD_MARGIN
    ok = any(lo <= rmd(n) <= hi for n in neutrals)
    return hit, ok


def main(max_mr=v1.MAX_MR):
    c = sqlite3.connect(DATA / "Jeon_fungal.sqlite")
    cor = pd.read_sql("select * from Jeon_fungal_correlations", c).merge(
        pd.read_sql("select * from Jeon_fungal_correlations_MR_edges", c), on=["metabolite", "gene"])
    cor["locus"] = cor.gene.str.extract(r"(Solyc\d+g\d+)")[0]
    annotated = set(pd.read_csv(RES / "metabolite_pathway_map.csv").feature)
    orphans = sorted(set(cor.metabolite) - annotated)
    grp, t = v1.compound_groups(set(cor.metabolite))
    gp = pd.read_csv(RES / f"gene_pathway_all{v1.SEQ_SUF}.csv")                # v1 output: gene, pc, tier, weight, plantcyc_id, pathway
    pcmap = pd.read_csv(DATA / "plantmetwiki_pc_pathways.csv")
    # 1. specificity weighting
    gp["family"] = np.where(gp.tier.isin(["ortholog", "seq_ec"]), "sequence", "membership")
    k = gp.groupby(["gene", "tier"]).pc.transform("nunique")
    gp["w_eff"] = gp.weight / (1 + np.log2(k))
    fam = gp.groupby(["gene", "pc", "family"]).w_eff.max().unstack("family").fillna(0.0)
    pcs = list(fam.index.get_level_values("pc").unique()); pci = {p: i for i, p in enumerate(pcs)}
    genes = sorted(set(cor.locus)); gi = {g: i for i, g in enumerate(genes)}
    M = np.zeros((len(genes), len(pcs))); S = np.zeros_like(M)
    for (g, p), r in fam.iterrows():
        M[gi[g], pci[p]] = r.get("membership", 0); S[gi[g], pci[p]] = r.get("sequence", 0)
    pc2plantcyc = pcmap.drop_duplicates("pc").set_index("pc").plantcyc_id.to_dict()
    names = pcmap.drop_duplicates("pc").set_index("pc").pathway.to_dict()
    pmass = pathway_masses()

    sel = cor[(cor.MR <= max_mr) & (cor.correlation > 0) & cor.metabolite.isin(orphans)]
    sel = sel.assign(compound=sel.metabolite.map(lambda f: grp.get(f, f)))
    rng = np.random.default_rng(1)
    out = []
    for comp, d in sel.groupby("compound"):
        gl = sorted(set(d.locus)); idx = [gi[g] for g in gl]; n = len(idx)
        feats = sorted(f for f, g in grp.items() if g == comp)
        neutrals = sorted({t.mzmed[f] - H for f in feats} | {t.mzmed[f] - NA for f in feats})
        mw = np.zeros(len(pcs)); gate = np.ones(len(pcs))
        for p, j in pci.items():
            ms = pmass.get(pc2plantcyc.get(p))
            if ms is None:
                continue
            hit, ok = mass_terms(neutrals, ms)
            mw[j] = W_MASS if hit else 0.0
            gate[j] = 1.0 if ok else GATE_OUT

        def sc(m, s):
            return gate * (1 - (1 - m) * (1 - s) * (1 - mw))
        m, s = M[idx].max(0), S[idx].max(0)
        score = sc(m, s)
        gene_part = np.maximum(m, s) > 0
        if not gene_part.any():
            continue
        parts = []
        for _ in range(4):
            R = rng.integers(0, len(genes), size=(250, n))
            parts.append(sc(M[R].max(1), S[R].max(1)))
        ns = np.vstack(parts)
        best = score[gene_part].max()
        p_any = (np.sum(ns.max(1) >= best) + 1) / (len(ns) + 1)
        for j in np.where(gene_part)[0]:
            gg = [g for g in gl if M[gi[g], j] > 0 or S[gi[g], j] > 0]
            out.append(dict(compound=comp, features=";".join(feats), mz=round(t.mzmed[feats[0]], 4), rt_s=round(t.rtmed[feats[0]]),
                            pc=pcs[j], pathway=names.get(pcs[j]), score=round(float(score[j]), 3), w_membership=round(m[j], 3),
                            w_sequence=round(s[j], 3), mass_delta=bool(mw[j] > 0), mass_defect_ok=bool(gate[j] == 1.0),
                            n_genes_link=n, n_genes_pathway=len(gg), genes=",".join(gg[:6]),
                            p_pathway=round(float((np.sum(ns[:, j] >= score[j]) + 1) / (len(ns) + 1)), 4), p_any=round(float(p_any), 4)))
    cand = pd.DataFrame(out).sort_values(["score", "n_genes_pathway"], ascending=False)
    suf = ("" if max_mr == v1.MAX_MR else f"_mr{max_mr}") + v1.SEQ_SUF
    cand.to_csv(RES / f"orphan_candidates_v2{suf}.csv", index=False)
    best = cand.drop_duplicates("compound")
    v1c = pd.read_csv(RES / f"orphan_candidates{suf}.csv").sort_values(["score", "n_genes_pathway"], ascending=False).drop_duplicates("compound")
    cmp = best.merge(v1c[["compound", "pathway", "score", "p_any"]], on="compound", how="left", suffixes=("", "_v1"))
    cmp.to_csv(RES / f"orphan_compare_v1_v2{suf}.csv", index=False)
    print(f"v2: {len(best)} compounds with a candidate; p_any<0.05: {(best.p_any < 0.05).sum()} (v1: {(v1c.p_any < 0.05).sum()}); "
          f"best score >= 0.5: {(best.score >= 0.5).sum()}; mass-defect inconsistent best: {(~best.mass_defect_ok).sum()}", file=sys.stderr)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else v1.MAX_MR)
