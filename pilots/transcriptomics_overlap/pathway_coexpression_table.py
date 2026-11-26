"""Pathway co-expression table: are the genes of a PlantMetWiki pathway co-expressed more than random gene sets?

No nf-core pipeline computes this (see README.md), so it is our own step between the nf-core
outputs and the converter (to_turtle.py pathway_coexpression). The pathway co-expression claim in
README.md.

Input: a matrix with the columns of nf-core/rnaseq's salmon.merged.gene_tpm.tsv (gene_id, gene_name, one
column per sample): the nf-core output itself, or an adapter output (adapters.py).
Genes and pathways: the latest PlantMetWiki snapshots in data/ (gene nodes with a Solyc locus;
gene -> pathway membership, written by nfcore_to_turtle.py --refresh-pathways). Only pathways (PC), not
reactions (RC). Genes matched on the Solyc locus ("gene-" prefix and version removed; rows of one locus summed).

Per pathway with at least --min-genes of its genes present in the matrix (with non-zero variance):
  mean_r        mean Pearson r over all pairs of these genes (on the transformed values)
  null_mean, null_sd
                mean and SD of the same statistic for --n-random random gene sets of the same size,
                drawn without replacement from all genes with variance (the gene universe)
  empirical_p   (1 + number of random sets with mean r >= mean_r) / (1 + n_random), one-sided
  null_z        (mean_r - null_mean) / null_sd, for reading only
The random generator is numpy default_rng(--seed), so the table is reproducible.

Output: the table --out (default pathway_coexpression.tsv next to the matrix) and, next to it with the
same name, <name>.provenance.json.

Usage (from this folder; numpy and pandas, see requirements.txt):
  .venv/bin/python pathway_coexpression_table.py MATRIX --unit UNIT
      --transform log2p1|none [--n-random 10000] [--seed 20261112] [--min-genes 3] [--source-note TEXT] [--out DIR]
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
from pathlib import Path

import numpy as np
import pandas as pd

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



def mean_pair_r(z, rows):
    """Mean Pearson r over all pairs of rows of z (rows z-scored with population SD, so r_ij = z_i.z_j / n):
    sum over i != j of r_ij = |sum_i z_i|^2 / n - k."""
    k, n = len(rows), z.shape[1]
    s = z[rows].sum(axis=0)
    return (s @ s / n - k) / (k * (k - 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("matrix", type=Path)
    ap.add_argument("--unit", required=True, help="unit of the matrix values (TPM, FPKM, RPKM, counts, or free text)")
    ap.add_argument("--transform", choices=["log2p1", "none"], required=True)
    ap.add_argument("--n-random", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--min-genes", type=int, default=3)
    ap.add_argument("--source-note", default="")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    matrix = Path(os.path.abspath(a.matrix))
    out = (a.out or matrix.parent / "pathway_coexpression.tsv").resolve()
    prov_file = out.with_name(out.stem + ".provenance.json")

    gsnap = sorted(DATA.glob("plantmetwiki_tomato_gene_nodes_*.tsv"))[-1]
    psnap = sorted(DATA.glob("plantmetwiki_tomato_gene_pathways_*.tsv"))[-1]
    genes = pd.read_csv(gsnap, sep="\t", comment="#", dtype=str)
    genes["locus"] = genes["solyc"].map(locus)
    genes = genes.drop_duplicates("gene_node")
    member = pd.read_csv(psnap, sep="\t", comment="#", dtype=str)
    member = member[member["pathway"].str.contains(r"/pathways/PC\d+$")]          # pathways, not reactions
    member = member.merge(genes[["gene_node", "label", "locus"]], on="gene_node")

    df = pd.read_csv(matrix, sep="\t")
    samples = [c for c in df.columns if c not in ("gene_id", "gene_name")]
    m = df[samples].astype(float)
    m.index = df["gene_id"].map(locus)
    m = m.groupby(level=0).sum()
    if a.transform == "log2p1":
        m = np.log2(m + 1)
    m = m[m.var(axis=1) > 0]
    z = m.to_numpy()
    z = (z - z.mean(axis=1, keepdims=True)) / z.std(axis=1, keepdims=True)
    pos = {g: i for i, g in enumerate(m.index)}
    rng = np.random.default_rng(a.seed)
    null_cache = {}

    rows = []
    for (pw, pc, title), grp in member.groupby(["pathway", "plantcyc", "title"]):
        present = sorted(set(grp["locus"]) & set(pos))
        k = len(present)
        if k < a.min_genes:
            print(f"  {pw.rsplit('/', 1)[1]} {title}: {k} of {grp['locus'].nunique()} genes in the matrix, skipped")
            continue
        obs = mean_pair_r(z, [pos[g] for g in present])
        if k not in null_cache:
            null_cache[k] = np.array([mean_pair_r(z, rng.choice(len(m), size=k, replace=False))
                                      for _ in range(a.n_random)])
        null = null_cache[k]
        labels = grp.drop_duplicates("locus").set_index("locus")["label"]
        rows.append({"pathway": pw, "plantcyc": pc, "title": title,
                     "genes_in_pathway": grp["locus"].nunique(), "genes_used": k,
                     "loci": ",".join(present), "labels": ",".join(labels[g] for g in present),
                     "mean_r": obs, "null_mean": null.mean(), "null_sd": null.std(ddof=1),
                     "null_z": (obs - null.mean()) / null.std(ddof=1),
                     "empirical_p": (1 + int((null >= obs).sum())) / (1 + a.n_random), "n_random": a.n_random})

    out.parent.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(rows)
    table.to_csv(out, sep="\t", index=False)
    prov = {
        "script": "pilots/transcriptomics_overlap/pathway_coexpression_table.py", "run_on": datetime.date.today().isoformat(),
        "matrix": rel(matrix), "matrix_md5": md5(matrix), "source_note": a.source_note, "unit": a.unit,
        "transform": {"log2p1": "log2(x + 1)", "none": "none (values as given)"}[a.transform],
        "statistic": "mean Pearson r over all pairs of the pathway's genes present in the matrix",
        "null": f"{a.n_random} random gene sets of the same size, without replacement, from the genes with variance; "
                f"one null distribution per set size, numpy default_rng({a.seed})",
        "empirical_p": "(1 + #random >= observed) / (1 + n_random), one-sided",
        "n_random": a.n_random, "seed": a.seed, "min_genes": a.min_genes,
        "genes_with_variance": len(m), "samples": len(samples), "pathways": len(table),
        "plantmetwiki_genes": rel(gsnap), "plantmetwiki_pathways": rel(psnap),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
    }
    prov_file.write_text(json.dumps(prov, indent=2) + "\n")
    print(f"{matrix.name}: {len(m)} genes with variance, {len(samples)} samples; wrote {rel(out)} "
          f"({len(table)} pathways) and {prov_file.name}")
    if len(table):
        print(table[["pathway", "title", "genes_used", "mean_r", "null_mean", "null_z", "empirical_p"]]
              .assign(pathway=lambda t: t.pathway.str.rsplit("/", n=1).str[1]).to_string(index=False))


if __name__ == "__main__":
    main()
