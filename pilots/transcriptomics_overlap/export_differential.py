"""Export a differential expression result to the small files the converter reads (results/differential_<study>.*).

Input: an nf-core/differentialabundance 2.0.0 output folder, or an adapter folder written by adapters.py
(same layout, with provenance.json instead of pipeline_info/). The full DESeq2 tables cover all genes
(about 35,000 rows) and stay in data/downloads/; this step keeps what the claims need:

  results/differential_<study>.tsv                  DESeq2 columns for the PlantMetWiki tomato genes only
                                                    (gene_id as in the input, plus the Solyc locus)
  results/differential_<study>.provenance.json      software, version and parameters, input matrix,
                                                    normalised output, contrasts, and per condition the
                                                    replicate count and plant structure (from the samplesheet)

Usage (from this folder; run_pilot.py calls it):
  .venv/bin/python export_differential.py DIR --study ID [--samplesheet CSV --contrasts CSV]
  The samplesheet and contrasts default to the files the run used (nf-core params.json, or the adapter
  folder); if that path does not exist here, the file of the same name in nfcore/ is used.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import pandas as pd

PILOT = Path(__file__).resolve().parent
DATA = PILOT / "data"
RESULTS = PILOT / "results"


def locus(gene_id):
    """Solyc locus without "gene-" prefix and version suffix."""
    return re.sub(r"\.\d+$", "", re.sub(r"^gene-", "", str(gene_id).strip()))


def find(path_text):
    """A file named in a run's parameters: as given (relative to the working directory), else in nfcore/."""
    p = Path(path_text)
    return p if p.exists() else PILOT / "nfcore" / p.name


def run_info(d):
    prov_file = d / "provenance.json"
    if prov_file.exists():                                  # adapter folder
        prov = json.loads(prov_file.read_text())
        counts = "".join(f"; {v}" for k, v in prov["files"].items() if k.endswith("gene_counts.tsv"))
        return {
            "software": "Expression Atlas" if "Atlas" in prov["dataset"] else prov["dataset"],
            "version": prov["processing_by_source"],
            "note": f"published results, reshaped by {prov['adapter']} on {prov['adapted_on']}",
            "input": f"raw read counts used by the source for its published results{counts}",
            "p_adjust": "BH",                               # DESeq2 results() default; Atlas does not change it
            "normalised": "median-of-ratios normalised counts computed by the source's DESeq2 (not published)",
            "samplesheet": d / "differentialabundance/samplesheet.csv",
            "contrasts": d / "differentialabundance/contrasts.csv",
            "results_root": d / "differentialabundance/tables/differential",
        }
    info = d / "pipeline_info"                              # nf-core/differentialabundance output
    params = json.loads(sorted(info.glob("params_*.json"))[-1].read_text())
    versions = (info / "nf_core_differentialabundance_software_versions.yml").read_text()
    wf = re.search(r"nf-core/differentialabundance:\s*v?([\w.]+)", versions).group(1)
    deseq2 = re.search(r"DESEQ2_DIFFERENTIAL:\s*\n(?:\s+.*\n)*?\s+bioconductor-deseq2:\s*([\d.]+)", versions).group(1)
    version = (f"nf-core/differentialabundance {wf.split('-')[0]}; DESeq2 {deseq2}; test {params['deseq2_test']}, "
               f"p adjustment {params['deseq2_p_adjust_method']} (alpha {params['deseq2_alpha']}), "
               f"LFC shrinkage {'on' if params['deseq2_shrink_lfc'] else 'off'}")
    matrix = Path(params["matrix"])
    rnaseq_versions = list(matrix.parents[1].glob("pipeline_info/nf_core_rnaseq_software_mqc_versions.yml"))
    if rnaseq_versions:                                     # counts from nf-core/rnaseq
        v = rnaseq_versions[0].read_text()
        rs = re.search(r"nf-core/rnaseq:\s*v?([\d.]+)", v).group(1)
        salmon = re.search(r"SALMON_QUANT:\s*\n\s+salmon:\s*([\d.]+)", v)
        version += f"; counts: nf-core/rnaseq {rs}" + (f", Salmon {salmon.group(1)}" if salmon else "")
    norm = sorted((d / "tables/processed_abundance").glob("*/all.normalised_counts.tsv"))
    return {
        "software": "nf-core/differentialabundance (DESeq2)",
        "version": version,
        "note": f"study {params['study_name']}",
        "input": f"{matrix.name}, the count matrix DESeq2 read",
        "p_adjust": params["deseq2_p_adjust_method"],
        "normalised": f"{norm[0].name} (differentialabundance output)" if norm
                      else "median-of-ratios normalised counts (not found in the output folder)",
        "samplesheet": find(params["input"]),
        "contrasts": find(params["contrasts"]),
        "results_root": d / "tables/differential",
    }


