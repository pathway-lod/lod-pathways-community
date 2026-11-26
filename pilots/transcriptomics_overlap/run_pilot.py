"""Run the transcriptomics pilot: download, reshape, compute the tables in results/.

Steps (each one a script in this folder, run with the same Python):
  1. download_inputs.py      Expression Atlas E-MTAB-11876, MEANtools rnaseq.rpkm.csv, ATTED-II Sly-r.c6-0,
                             Ensembl Plants 63 Solyc <-> NCBI Gene ID (MD5-checked) -> data/downloads/
  2. adapters.py             reshape them into nf-core output files -> data/downloads/nfcore_shaped/
  3. export_differential.py  DESeq2 results of the PlantMetWiki genes and run metadata -> results/differential_<study>.*
  4. coexpression_table.py, expression_profile_table.py, pathway_coexpression_table.py -> results/<kind>_<study>.*
     (each: a table <name>.tsv and its <name>.provenance.json)
Then shape_constraints/build_rdf.py transcriptomics turns results/ into RDF and validates it.

The nf-core route (nf-core/rnaseq on the E-MTAB-11876 reads, nf-core/differentialabundance on its counts and
on the Atlas counts) needs Nextflow and Docker and about 6 GB of reads (nfcore/, README.md). Its outputs are
used when they are in data/downloads/nfcore/; otherwise the committed results of those routes are kept:
  differential_EMTAB11876_nfcore_salmon, differential_EMTAB11876_atlas_counts, coexpression_EMTAB11876_nfcore_salmon.

Usage (from this folder): .venv/bin/python run_pilot.py [--no-download]
The inputs folder can be moved with the environment variable TX_PILOT_DOWNLOADS (default data/downloads).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parent
RESULTS = PILOT / "results"
DL = Path(os.environ.get("TX_PILOT_DOWNLOADS", PILOT / "data/downloads")).resolve()
SHAPED = DL / "nfcore_shaped"
NFCORE = DL / "nfcore"
MATRIX = "rnaseq/salmon/salmon.merged.gene_tpm.tsv"

NOTE_MEANTOOLS = "MEANtools rnaseq.rpkm.csv (Zenodo 15697913), RPKM, reshaped by adapters.py"
NOTE_ATTED = "ATTED-II Sly-r.c6-0, log2 ComBat (NCBI Gene IDs mapped one-to-one to Ensembl Plants 63 where possible)"
NOTE_NFCORE = "E-MTAB-11876 reads, nf-core/rnaseq 3.27.0 Salmon TPM"


def run(script, *args):
    cmd = [sys.executable, str(PILOT / script), *map(str, args)]
    print("\n$ " + " ".join([Path(cmd[0]).name, *cmd[1:]]).replace(str(PILOT) + "/", ""), flush=True)
    subprocess.run(cmd, check=True, cwd=PILOT)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-download", action="store_true", help="use the files already in data/downloads/")
    a = ap.parse_args()
    if not a.no_download:
        run("download_inputs.py")
    run("adapters.py")

    # differential expression: published Atlas results (adapter); nf-core routes if their outputs are here
    run("export_differential.py", SHAPED / "E-MTAB-11876_atlas", "--study", "EMTAB11876_atlas_published")
    for src, study in [("nfcore", "EMTAB11876_nfcore_salmon"), ("atlas", "EMTAB11876_atlas_counts")]:
        d = NFCORE / f"differentialabundance_E-MTAB-11876_{src}"
        if d.exists():
            run("export_differential.py", d, "--study", study)
        else:
            print(f"\n(no {d.name} in data/downloads/nfcore/: results/differential_{study}.tsv kept as committed)")

    # response profile (only the MEANtools set has enough conditions)
    m = SHAPED / "meantools_rpkm"
    run("expression_profile_table.py", m / MATRIX, m / "differentialabundance/samplesheet.csv", "--factors", "treatment,time_h",
        "--unit", "RPKM", "--transform", "log2p1", "--source-note", NOTE_MEANTOOLS,
        "--out", RESULTS / "expression_profile_meantools_rpkm.tsv")

    # gene-pair and pathway co-expression
    sets = [(m / MATRIX, "RPKM", "log2p1", NOTE_MEANTOOLS, "meantools_rpkm", True),
            (SHAPED / "atted_Sly-r.c6-0" / MATRIX, "log2 expression, ComBat-corrected", "none", NOTE_ATTED, "atted_Sly_r_c6_0", True),
            (NFCORE / "rnaseq_E-MTAB-11876/salmon/salmon.merged.gene_tpm.tsv", "TPM", "log2p1", NOTE_NFCORE, "EMTAB11876_nfcore_salmon", False)]
    for matrix, unit, transform, note, study, pathways in sets:
        if not matrix.exists():
            print(f"\n(no {matrix.name} for {study}: results/coexpression_{study}.tsv kept as committed)")
            continue
        common = ["--unit", unit, "--transform", transform, "--source-note", note]
        run("coexpression_table.py", matrix, *common, "--out", RESULTS / f"coexpression_{study}.tsv")
        if pathways:      # not on E-MTAB-11876: 6 samples are too few for a correlation per pathway
            run("pathway_coexpression_table.py", matrix, *common, "--out", RESULTS / f"pathway_coexpression_{study}.tsv")
    print("\nnext: cd ../../shape_constraints && .venv/bin/python build_rdf.py transcriptomics")


if __name__ == "__main__":
    main()
