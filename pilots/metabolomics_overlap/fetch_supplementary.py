#!/usr/bin/env python3
"""
Download the supplementary files S1-S6 of the Brassicaceae metabolic fingerprinting dataset
(Zenodo record 19391098, DOI 10.5281/zenodo.19391098) into data/supplementary/ and check their MD5 sums.

  python fetch_supplementary.py              # all files (about 480 MB; S3 alone is 385 MB)
  python fetch_supplementary.py S1 S2 S5     # only these
  python fetch_supplementary.py --extract    # also unzip each archive into data/supplementary/extracted/<S#>/

An interrupted download is resumed on the next run (HTTP range request). A file whose MD5 sum matches is not
downloaded again. The folder is ignored by git; see data/supplementary/README.md for what each file holds.
"""

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

import requests

RECORD = "https://zenodo.org/api/records/19391098"
OUT = Path(__file__).parent / "data" / "supplementary"


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(name, url, size, md5, attempts=20):
    dest = OUT / name
    for attempt in range(1, attempts + 1):
        have = dest.stat().st_size if dest.exists() else 0
        if have == size:
            break
        if have > size:
            dest.unlink()
            have = 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        print(f"{name}: downloading {size / 1e6:.1f} MB" + (f" (resuming at {have / 1e6:.1f} MB)" if have else ""), flush=True)
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                if r.status_code not in (200, 206):
                    print(f"  failed: HTTP {r.status_code}", file=sys.stderr)
                    return False
                with open(dest, "ab" if (have and r.status_code == 206) else "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
        except requests.exceptions.RequestException as exc:   # Zenodo drops slow long transfers: resume
            print(f"  interrupted ({type(exc).__name__}), attempt {attempt} of {attempts}", flush=True)
    ok = dest.exists() and dest.stat().st_size == size and md5_of(dest) == md5
    print(f"  MD5 {'ok' if ok else 'MISMATCH or incomplete, run again'}")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*", help="file prefixes to fetch, e.g. S1 S2 (default: all)")
    ap.add_argument("--extract", action="store_true", help="unzip archives into data/supplementary/extracted/")
    args = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    meta = requests.get(RECORD, timeout=60).json()
    files = [(f["key"], f["links"]["self"], f["size"], f["checksum"].split(":", 1)[1]) for f in meta["files"]]
    ok = True
    for name, url, size, md5 in sorted(files):
        if args.only and not any(name.startswith(p) for p in args.only):
            continue
        good = fetch(name, url, size, md5)
        ok &= good
        if good and args.extract and name.endswith(".zip"):
            target = OUT / "extracted" / name.split("_", 1)[0]
            target.mkdir(parents=True, exist_ok=True)
            zipfile.ZipFile(OUT / name).extractall(target)
            print(f"  extracted to {target.relative_to(OUT.parent.parent)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
