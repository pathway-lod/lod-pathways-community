"""Co-expression table for all pairs of selected genes, from a gene x sample matrix in nf-core layout.

No nf-core pipeline computes gene-gene co-expression (see README.md), so this is our own
step between the nf-core outputs and the converter (to_turtle.py coexpression).

Input: a matrix with the columns of nf-core/rnaseq's salmon.merged.gene_tpm.tsv (gene_id, gene_name,
one column per sample): the nf-core output itself, or an adapter output (adapters.py).
Genes: the PlantMetWiki tomato gene nodes (latest snapshot in data/), matched on the Solyc locus
("gene-" prefix and version removed; rows of the same locus summed).

Per pair (A, B): Pearson r and p-value, Spearman rho and p-value, and the mutual rank
MR = sqrt(rank of B among all genes by Pearson r with A x rank of A among all genes by r with B),
rank 1 = highest r, self excluded, over all genes of the matrix with non-zero variance.

Output: the table --out (default coexpression_pairs.tsv next to the matrix) and, next to it with the same
name, <name>.provenance.json (matrix, unit, transform, gene and sample counts, versions).

Usage (from this folder; needs scipy, see requirements.txt):
  .venv/bin/python coexpression_table.py MATRIX --unit UNIT
                                               --transform log2p1|none [--source-note TEXT] [--out DIR]
  UNIT: what the matrix values are (TPM, FPKM, RPKM, counts, or free text such as "log2 ComBat");
  the converter types the input matrix node with TPM, FPKM, RPKM or counts (TX-03, TX-04).
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy import stats

DATA = Path(__file__).resolve().parent / "data"
PILOT = Path(__file__).resolve().parent
DL = Path(os.path.abspath(os.environ.get("TX_PILOT_DOWNLOADS", PILOT / "data/downloads")))   # inputs (ignored by git)


def rel(p):
    """Path as recorded in provenance.json: data/downloads/... for inputs, else relative to the pilot."""
    p = Path(os.path.abspath(p))
    if p.is_relative_to(DL):
        return "data/downloads/" + str(p.relative_to(DL))
    if p.is_relative_to(PILOT):
        return str(p.relative_to(PILOT))
    return p.name


def locus(gene_id):
    return re.sub(r"\.\d+$", "", re.sub(r"^gene-", "", str(gene_id).strip()))


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("matrix", type=Path)
    ap.add_argument("--transform", choices=["log2p1", "none"], required=True,
                    help="log2p1: log2(x + 1) for TPM/RPKM; none: values already on a log scale")
    ap.add_argument("--unit", required=True, help="unit of the matrix values (TPM, FPKM, RPKM, counts, or free text)")
    ap.add_argument("--source-note", default="", help="what the matrix is (unit, origin), for provenance.json")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    matrix = Path(os.path.abspath(a.matrix))
    out = (a.out or matrix.parent / "coexpression_pairs.tsv").resolve()
    prov_file = out.with_name(out.stem + ".provenance.json")

    snap = sorted(DATA.glob("plantmetwiki_tomato_gene_nodes_*.tsv"))[-1]
    genes = pd.read_csv(snap, sep="\t", comment="#", dtype=str)
    genes["locus"] = genes["solyc"].map(locus)
    labels = genes.drop_duplicates("locus").set_index("locus")["label"]

    df = pd.read_csv(matrix, sep="\t")
    samples = [c for c in df.columns if c not in ("gene_id", "gene_name")]
    m = df[samples].astype(float)
    m.index = df["gene_id"].map(locus)
    m = m.groupby(level=0).sum()
    if a.transform == "log2p1":
        m = np.log2(m + 1)
    m = m[m.var(axis=1) > 0]
    sel = [g for g in labels.index if g in m.index]
    print(f"{matrix.name}: {len(m)} genes with variance, {len(samples)} samples; "
          f"{len(sel)} of {len(labels)} PlantMetWiki genes present")

    # Pearson r of every gene with each selected gene (rows z-scored, population SD)
    z = m.to_numpy()
    z = (z - z.mean(axis=1, keepdims=True)) / z.std(axis=1, keepdims=True)
    idx = [m.index.get_loc(g) for g in sel]
    r_all = z @ z[idx].T / z.shape[1]                      # genes x selected
    for j, i in enumerate(idx):
        r_all[i, j] = -np.inf                              # exclude self from ranking

    def rank(of_gene, among_col):                          # rank of gene i in column j (1 = highest r)
        return int((r_all[:, among_col] > r_all[of_gene, among_col]).sum()) + 1

    rows = []
    for (ja, ga), (jb, gb) in combinations(enumerate(sel), 2):
        x, y = m.loc[ga].to_numpy(), m.loc[gb].to_numpy()
        r, p = stats.pearsonr(x, y)
        rho, p_rho = stats.spearmanr(x, y)
        rb, ra = rank(idx[jb], ja), rank(idx[ja], jb)
        rows.append({"gene_a": ga, "label_a": labels[ga], "gene_b": gb, "label_b": labels[gb],
                     "pearson_r": r, "pearson_p": p, "spearman_rho": rho, "spearman_p": p_rho,
                     "rank_b_for_a": rb, "rank_a_for_b": ra, "mutual_rank": float(np.sqrt(rb * ra))})

    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, sep="\t", index=False)
    prov = {
        "script": "pilots/transcriptomics_overlap/coexpression_table.py", "run_on": datetime.date.today().isoformat(),
        "matrix": rel(matrix), "matrix_md5": md5(matrix), "source_note": a.source_note,
        "unit": a.unit, "transform": {"log2p1": "log2(x + 1)", "none": "none (values as given)"}[a.transform],
        "genes_with_variance": len(m), "samples": len(samples), "pairs": len(rows),
        "plantmetwiki_genes": rel(snap), "plantmetwiki_genes_present": len(sel),
        "methods": "Pearson r (scipy.stats.pearsonr), Spearman rho (scipy.stats.spearmanr), mutual rank over all genes with variance",
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                     "scipy": scipy.__version__},
    }
    prov_file.write_text(json.dumps(prov, indent=2) + "\n")
    print(f"wrote {rel(out)} ({len(rows)} pairs) and {prov_file.name}")


if __name__ == "__main__":
    main()
