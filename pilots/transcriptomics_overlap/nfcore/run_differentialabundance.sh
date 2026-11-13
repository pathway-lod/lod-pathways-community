#!/usr/bin/env bash
# nf-core/differentialabundance 2.0.0 (DESeq2, profile rnaseq) on E-MTAB-11876, contrast
# jasmonate_vs_none, with --deseq2_shrink_lfc false so the Wald statistic (TX-09) is kept.
#
# Usage (from the repository root):
#   bash pilots/transcriptomics_overlap/nfcore/run_differentialabundance.sh nfcore   # counts from our nf-core/rnaseq run (Salmon)
#   bash pilots/transcriptomics_overlap/nfcore/run_differentialabundance.sh atlas    # Expression Atlas HTSeq counts (adapter output)
# Add -resume to continue a stopped run.
#
# nfcore: Salmon counts need the gene lengths matrix; features come from the Ensembl Plants 63 GTF.
# atlas:  HTSeq counts are true counts (no lengths); no GTF, because the Atlas IDs (Ensembl Genomes 53,
#         no "gene-" prefix) do not match the release 63 GTF; features are taken from the matrix.
# Outputs go to pilots/transcriptomics_overlap/data/downloads/nfcore/differentialabundance_E-MTAB-11876_<source>/ (ignored by git).
set -euo pipefail

SRC="${1:?usage: run_differentialabundance.sh nfcore|atlas [nextflow options]}"; shift
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
NF_ENV="${NF_ENV:-$HOME/miniconda3/envs/nextflow}"   # conda env with Nextflow >= 25.10.4 and Java
export JAVA_HOME="$NF_ENV" PATH="$NF_ENV/bin:$PATH"
OUT="$ROOT/pilots/transcriptomics_overlap/data/downloads/nfcore"

case "$SRC" in
    nfcore)
        SALMON="$OUT/rnaseq_E-MTAB-11876/salmon"
        INPUTS=(--matrix "$SALMON/salmon.merged.gene_counts.tsv"
                --feature_length_matrix "$SALMON/salmon.merged.gene_lengths.tsv"
                --gtf pilots/transcriptomics_overlap/data/downloads/ensembl/Solanum_lycopersicum_gca000188115v5cm.SL4.0.63.gtf.gz) ;;
    atlas)
        INPUTS=(--matrix pilots/transcriptomics_overlap/data/downloads/nfcore_shaped/E-MTAB-11876_atlas/rnaseq/salmon/salmon.merged.gene_counts.tsv) ;;
    *) echo "unknown source: $SRC" >&2; exit 1 ;;
esac

nextflow run nf-core/differentialabundance -r 2.0.0 -profile rnaseq,docker \
    -c pilots/transcriptomics_overlap/nfcore/workstation.config \
    -work-dir "$OUT/work" \
    --input pilots/transcriptomics_overlap/nfcore/differentialabundance_samplesheet_E-MTAB-11876.csv \
    --contrasts pilots/transcriptomics_overlap/nfcore/differentialabundance_contrasts_E-MTAB-11876.csv \
    "${INPUTS[@]}" \
    --study_name "E-MTAB-11876_$SRC" \
    --deseq2_shrink_lfc false \
    --outdir "$OUT/differentialabundance_E-MTAB-11876_$SRC" \
    "$@"
