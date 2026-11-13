"""Response profile table (z-score per gene and condition) from a gene x sample matrix in nf-core layout.

No nf-core pipeline computes this (see README.md), so it is our own step between the nf-core
outputs and the converter (to_turtle.py profile).

Input: a matrix with the columns of nf-core/rnaseq's salmon.merged.gene_tpm.tsv (gene_id, gene_name, one
column per sample) and a samplesheet in nf-core/differentialabundance form (column "sample" plus one column
per factor). The factors given with --factors define the conditions (e.g. treatment and time: 9 x 3 = 27
conditions for the MEANtools set). Genes: the PlantMetWiki tomato gene nodes (latest snapshot in
data/), matched on the Solyc locus ("gene-" prefix and version removed; rows of one locus summed).

Per gene and condition:
  mean_expression   mean of the replicate values in the matrix unit (TPM, RPKM, ...), TX-04
  mean_transformed  mean of the transformed replicate values (--transform)
  zscore            (mean_transformed - mean over all conditions of the gene) / SD over all conditions
                    (population SD, ddof 0), TX-06: how far this condition lies from the gene's
                    average over the experiment. Not a test against a control.
Genes whose condition means do not vary are left out.
Optional samplesheet columns plant_structure (PO term, TX-19) and plant_structure_note are copied to each
condition when they are the same for all its samples.

Output: the table --out (default expression_profile.tsv next to the matrix) and, next to it with the same
name, <name>.provenance.json.

Usage (from this folder; pandas, see requirements.txt):
  .venv/bin/python expression_profile_table.py MATRIX SAMPLESHEET \\
      --factors treatment,time_h --unit RPKM --transform log2p1|none [--source-note TEXT] [--out DIR]
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



def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("matrix", type=Path)
    ap.add_argument("samplesheet", type=Path)
    ap.add_argument("--factors", required=True, help="comma-separated samplesheet columns that define a condition")
    ap.add_argument("--unit", required=True, help="unit of the matrix values (TPM, RPKM, FPKM)")
    ap.add_argument("--transform", choices=["log2p1", "none"], required=True,
                    help="log2p1: z-scores on log2(x + 1); none: on the values as given")
    ap.add_argument("--source-note", default="", help="what the matrix is (origin), for provenance.json")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    matrix, sheet_file = Path(os.path.abspath(a.matrix)), Path(os.path.abspath(a.samplesheet))
    out = (a.out or matrix.parent / "expression_profile.tsv").resolve()
    prov_file = out.with_name(out.stem + ".provenance.json")
    factors = a.factors.split(",")

    snap = sorted(DATA.glob("plantmetwiki_tomato_gene_nodes_*.tsv"))[-1]
    genes = pd.read_csv(snap, sep="\t", comment="#", dtype=str)
    genes["locus"] = genes["solyc"].map(locus)
    labels = genes.drop_duplicates("locus").set_index("locus")["label"]

    sheet = pd.read_csv(sheet_file, dtype=str)
    missing = [f for f in ["sample"] + factors if f not in sheet.columns]
    if missing:
        raise SystemExit(f"samplesheet lacks columns {missing}")
    df = pd.read_csv(matrix, sep="\t")
    samples = [s for s in sheet["sample"] if s in df.columns]
    if len(samples) != len(sheet):
        raise SystemExit(f"samples in the samplesheet but not in the matrix: {sorted(set(sheet['sample']) - set(df.columns))}")
    m = df[samples].astype(float)
    m.index = df["gene_id"].map(locus)
    m = m.groupby(level=0).sum()
    m = m.loc[[g for g in labels.index if g in m.index]]
    t = np.log2(m + 1) if a.transform == "log2p1" else m

    cond = sheet.set_index("sample").loc[samples, factors].astype(str).agg("|".join, axis=1)
    raw_means = m.T.groupby(cond.values).mean().T            # genes x conditions
    t_means = t.T.groupby(cond.values).mean().T
    n_rep = cond.value_counts()
    # optional sample columns carried per condition (TX-19 plant structure), when constant within a condition
    extra = {}
    for col in ["plant_structure", "plant_structure_note"]:
        if col in sheet.columns:
            per = sheet.set_index("sample").loc[samples, col].astype(str).groupby(cond.values).unique()
            if any(len(v) > 1 for v in per):
                raise SystemExit(f"column {col} differs within a condition")
            extra[col] = per.map(lambda v: v[0])
    sd = t_means.std(axis=1, ddof=0)
    keep = sd > 0
    z = t_means[keep].sub(t_means[keep].mean(axis=1), axis=0).div(sd[keep], axis=0)
    print(f"{matrix.name}: {len(samples)} samples, {t_means.shape[1]} conditions ({' x '.join(factors)}); "
          f"{int(keep.sum())} of {len(labels)} PlantMetWiki genes present with varying condition means")

    rows = []
    for g in z.index:
        for c in z.columns:
            values = dict(zip(factors, c.split("|")))
            rows.append({"gene": g, "label": labels[g], "condition": c.replace("|", "_"), **values,
                         **{col: s[c] for col, s in extra.items()},
                         "replicates": int(n_rep[c]), "mean_expression": raw_means.loc[g, c],
                         "mean_transformed": t_means.loc[g, c], "zscore": z.loc[g, c]})

    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, sep="\t", index=False)
    prov = {
        "script": "pilots/transcriptomics_overlap/expression_profile_table.py", "run_on": datetime.date.today().isoformat(),
        "matrix": rel(matrix), "matrix_md5": md5(matrix), "samplesheet": rel(sheet_file),
        "source_note": a.source_note, "unit": a.unit, "factors": factors,
        "transform": {"log2p1": "log2(x + 1)", "none": "none (values as given)"}[a.transform],
        "zscore": "per gene: (condition mean - mean of all condition means) / population SD of the condition means, "
                  "on the transformed values",
        "samples": len(samples), "conditions": int(t_means.shape[1]), "genes": int(keep.sum()), "rows": len(rows),
        "plantmetwiki_genes": rel(snap),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
    }
    prov_file.write_text(json.dumps(prov, indent=2) + "\n")
    print(f"wrote {rel(out)} ({len(rows)} rows) and {prov_file.name}")


if __name__ == "__main__":
    main()
