"""Reshape the current tomato TX datasets into the files nf-core pipelines write.

The converter to Turtle reads only nf-core output files (nf-core/rnaseq 3.27.0,
nf-core/differentialabundance 2.0.0; formats in README.md). This script writes
the same files from data that did not go through those pipelines, so the converter can read them too:

  E-MTAB-11876 (Expression Atlas)
    raw counts (TopHat2 + HTSeq)  -> rnaseq/salmon/salmon.merged.gene_counts.tsv
    condensed SDRF + configuration -> samplesheet + contrasts (also used for the real
                                      differentialabundance run: nfcore/)
    analytics (log2FC, adjusted p) -> differentialabundance/tables/differential/rnaseq/<contrast>_<study>.deseq2.results.tsv
  MEANtools rnaseq.rpkm.csv        -> rnaseq/salmon/salmon.merged.gene_tpm.tsv (unit RPKM)
                     sample names -> differentialabundance/samplesheet.csv (treatment, time_h, replicate)
  ATTED-II Sly-r.c6-0 matrix       -> rnaseq/salmon/salmon.merged.gene_tpm.tsv (log2, ComBat)

Usage (from this folder; inputs from download_inputs.py; run_pilot.py calls it):
  .venv/bin/python adapters.py
Writes data/downloads/nfcore_shaped/<dataset>/ (ignored by git) and the samplesheet and contrasts
for E-MTAB-11876 to nfcore/.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PILOT = Path(__file__).resolve().parent
DL = Path(os.environ.get("TX_PILOT_DOWNLOADS", PILOT / "data/downloads")).resolve()
OUT = DL / "nfcore_shaped"
NFCORE = PILOT / "nfcore"
TODAY = datetime.date.today().isoformat()

ATLAS = "https://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/E-MTAB-11876"
DESEQ2_COLUMNS = ["gene_id", "baseMean", "log2FoldChange", "lfcSE", "stat", "pvalue", "padj"]
CONTRAST_ID = "jasmonate_vs_none"
# differentialabundance 2.0.0 names results <contrast>_<study_name> in a folder per paramset (rnaseq)
STUDY = "E-MTAB-11876_atlas_published"


PLANT_STRUCTURE = {"root": "PO:0009005", "leaf": "PO:0025034"}   # TX-19, Plant Ontology (checked in OLS4)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source(path, url):
    return {"file": str(path.relative_to(DL)), "url": url, "md5": md5(path)}


def write_tsv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False, na_rep="NA")
    print(f"wrote {path.relative_to(DL.parent) if path.is_relative_to(DL.parent) else path}  ({len(df)} rows, {df.shape[1]} columns)")


def write_provenance(dataset_dir, prov):
    prov = {"adapter": "pilots/transcriptomics_overlap/adapters.py", "adapted_on": TODAY, **prov}
    path = dataset_dir / "provenance.json"
    path.write_text(json.dumps(prov, indent=2) + "\n")
    print(f"wrote {path.relative_to(DL.parent) if path.is_relative_to(DL.parent) else path}")


def matrix(df_values, gene_ids, gene_names=None):
    """nf-core gene matrix layout: gene_id, gene_name, one column per sample.
    As in nf-core/rnaseq output, gene_name repeats gene_id where the gene has no name."""
    ids = [str(g) for g in gene_ids]
    names = [str(n) if isinstance(n, str) and n else i
             for i, n in zip(ids, gene_names if gene_names is not None else [""] * len(ids))]
    out = df_values.copy()
    out.insert(0, "gene_name", names)
    out.insert(0, "gene_id", ids)
    return out.reset_index(drop=True)


# --- E-MTAB-11876 (Expression Atlas) -------------------------------------------------------------
def atlas():
    src = DL / "E-MTAB-11876"
    d = OUT / "E-MTAB-11876_atlas"
    f_counts = src / "E-MTAB-11876-raw-counts.tsv"
    f_sdrf = src / "E-MTAB-11876.condensed-sdrf.tsv"
    f_conf = src / "E-MTAB-11876-configuration.xml"
    f_anal = src / "E-MTAB-11876-analytics.tsv"

    # design: SDRF factor "compound" per run, cross-checked with the configuration's assay groups
    sdrf = pd.read_csv(f_sdrf, sep="\t", header=None, names=["exp", "x", "run", "kind", "key", "value"])
    compound = sdrf[(sdrf.kind == "factor") & (sdrf.key == "compound")].set_index("run")["value"]
    organ = sdrf[(sdrf.kind == "characteristic") & (sdrf.key == "organism part")].set_index("run")["value"]
    conf = ET.parse(f_conf).getroot()
    groups = {g.get("id"): [a.text for a in g.findall("assay")] for g in conf.iter("assay_group")}
    c = conf.find(".//contrast")
    ref, test = c.findtext("reference_assay_group"), c.findtext("test_assay_group")
    assert set(compound[groups[ref]]) == {"none"} and set(compound[groups[test]]) == {"jasmonate"}, \
        "SDRF and configuration.xml disagree on the groups"
    runs = sorted(compound.index)

    # samplesheet for differentialabundance = rnaseq samplesheet + treatment column + plant structure
    # (TX-19: SDRF "organism part" as a PO term; the roots are hairy roots, which have no PO term)
    rnaseq_sheet = pd.read_csv(NFCORE / "rnaseq_samplesheet_E-MTAB-11876.csv", dtype=str).fillna("")
    assert sorted(rnaseq_sheet["sample"]) == runs
    sheet = rnaseq_sheet.assign(treatment=rnaseq_sheet["sample"].map(compound),
                                plant_structure=rnaseq_sheet["sample"].map(organ).map(PLANT_STRUCTURE),
                                plant_structure_note="hairy root (Agrobacterium rhizogenes ATCC 15834); no PO term")
    assert sheet["plant_structure"].notna().all(), f"organism part without a PO term: {set(organ)}"
    contrasts = pd.DataFrame([{"id": CONTRAST_ID, "variable": "treatment", "reference": "none",
                               "target": "jasmonate", "blocking": ""}])
    (d / "differentialabundance").mkdir(parents=True, exist_ok=True)
    for df, name in [(sheet, "samplesheet"), (contrasts, "contrasts")]:
        df.to_csv(NFCORE / f"differentialabundance_{name}_E-MTAB-11876.csv", index=False)
        df.to_csv(d / "differentialabundance" / f"{name}.csv", index=False)
        print(f"wrote pilots/transcriptomics_overlap/nfcore/differentialabundance_{name}_E-MTAB-11876.csv")

    # count matrix
    counts = pd.read_csv(f_counts, sep="\t", dtype={"Gene Name": str})
    assert sorted(counts.columns[2:]) == runs
    write_tsv(matrix(counts[runs], counts["Gene ID"], counts["Gene Name"].fillna("")),
              d / "rnaseq/salmon/salmon.merged.gene_counts.tsv")

    # DESeq2 results shape. Atlas gives one p-value column; it is the adjusted p-value (padj):
    # 2,337 genes with counts (up to 684 reads in total) have NA, which in DESeq2 only independent
    # filtering produces, and independent filtering sets padj only. pvalue, baseMean, lfcSE, stat
    # are not published by Atlas and stay empty. Atlas writes log2FC 0 for genes with no reads at
    # all; DESeq2 gives NA there, so those are set to NA.
    anal = pd.read_csv(f_anal, sep="\t")
    cid = c.get("id")
    res = pd.DataFrame({"gene_id": anal["Gene ID"]})
    for col in DESEQ2_COLUMNS[1:]:
        res[col] = np.nan
    res["log2FoldChange"] = anal[f"{cid}.log2foldchange"]
    res["padj"] = anal[f"{cid}.p-value"]
    zero = counts.set_index("Gene ID")[runs].sum(axis=1).reindex(res["gene_id"]).fillna(0).to_numpy() == 0
    res.loc[zero, "log2FoldChange"] = np.nan
    write_tsv(res[DESEQ2_COLUMNS], d / f"differentialabundance/tables/differential/rnaseq/{CONTRAST_ID}_{STUDY}.deseq2.results.tsv")

    write_provenance(d, {
        "dataset": "E-MTAB-11876 (Expression Atlas)",
        "sources": [source(f_counts, f"{ATLAS}/E-MTAB-11876-raw-counts.tsv"),
                    source(f_sdrf, f"{ATLAS}/E-MTAB-11876.condensed-sdrf.tsv"),
                    source(f_conf, f"{ATLAS}/E-MTAB-11876-configuration.xml"),
                    source(f_anal, f"{ATLAS}/E-MTAB-11876-analytics.tsv")],
        "processing_by_source": "Expression Atlas iRAP 1.0.3: TopHat2 2.1.1 on Ensembl Genomes 53, "
                                "HTSeq 0.11.0, DESeq2 1.22.1 (E-MTAB-11876-analysis-methods.tsv)",
        "files": {
            "rnaseq/salmon/salmon.merged.gene_counts.tsv": "HTSeq read counts (true counts, not Salmon estimates)",
            "differentialabundance/samplesheet.csv": "rnaseq samplesheet + treatment (SDRF factor compound) + plant_structure (SDRF organism part as PO term) + plant_structure_note",
            "differentialabundance/contrasts.csv": f"{CONTRAST_ID} = Atlas contrast {cid} "
                                                   f"(reference {ref} none, test {test} jasmonate 50 micromolar)",
            f"differentialabundance/tables/differential/rnaseq/{CONTRAST_ID}_{STUDY}.deseq2.results.tsv":
                "Atlas log2foldchange -> log2FoldChange; Atlas p-value (adjusted, see adapter) -> padj; "
                "baseMean, lfcSE, stat, pvalue not published (NA); whether log2FC is shrunken is not stated",
        },
        "gene_ids": "Ensembl Genomes 53 gene IDs with version (Solyc....3; also ENSRNA... for ncRNA)",
    })


# --- MEANtools rnaseq.rpkm.csv ---------------------------------------------------------------------
def meantools():
    f = DL / "meantools/rnaseq.rpkm.csv"
    d = OUT / "meantools_rpkm"
    rpkm = pd.read_csv(f)
    rpkm.columns = rpkm.columns.str.strip()
    gene_col = rpkm.columns[0]
    write_tsv(matrix(rpkm.drop(columns=gene_col), rpkm[gene_col]), d / "rnaseq/salmon/salmon.merged.gene_tpm.tsv")
    # samplesheet in nf-core/differentialabundance form (sample + one column per factor), from the
    # column names <treatment>_<time>h_<replicate>; the meaning of the treatment codes is not in the file
    samples = [c for c in rpkm.columns if c != gene_col]
    parts = [re.fullmatch(r"(.+)_(\d+)h_(\d+)", s) for s in samples]
    if not all(parts):
        sys.exit(f"meantools: sample names not of the form <treatment>_<time>h_<replicate>: "
                 f"{[s for s, p in zip(samples, parts) if not p]}")
    sheet = pd.DataFrame({"sample": samples, "treatment": [p.group(1) for p in parts],
                          "time_h": [int(p.group(2)) for p in parts], "replicate": [int(p.group(3)) for p in parts],
                          "plant_structure": PLANT_STRUCTURE["leaf"]})   # leaves (Jeon et al. 2020), not in the file
    (d / "differentialabundance").mkdir(parents=True, exist_ok=True)
    sheet.to_csv(d / "differentialabundance/samplesheet.csv", index=False)
    write_provenance(d, {
        "dataset": "MEANtools tomato RNA-seq (Zenodo 15697913, reads PRJNA509154)",
        "sources": [source(f, "https://zenodo.org/records/15697913/files/rnaseq.rpkm.csv")],
        "processing_by_source": "not documented with the file",
        "files": {"rnaseq/salmon/salmon.merged.gene_tpm.tsv":
                  "RPKM as published (not TPM; file name only marks the role: normalised expression matrix)",
                  "differentialabundance/samplesheet.csv":
                  "from the column names <treatment>_<time>h_<replicate>; treatment codes as published (meaning in Jeon et al. 2020); "
                  "plant_structure leaf from Jeon et al. 2020 (not in the file)"},
        "unit": "RPKM", "transform": "none",
        "gene_ids": "ITAG gene IDs with version (Solyc....2)",
    })


# --- ATTED-II Sly-r.c6-0 ----------------------------------------------------------------------------
def atted():
    f_mat = DL / "atted/Sly-r.c6-0.expression.combat.txt.zip"
    f_ens = DL / "ensembl/Solanum_lycopersicum_gca000188115v5cm.SL4.0.63.entrez.tsv.gz"
    d = OUT / "atted_Sly-r.c6-0"
    ens = pd.read_csv(f_ens, sep="\t", dtype=str)
    pairs = ens.loc[ens["db_name"] == "EntrezGene", ["gene_stable_id", "xref"]].drop_duplicates()
    one_to_one = pairs[~pairs["gene_stable_id"].duplicated(keep=False) & ~pairs["xref"].duplicated(keep=False)]
    ncbi_to_gene = one_to_one.set_index("xref")["gene_stable_id"]

    with zipfile.ZipFile(f_mat) as zf:
        mat = pd.read_csv(zf.open(zf.infolist()[0].filename), sep="\t", index_col=0)
    mat.index = mat.index.astype(str)
    mapped = mat.index.isin(ncbi_to_gene.index)
    print(f"ATTED-II: {len(mat)} NCBI genes, {mapped.sum()} mapped one-to-one to Ensembl Plants 63, "
          f"{(~mapped).sum()} kept as ncbigene-<id>")
    # Unmapped genes stay in the matrix: they cannot match PlantMetWiki, but rank-based values
    # (mutual rank) are computed over all genes and change if genes are dropped.
    ids = [ncbi_to_gene[i] if ok else f"ncbigene-{i}" for i, ok in zip(mat.index, mapped)]
    write_tsv(matrix(mat, ids), d / "rnaseq/salmon/salmon.merged.gene_tpm.tsv")
    write_provenance(d, {
        "dataset": "ATTED-II Sly-r.c6-0 (v13.0, 2026-02-16; Zenodo 18679026)",
        "sources": [source(f_mat, "https://atted.jp/download/Sly-r.c6-0/exp/Sly-r.c6-0.expression.combat.txt.zip"),
                    source(f_ens, "https://ftp.ebi.ac.uk/ensemblgenomes/pub/plants/release-63/tsv/"
                                  "solanum_lycopersicum_gca000188115v5cm/"
                                  "Solanum_lycopersicum_gca000188115v5cm.SL4.0.63.entrez.tsv.gz")],
        "processing_by_source": "ATTED-II: 1,608 public RNA-seq runs, log2 expression, ComBat batch correction",
        "files": {"rnaseq/salmon/salmon.merged.gene_tpm.tsv":
                  "log2 ComBat-corrected expression as published (not TPM; file name only marks the role)"},
        "unit": "log2 expression (ATTED-II)", "transform": "as published",
        "gene_ids": f"NCBI Gene IDs mapped to Ensembl Plants 63 gene IDs (gene-Solyc...) where the pair is "
                    f"one-to-one ({int(mapped.sum())} of {len(mapped)}); the others kept as ncbigene-<NCBI Gene ID>",
    })


if __name__ == "__main__":
    atlas()
    meantools()
    atted()
