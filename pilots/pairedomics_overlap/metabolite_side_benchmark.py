"""Test of the claim "the metabolite side (mass, structure) singles out the right pathway", with known answers.

Leave-one-out on PlantMetWiki itself: every compound with a structure that is a member of a pathway (>= 3 other compounds with a structure)
is hidden, and each method ranks all such pathways for it using only the metabolite side:
  - structure: similarity (Tanimoto) of the compound to the other compounds of the pathway, per fingerprint, aggregated by max or top-3 mean
  - mass:      only the neutral mass: (a) a specific conjugation delta (acetyl, hexose, pentose, deoxyhexose, caffeoyl, feruloyl, coumaroyl,
               sulfate, glucuronide) to another compound of the pathway; (b) the relative mass defect close to that of the pathway
  - baselines: pathway size (big pathways are more likely) and random
Metrics: top-1 / top-5 / top-10 hit rate (ties count as the midpoint), median rank as a fraction of the pathways, and the random expectation.
The THT case: the same scores for the hypothesis structure (an oracle: the structure is the hypothesis) and for its mass alone.

Run:  python metabolite_side_benchmark.py    -> results/metabolite_side_benchmark.csv, results/metabolite_side_tht.json
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator as G
from rdkit.Chem.Descriptors import ExactMolWt

RDLogger.DisableLog("rdApp.*")
HERE = Path(__file__).parent
DATA, RES = HERE / "data", HERE / "results"
PW_FILE = HERE.parent / "metabolomics_overlap" / "data" / "plantmetwiki_metabolite_pathways.csv"
MIN_MEMBERS = 4                       # >= 3 other compounds after hiding one
PPM = 5.0
SPECIFIC = [42.010565, 162.052824, 132.042259, 146.057909, 162.031694, 176.047344, 146.036779, 79.956815, 176.032088]
GENERIC = [2.01565, 15.994915, 14.01565, 18.010565]
HYPOTHESIS = "O=C(/C=C/c1ccc(O)c(O)c1)NCCc1ccc(O)cc1"          # caffeoyltyramine (hand-written, checked in PubChem)
THT_PATHWAY = "PWY-5474"
FPS = {"Morgan r2 bits": (G.GetMorganGenerator(radius=2, fpSize=2048), False), "Morgan r2 counts": (G.GetMorganGenerator(radius=2, fpSize=2048), True),
       "atom pairs counts": (G.GetAtomPairGenerator(fpSize=2048), True), "topological torsion counts": (G.GetTopologicalTorsionGenerator(fpSize=2048), True),
       "RDKit path bits": (G.GetRDKitFPGenerator(fpSize=2048), False)}


def load():
    ik = pd.read_csv(DATA / "plantmetwiki_metabolite_inchi.csv").dropna()
    ik["k14"] = ik.inchikey.str[:14]
    ik = ik.drop_duplicates("k14")
    mols, keep = [], []
    for r in ik.itertuples():
        m = Chem.MolFromInchi(r.inchi)
        if m is not None and m.GetNumHeavyAtoms() >= 6:
            mols.append(m); keep.append(r.k14)
    pw = pd.read_csv(PW_FILE, dtype=str)
    pw = pw[~pw.plantcyc_id.str.contains("RXN")]; pw["k14"] = pw.inchikey.str[:14]
    pw = pw[pw.k14.isin(keep)].drop_duplicates(["k14", "plantcyc_id"])
    idx = {k: i for i, k in enumerate(keep)}
    members = {p: np.array(sorted(idx[k] for k in g.k14)) for p, g in pw.groupby("plantcyc_id")}
    members = {p: m for p, m in members.items() if len(m) >= MIN_MEMBERS}
    return mols, keep, members


def midrank(score, true_idx):
    """Rank (1 = best) of the best true pathway; ties share the midpoint."""
    best = np.max(score[true_idx])
    gt, eq = np.sum(score > best), np.sum(score == best)
    return gt + (eq + 1) / 2.0


def evaluate(name, scores, truth, rows, n_path):
    """scores: array [n_compounds, n_pathways]; truth: list of arrays of pathway columns (per compound)."""
    ranks = np.array([midrank(scores[i], t) for i, t in enumerate(truth)])
    exp = {k: np.mean([min(1.0, len(t) * k / n_path) for t in truth]) for k in (1, 5, 10)}
    rows.append({"method": name, "compounds": len(ranks), "pathways": n_path, **{f"top{k}": round(float(np.mean(ranks <= k)), 3) for k in (1, 5, 10)},
                 "median_rank_fraction": round(float(np.median(ranks) / n_path), 3), **{f"random_top{k}": round(float(v), 3) for k, v in exp.items()}})


def main():
    mols, keep, members = load()
    plist = sorted(members); pcol = {p: j for j, p in enumerate(plist)}
    n, P = len(mols), len(plist)
    print(f"{n} compounds with a structure, {P} pathways with >= {MIN_MEMBERS} of them")
    mass = np.array([ExactMolWt(m) for m in mols]); rmd = (mass - np.round(mass)) / mass * 1e6
    # truth: pathways of the compound that keep >= 3 other members
    truth = [[] for _ in range(n)]
    for p, m in members.items():
        for i in m:
            truth[i].append(pcol[p])
    keep_i = [i for i in range(n) if truth[i]]
    truth_k = [np.array(truth[i]) for i in keep_i]
    rows = []
    size = np.array([len(members[p]) for p in plist], float)
    evaluate("baseline: pathway size", np.tile(size, (len(keep_i), 1)), truth_k, rows, P)
    rng = np.random.default_rng(1)
    evaluate("baseline: random", rng.random((len(keep_i), P)), truth_k, rows, P)

    # mass-only
    D = mass[:, None] - mass[None, :]
    def hit_matrix(deltas):
        H = np.zeros((n, n), bool)
        tol = mass[:, None] * PPM * 1e-6
        for d in deltas:
            H |= (np.abs(D - d) <= tol) | (np.abs(D + d) <= tol)
        np.fill_diagonal(H, False)
        return H
    for lab, dl in (("mass delta, specific conjugations", SPECIFIC), ("mass delta, specific + generic (2H, O, CH2, H2O)", SPECIFIC + GENERIC)):
        H = hit_matrix(dl); S = np.zeros((n, P))
        for p, m in members.items():
            S[:, pcol[p]] = H[:, m].sum(1)
        evaluate("mass-only: " + lab, S[keep_i], truth_k, rows, P)
    S = np.zeros((n, P))
    for p, m in members.items():
        S[:, pcol[p]] = -np.abs(rmd - np.median(rmd[m]))
    evaluate("mass-only: relative mass defect close to the pathway's", S[keep_i], truth_k, rows, P)

    # structure
    sims = {}
    for fname, (g, cnt) in FPS.items():
        fps = [g.GetCountFingerprint(m) if cnt else g.GetFingerprint(m) for m in mols]
        S = np.zeros((n, n), np.float32)
        for i in range(n):
            S[i] = DataStructs.BulkTanimotoSimilarity(fps[i], fps)
        np.fill_diagonal(S, -1)
        sims[fname] = S
        mx, t3 = np.zeros((n, P)), np.zeros((n, P))
        for p, m in members.items():
            sub = S[:, m]
            mx[:, pcol[p]] = sub.max(1)
            k = min(3, sub.shape[1] - 1)
            t3[:, pcol[p]] = np.sort(sub, axis=1)[:, -k:].mean(1)
        evaluate(f"structure: {fname}, max", mx[keep_i], truth_k, rows, P)
        evaluate(f"structure: {fname}, top-3 mean", t3[keep_i], truth_k, rows, P)
    res = pd.DataFrame(rows)
    res.to_csv(RES / "metabolite_side_benchmark.csv", index=False)
    print(res.to_string())

    # the THT case
    q = Chem.MolFromSmiles(HYPOTHESIS); mq = ExactMolWt(q); neutral = 300.1225 - 1.007276
    out = {"hypothesis_exact_mass": round(mq, 4), "feature_neutral_mass": round(neutral, 4), "pathways": P, "tht_pathway_members_with_structure": int(len(members.get(THT_PATHWAY, []))), "ranks": {}}
    if THT_PATHWAY in pcol:
        j = pcol[THT_PATHWAY]
        for fname, (g, cnt) in FPS.items():
            fq = g.GetCountFingerprint(q) if cnt else g.GetFingerprint(q)
            fps = [g.GetCountFingerprint(m) if cnt else g.GetFingerprint(m) for m in mols]
            s = np.array(DataStructs.BulkTanimotoSimilarity(fq, fps))
            mx = np.array([s[members[p]].max() for p in plist]); t3 = np.array([np.sort(s[members[p]])[-3:].mean() for p in plist])
            for agg, sc in (("max", mx), ("top-3 mean", t3)):
                out["ranks"][f"structure oracle: {fname}, {agg}"] = float(midrank(sc, np.array([j])))
        for lab, dl in (("specific", SPECIFIC), ("specific + generic", SPECIFIC + GENERIC)):
            sc = np.array([sum(any(abs((neutral - mm) - s_ * d) / neutral * 1e6 <= PPM for d in dl for s_ in (1, -1)) for mm in mass[members[p]]) for p in plist], float)
            out["ranks"][f"mass-only: delta {lab}"] = float(midrank(sc, np.array([j])))
            out["ranks"][f"mass-only: delta {lab}: pathways with any hit"] = int((sc > 0).sum())
        sc = np.array([-abs(rmd_q - np.median(rmd[members[p]])) for p in plist for rmd_q in [(neutral - round(neutral)) / neutral * 1e6]])
        out["ranks"]["mass-only: relative mass defect"] = float(midrank(sc, np.array([j])))
        out["ranks"]["baseline: pathway size"] = float(midrank(size, np.array([j])))
    (RES / "metabolite_side_tht.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
