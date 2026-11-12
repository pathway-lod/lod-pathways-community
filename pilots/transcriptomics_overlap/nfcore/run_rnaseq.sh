#!/usr/bin/env bash
# nf-core/rnaseq 3.27.0 on E-MTAB-11876, Salmon only (no STAR alignment: lower RAM).
# Outputs and the Nextflow work directory go to pilots/transcriptomics_overlap/data/downloads/nfcore/ (ignored by git).
#
# Usage (from the repository root, after download_inputs.sh):
#   bash pilots/transcriptomics_overlap/nfcore/run_rnaseq.sh            # add -resume to continue a stopped run
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
NF_ENV="${NF_ENV:-$HOME/miniconda3/envs/nextflow}"   # conda env with Nextflow >= 25.10.4 and Java
export JAVA_HOME="$NF_ENV" PATH="$NF_ENV/bin:$PATH"
OUT=pilots/transcriptomics_overlap/data/downloads/nfcore
PFX=pilots/transcriptomics_overlap/data/downloads/ensembl/Solanum_lycopersicum_gca000188115v5cm.SL4.0

nextflow run nf-core/rnaseq -r 3.27.0 -profile docker \
    -c pilots/transcriptomics_overlap/nfcore/workstation.config \
    -work-dir "$OUT/work" \
    --input pilots/transcriptomics_overlap/nfcore/rnaseq_samplesheet_E-MTAB-11876.csv \
    --outdir "$OUT/rnaseq_E-MTAB-11876" \
    --fasta "$PFX.dna.toplevel.fa.gz" \
    --gtf "$PFX.63.gtf.gz" \
    --skip_alignment --pseudo_aligner salmon \
    --save_reference \
    "$@"