def one_value(sheet, mask, col):
    if col not in sheet.columns:
        return None
    vals = sheet.loc[mask, col].dropna().unique()
    return str(vals[0]) if len(vals) == 1 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dir", type=Path)
    ap.add_argument("--study", required=True, help="identifier of the run (results/differential_<study>.tsv)")
    ap.add_argument("--samplesheet", type=Path)
    ap.add_argument("--contrasts", type=Path)
    a = ap.parse_args()
    d = a.dir.resolve()
    info = run_info(d)
    sheet = pd.read_csv(a.samplesheet or info["samplesheet"], dtype=str)
    contrasts = pd.read_csv(a.contrasts or info["contrasts"], dtype=str).fillna("")

    snap = sorted(DATA.glob("plantmetwiki_tomato_gene_nodes_*.tsv"))[-1]
    genes = pd.read_csv(snap, sep="\t", comment="#", dtype=str)
    loci = set(genes["solyc"].map(locus))

    rows, design = [], []
    for c in contrasts.itertuples():
        files = list(info["results_root"].glob(f"*/{c.id}_*.deseq2.results.tsv")) or \
                list(info["results_root"].glob(f"*/{c.id}.deseq2.results.tsv"))
        if len(files) != 1:
            sys.exit(f"contrast {c.id}: expected one results file under {info['results_root']}, found {files}")
        res = pd.read_csv(files[0], sep="\t")
        res.insert(1, "locus", res["gene_id"].map(locus))
        res = res[res["locus"].isin(loci)].drop_duplicates("locus")
        res.insert(0, "contrast", c.id)
        rows.append(res)
        conditions = {}
        for value in (c.target, c.reference):
            mask = sheet[c.variable] == value
            conditions[value] = {"replicates": int(mask.sum()),
                                 "plant_structure": one_value(sheet, mask, "plant_structure"),
                                 "plant_structure_note": one_value(sheet, mask, "plant_structure_note")}
        design.append({"id": c.id, "variable": c.variable, "target": c.target, "reference": c.reference,
                       "blocking": c.blocking, "conditions": conditions})

    out = RESULTS / f"differential_{a.study}.tsv"
    RESULTS.mkdir(parents=True, exist_ok=True)
    table = pd.concat(rows)
    table.to_csv(out, sep="\t", index=False, na_rep="NA")
    meta = {k: (str(v) if isinstance(v, Path) else v) for k, v in info.items()
            if k not in ("samplesheet", "contrasts", "results_root")}
    meta.update({"exported_by": "pilots/transcriptomics_overlap/export_differential.py",
                 "exported_on": datetime.date.today().isoformat(), "source_folder": d.name,
                 "plantmetwiki_genes": f"data/{snap.name}", "contrasts": design})
    out.with_name(out.stem + ".provenance.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote results/{out.name}: {len(table)} rows (PlantMetWiki genes), and {out.stem}.provenance.json")


if __name__ == "__main__":
    main()
