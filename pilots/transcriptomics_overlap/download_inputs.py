"""Download the inputs of the transcriptomics pilot into data/downloads/ (ignored by git) and check their MD5.

Files already present with the right MD5 are not downloaded again. ATTED-II and Zenodo publish MD5
checksums; Expression Atlas and Ensembl Plants do not, so their MD5s below were recorded on the first
download (2026-11-10): a mismatch means the source changed since then.

Not downloaded here: the E-MTAB-11876 reads and the Ensembl Plants genome for the nf-core route
(about 6 GB; see nfcore/download_inputs.sh and README.md).

Usage (from this folder): .venv/bin/python download_inputs.py
"""
import hashlib
import os
import shutil
import sys
import urllib.request
from pathlib import Path

DL = Path(os.environ.get("TX_PILOT_DOWNLOADS", Path(__file__).resolve().parent / "data/downloads")).resolve()

ATLAS = "https://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/E-MTAB-11876"
ENSEMBL = ("https://ftp.ensemblgenomes.ebi.ac.uk/pub/plants/release-63/tsv/solanum_lycopersicum_gca000188115v5cm/"
           "Solanum_lycopersicum_gca000188115v5cm.SL4.0.63.entrez.tsv.gz")

# (path under data/downloads, URL, MD5)
FILES = [
    # Expression Atlas E-MTAB-11876: tomato hairy roots, jasmonate vs none (differential expression)
    ("E-MTAB-11876/E-MTAB-11876-raw-counts.tsv", f"{ATLAS}/E-MTAB-11876-raw-counts.tsv", "0a84fc4bf53d78cc18de48139bacb3f8"),
    ("E-MTAB-11876/E-MTAB-11876-analytics.tsv", f"{ATLAS}/E-MTAB-11876-analytics.tsv", "729a9e040bd0dbab7952946c360140d2"),
    ("E-MTAB-11876/E-MTAB-11876-configuration.xml", f"{ATLAS}/E-MTAB-11876-configuration.xml", "60eccf3f99b7744547867a46207f3ab7"),
    ("E-MTAB-11876/E-MTAB-11876.condensed-sdrf.tsv", f"{ATLAS}/E-MTAB-11876.condensed-sdrf.tsv", "4f04de3139f92b06619d86f2b9164072"),
    ("E-MTAB-11876/E-MTAB-11876-analysis-methods.tsv", f"{ATLAS}/E-MTAB-11876-analysis-methods.tsv", "99e67e434f3ff5fc37498b56224403c7"),
    # MEANtools case study (Zenodo 15697913, v3.0.0): tomato leaves, RPKM (response profile, co-expression)
    ("meantools/rnaseq.rpkm.csv", "https://zenodo.org/records/15697913/files/rnaseq.rpkm.csv?download=1",
     "1c89784ac92eaab2cbb23c6540876868"),
    # ATTED-II v13.0 Sly-r.c6-0: 1,608 tomato RNA-seq runs, log2 ComBat (co-expression), 88 MB
    ("atted/Sly-r.c6-0.expression.combat.txt.zip", "https://atted.jp/download/Sly-r.c6-0/exp/Sly-r.c6-0.expression.combat.txt.zip",
     "27aad1f33531d36b24ad3930553d267a"),
    # Ensembl Plants release 63, tomato SL4.0: Solyc <-> NCBI Gene ID (for the ATTED-II gene IDs)
    ("ensembl/Solanum_lycopersicum_gca000188115v5cm.SL4.0.63.entrez.tsv.gz", ENSEMBL, "77430fc6d0d1d47bcc1c953ba5cf91b9"),
]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(rel, url, expected):
    dest = DL / rel
    if dest.exists() and md5(dest) == expected:
        print(f"present  {rel}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"download {rel}")
    part = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=300) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f)
    part.replace(dest)
    got = md5(dest)
    if got != expected:
        print(f"MD5 MISMATCH {rel}: got {got}, expected {expected}", file=sys.stderr)
        return False
    print(f"md5 ok   {rel}")
    return True


def main():
    ok = all([fetch(*f) for f in FILES])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
