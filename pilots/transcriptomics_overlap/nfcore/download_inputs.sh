#!/usr/bin/env bash
# Download the nf-core/rnaseq inputs for E-MTAB-11876 into pilots/transcriptomics_overlap/data/downloads/ (ignored by git):
#   - 6 single-end runs of PRJEB53936 from the NCBI SRA copy on AWS, converted to FASTQ,
#     read counts checked against ENA
#   - Ensembl Plants release 63 tomato SL4.0 genome (toplevel) and GTF, checked with the
#     BSD `sum` values from Ensembl's CHECKSUMS files
#
# Usage: bash pilots/transcriptomics_overlap/nfcore/download_inputs.sh
# Files already present are not downloaded again (about 6 GB reads + 0.3 GB genome).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DL="$(cd "$HERE/.." && pwd)/data/downloads"

fetch() {  # fetch URL DEST
    local url="$1" dest="$2"
    mkdir -p "$(dirname "$dest")"
    if [[ -s "$dest" ]]; then
        echo "present  ${dest#"$DL"/}"
    else
        echo "download ${dest#"$DL"/}"
        # resume a partial .part file; retry on dropped connections (ENA drops long transfers)
        local i
        for i in 1 2 3 4 5 6 7 8 9 10; do
            curl -fsSL --retry 5 --retry-all-errors -C - -o "$dest.part" "$url" && break
            echo "retry $i ${dest#"$DL"/}" >&2
            sleep 10
        done
        mv "$dest.part" "$dest"
    fi
}

check_md5() {  # check_md5 FILE EXPECTED
    local got; got="$(md5sum "$1" | cut -d' ' -f1)"
    [[ "$got" == "$2" ]] || { echo "MD5 MISMATCH ${1#"$DL"/}: got $got, expected $2" >&2; exit 1; }
    echo "md5 ok   ${1#"$DL"/}"
}

check_sum() {  # check_sum FILE "CHECKSUM BLOCKS" (BSD sum, as in Ensembl CHECKSUMS)
    local got; got="$(sum "$1" | awk '{print $1+0, $2+0}')"
    [[ "$got" == "$2" ]] || { echo "SUM MISMATCH ${1#"$DL"/}: got $got, expected $2" >&2; exit 1; }
    echo "sum ok   ${1#"$DL"/}"
}

# 1. Reads: from the NCBI SRA copy on AWS (sra-pub-run-odp), not ENA. ENA served them at
#    about 0.3 MB/s with dropped connections (2026-11-11); AWS at about 19 MB/s.
#    .sra file → vdb-validate → fasterq-dump → gzip. The FASTQ is rebuilt locally, so ENA's
#    FASTQ MD5 does not apply; instead the read count is checked against ENA's read_count.
#    sra-tools and pigz come from the conda env `bioinformatics`.
BIN="${SRA_TOOLS_BIN:-$HOME/miniconda3/envs/bioinformatics/bin}"   # sra-tools and pigz
SRA=https://sra-pub-run-odp.s3.amazonaws.com/sra
FQ="$DL/E-MTAB-11876/fastq"
while read -r run reads; do
    f="$FQ/$run.fastq.gz"
    if [[ -s "$f" ]]; then
        echo "present  ${f#"$DL"/}"
    else
        fetch "$SRA/$run/$run" "$FQ/sra/$run.sra"
        "$BIN/vdb-validate" "$FQ/sra/$run.sra"
        "$BIN/fasterq-dump" --threads 8 --temp "$FQ/sra" --outdir "$FQ/sra" "$FQ/sra/$run.sra"
        got=$(( $(wc -l < "$FQ/sra/$run.fastq") / 4 ))
        [[ "$got" == "$reads" ]] || { echo "READ COUNT MISMATCH $run: got $got, ENA $reads" >&2; exit 1; }
        "$BIN/pigz" -p 8 -c "$FQ/sra/$run.fastq" > "$f.part" && mv "$f.part" "$f"
        rm "$FQ/sra/$run.fastq" "$FQ/sra/$run.sra"
    fi
    echo "reads ok ${f#"$DL"/} ($reads)"
done <<'RUNS'
ERR9883576 20048197
ERR9883577 22670264
ERR9883578 19280906
ERR9883579 20284993
ERR9883580 21853208
ERR9883581 20297115
RUNS

# 2. Genome and annotation (Ensembl Plants 63, SL4.0)
EP=https://ftp.ebi.ac.uk/ensemblgenomes/pub/plants/release-63
SP=solanum_lycopersicum_gca000188115v5cm
PFX=Solanum_lycopersicum_gca000188115v5cm.SL4.0
fetch "$EP/fasta/$SP/dna/$PFX.dna.toplevel.fa.gz" "$DL/ensembl/$PFX.dna.toplevel.fa.gz"
check_sum "$DL/ensembl/$PFX.dna.toplevel.fa.gz" "49785 230112"
fetch "$EP/gtf/$SP/$PFX.63.gtf.gz" "$DL/ensembl/$PFX.63.gtf.gz"
check_sum "$DL/ensembl/$PFX.63.gtf.gz" "62729 6457"
