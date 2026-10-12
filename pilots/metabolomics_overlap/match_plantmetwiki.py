# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas==3.0.6", "rdkit==2026.3.6", "requests==2.34.2"]
# ///
"""
Pilot: how many metabolites annotated in the Brassicaceae LC-MS/MS dataset
(Wolters et al. 2026, Zenodo 10.5281/zenodo.19391098, file S6) are present
as metabolites in PlantMetWiki?

Matching is done on the first InChIKey block (connectivity only), so
stereochemistry and protonation/charge differences are ignored. PlantMetWiki
often stores charged forms (e.g. carboxylates), while MS tools predict
neutral structures.

Every structure prediction for a feature gets an evidence tier (strongest first):
  1. gnps_library     spectral library match in GNPS (MSI level 2-like)
  2. consensus_inchi  >= 2 of SIRIUS / MS2Query / DreaMS agree on the structure
  3. sirius           SIRIUS CSI:FingerID top hit
  4. ms2query_exact   MS2Query hit with precursor m/z difference <= 0.01 Da
  5. dreams           DreaMS top hit
  6. ms2query_analog  MS2Query analogue (different mass: related, NOT the same compound)

Usage (writes results/*.csv; explore them in explore_results.ipynb):
  uv run --python 3.12 match_plantmetwiki.py
"""

import glob
import io
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

HERE = Path(__file__).parent
DATA = HERE / "data"
RESULTS = HERE / "results"

ZENODO_S6 = "https://zenodo.org/records/19391098/files/S6_Annotation_tables_and_annotated_FBMNs.zip?download=1"
ZENODO_S6_MD5 = "ef234f42d2db0d52d1e851237bed4d5c"  # from the Zenodo record, version 1.0
SPARQL_ENDPOINT = "https://plantmetwiki.bioinformatics.nl/sparql"
SPARQL_QUERY = """
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?inchikey (SAMPLE(?label) AS ?name) (SAMPLE(?wd) AS ?wikidata) (COUNT(DISTINCT ?pw) AS ?n_pathways) WHERE {
  ?m a wp:Metabolite ; wp:bdbInChIKey ?ik .
  BIND(REPLACE(STR(?ik), "^.*/", "") AS ?inchikey)
  OPTIONAL { ?m rdfs:label ?label }
  OPTIONAL { ?m wp:bdbWikidata ?wd }
  OPTIONAL { ?m <http://purl.org/dc/terms/isPartOf> ?pw . ?pw a wp:Pathway }
} GROUP BY ?inchikey
"""

PATHWAY_QUERY = """
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT DISTINCT ?inchikey ?plantcyc_id ?pathway WHERE {
  ?m a wp:Metabolite ; wp:bdbInChIKey ?ik ; dcterms:isPartOf ?pw .
  ?pw a wp:Pathway ; <http://rdf-plantmetwiki.bioinformatics.nl/vocab/plantcycId> ?plantcyc_id ; dc:title ?pathway .
  BIND(REPLACE(STR(?ik), "^.*/", "") AS ?inchikey)
  FILTER(STRSTARTS(?inchikey, "%s"))
}
"""

# PlantCyc pathway classes are stored as GPML properties "Type", "Type_1", "Type_2", ... (most specific class only)
PATHWAY_CLASS_QUERY = """
PREFIX v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>
SELECT DISTINCT ?plantcyc_id ?class WHERE {
  ?pw a <http://vocabularies.wikipathways.org/wp#Pathway> ; v:plantcycId ?plantcyc_id ; v:gpmlProperty ?b .
  ?b v:key ?k ; v:value ?class .
  FILTER(REGEX(?k, "^Type(_[0-9]+)?$"))
}
"""
# Curated mapping of those classes to primary / specialized / hormones / ... (edit to refine)
CLASS_CATEGORIES = DATA / "pathway_class_categories.csv"

TIER_DESCRIPTIONS = {
    "gnps_library": "GNPS spectral library match",
    "consensus_inchi": ">= 2 of SIRIUS / MS2Query / DreaMS agree on the structure",
    "sirius": "SIRIUS CSI:FingerID top hit",
    "ms2query_exact": f"MS2Query hit with precursor m/z difference <= 0.01 Da",
    "dreams": "DreaMS top hit",
    "ms2query_analog": "MS2Query analogue (different mass: related, NOT the same compound)",
}
TIERS = list(TIER_DESCRIPTIONS)
# Tiers that claim the feature *is* the compound (analogues excluded)
DETECTION_TIERS = TIERS[:-1]
MS2QUERY_EXACT_TOL = 0.01  # Da


# ----------------------------
# Inputs
# ----------------------------
def load_plantmetwiki():
    path = DATA / "plantmetwiki_metabolites.csv"
    if not path.exists():
        print("Querying PlantMetWiki SPARQL endpoint...")
        r = requests.get(SPARQL_ENDPOINT, params={"query": SPARQL_QUERY}, headers={"Accept": "text/csv"}, timeout=300)
        r.raise_for_status()
        path.write_text(r.text)
    pmw = pd.read_csv(path, dtype=str)
    pmw["key14"] = pmw["inchikey"].str[:14]
    pmw["n_pathways"] = pmw["n_pathways"].astype(int)
    # Collapse stereo/charge variants onto the connectivity block
    agg = pmw.groupby("key14").agg(
        pmw_names=("name", lambda s: " | ".join(sorted(set(s.dropna())))),
        pmw_inchikeys=("inchikey", lambda s: " | ".join(sorted(set(s)))),
        wikidata=("wikidata", lambda s: " | ".join(sorted(set(s.dropna())))),
        n_pathways=("n_pathways", "max"),
    )
    return pmw, agg


def load_pathways():
    """Metabolite -> PlantCyc pathway membership. The endpoint caps results at
    10,000 rows (also when paging with OFFSET), so query per InChIKey first letter."""
    path = DATA / "plantmetwiki_metabolite_pathways.csv"
    if not path.exists():
        print("Querying PlantMetWiki pathway membership...")
        parts = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            r = requests.get(SPARQL_ENDPOINT, params={"query": PATHWAY_QUERY % letter},
                             headers={"Accept": "text/csv"}, timeout=300)
            r.raise_for_status()
            parts.append(pd.read_csv(io.StringIO(r.text), dtype=str))
        pd.concat(parts, ignore_index=True).to_csv(path, index=False)
    pw = pd.read_csv(path, dtype=str)
    pw["key14"] = pw["inchikey"].str[:14]
    # PlantMetWiki also types single-reaction diagrams (e.g. ADENPHOSPHOR-RXN) as wp:Pathway;
    # keep only the 1,162 PlantCyc pathways
    pw = pw[~pw["plantcyc_id"].str.contains("RXN")]
    return pw.drop_duplicates(["key14", "plantcyc_id"])


def load_pathway_classes():
    """PlantCyc pathway -> most specific class(es) from PlantMetWiki."""
    path = DATA / "plantmetwiki_pathway_classes.csv"
    if not path.exists():
        print("Querying PlantMetWiki pathway classes...")
        r = requests.get(SPARQL_ENDPOINT, params={"query": PATHWAY_CLASS_QUERY},
                         headers={"Accept": "text/csv"}, timeout=300)
        r.raise_for_status()
        path.write_text(r.text)
    return pd.read_csv(path, dtype=str)


# Priority when a pathway has classes in several categories
CATEGORY_PRIORITY = ["specialized (secondary)", "hormones", "primary", "super-pathway / cluster", "unclassified"]


def classify_pathways(classes):
    """One metabolism category per PlantCyc pathway.

    PlantMetWiki only keeps the most specific class, and the MetaCyc class hierarchy is not
    openly queryable (BioCyc requires an account), so classes are mapped with the curated
    table data/pathway_class_categories.csv. It follows the MetaCyc hierarchy: classes under
    'Secondary Metabolite Biosynthesis' (incl. carotenoids and lignin) are specialized."""
    mapping = pd.read_csv(CLASS_CATEGORIES, dtype=str).set_index("class")["category"]
    unknown = set(classes["class"]) - set(mapping.index)
    if unknown:
        print(f"Warning: {len(unknown)} classes missing from {CLASS_CATEGORIES.name}, treated as unclassified: {sorted(unknown)}")
    rank = {c: i for i, c in enumerate(CATEGORY_PRIORITY)}
    out = classes.groupby("plantcyc_id")["class"].agg(list).to_frame("classes")
    out["category"] = out["classes"].map(
        lambda cl: min((mapping.get(c, "unclassified") for c in cl), key=rank.__getitem__))
    out["classes"] = out["classes"].map(", ".join)
    return out


def ensure_nodetables():
    """Download S6 from Zenodo (once), verify its MD5 checksum and extract the two node tables."""
    import hashlib
    import zipfile

    zip_path = DATA / "S6.zip"
    if not glob.glob(str(DATA / "S6_*" / "*nodetable.csv")):
        if not zip_path.exists():
            print("Downloading S6 from Zenodo (~45 MB)...")
            with requests.get(ZENODO_S6, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
        md5 = hashlib.md5(zip_path.read_bytes()).hexdigest()
        if md5 != ZENODO_S6_MD5:
            sys.exit(f"Checksum mismatch for {zip_path}: {md5} != {ZENODO_S6_MD5}. Delete it and retry.")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(DATA, members=[n for n in z.namelist() if n.endswith("nodetable.csv")])
    return sorted(glob.glob(str(DATA / "S6_*" / "*nodetable.csv")))


def load_nodetables():
    tables = {}
    for f in ensure_nodetables():
        mode = "neg" if "_neg_" in os.path.basename(f) else "pos"
        tables[mode] = pd.read_csv(f, dtype=str, low_memory=False)
    return tables


def snapshot_info():
    """Provenance of every input file (for the reproducibility cell in the notebook)."""
    import datetime
    import hashlib

    rows = []
    for f in sorted(DATA.glob("plantmetwiki_*.csv")) + [CLASS_CATEGORIES] + sorted(DATA.glob("S6_*/*nodetable.csv")):
        rows.append({
            "file": str(f.relative_to(HERE)),
            "size_MB": round(f.stat().st_size / 1e6, 2),
            "md5": hashlib.md5(f.read_bytes()).hexdigest(),
            "last_modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return pd.DataFrame(rows).set_index("file")


# ----------------------------
# Structure keys
# ----------------------------
_inchi_cache = {}


def inchi_to_key14(inchi):
    if not isinstance(inchi, str) or inchi.strip() in ("", "none", "N/A"):
        return None
    inchi = inchi.strip()
    if not inchi.startswith("InChI="):
        inchi = "InChI=" + inchi  # GNPS library_InChI lacks the prefix
    if inchi not in _inchi_cache:
        try:
            key = Chem.InchiToInchiKey(inchi)
        except Exception:
            key = None
        _inchi_cache[inchi] = key[:14] if key else None
    return _inchi_cache[inchi]


def clean_key(k):
    if not isinstance(k, str) or len(k.strip()) < 14:
        return None
    return k.strip()[:14]


def feature_keys(df):
    """One column of 14-char InChIKey blocks per evidence tier."""
    out = pd.DataFrame({"feature_id": df["shared name"]})
    out["gnps_library"] = df["library_InChI"].map(inchi_to_key14)
    out["consensus_inchi"] = df["match_value_inchi"].map(inchi_to_key14)
    out["sirius"] = df["sirius_InChIkey2D"].map(clean_key)
    ms2q = df["ms2query_inchikey"].map(clean_key)
    diff = pd.to_numeric(df["ms2query_precursor_mz_difference"], errors="coerce").abs()
    exact = diff <= MS2QUERY_EXACT_TOL
    out["ms2query_exact"] = ms2q.where(exact)
    out["ms2query_analog"] = ms2q.where(~exact)
    out["dreams"] = df["dreams_InChI"].map(inchi_to_key14)
    return out


def species_per_feature(df):
    cols = [c for c in df.columns if c.startswith("ATTRIBUTE_GROUP_SPECIES:GNPSGROUP:")]
    pres = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0) > 0
    names = [c.split(":")[-1].replace("_", " ").capitalize() for c in cols]
    return pres.apply(lambda row: ", ".join(n for n, p in zip(names, row) if p), axis=1)


# ----------------------------
# Main
# ----------------------------
def build():
    """Run the matching and return all tables as a dict (used by the notebook)."""
    pmw_raw, pmw = load_plantmetwiki()
    pathways = load_pathways()
    tables = load_nodetables()

    # Long table: one row per (mode, feature, tier) where the tier has a prediction
    rows = []
    for mode, df in tables.items():
        keys = feature_keys(df)
        keys["species"] = species_per_feature(df).values
        keys["mode"] = mode
        rows.append(keys.melt(id_vars=["mode", "feature_id", "species"], value_vars=TIERS,
                              var_name="tier", value_name="key14").dropna(subset=["key14"]))
    long = pd.concat(rows, ignore_index=True)
    long["in_plantmetwiki"] = long["key14"].isin(set(pmw.index))
    long["tier_rank"] = long["tier"].map({t: i for i, t in enumerate(TIERS)})

    hits = long[long["in_plantmetwiki"]].join(pmw, on="key14")

    # Per PlantMetWiki metabolite: best evidence and where it was seen (analogues excluded)
    det = hits[hits["tier"].isin(DETECTION_TIERS)]
    per_met = det.sort_values("tier_rank").groupby("key14").agg(
        best_tier=("tier", "first"),
        tiers=("tier", lambda s: ", ".join(t for t in TIERS if t in set(s))),
        n_features=("feature_id", lambda s: s.nunique()),
        modes=("mode", lambda s: ", ".join(sorted(set(s)))),
        species=("species", lambda s: ", ".join(sorted({x for v in s for x in v.split(", ") if x}))),
    ).join(pmw)
    per_met["best_tier"] = pd.Categorical(per_met["best_tier"], categories=TIERS, ordered=True)
    per_met = per_met.sort_values(["best_tier", "n_pathways"], ascending=[True, False])

    # Pathway categories (primary / specialized / ...) and per-metabolite metabolism class
    pathway_classes = classify_pathways(load_pathway_classes())
    pathways = pathways.join(pathway_classes, on="plantcyc_id")
    pathways["category"] = pathways["category"].fillna("unclassified")
    metabolite_class = metabolite_metabolism_class(pathways)
    per_met = per_met.join(metabolite_class)

    return {"pmw_raw": pmw_raw, "pmw": pmw, "pathways": pathways, "tables": tables,
            "long": long, "hits": hits, "per_met": per_met,
            "pathway_classes": pathway_classes, "metabolite_class": metabolite_class}


def metabolite_metabolism_class(pathways):
    """Classify each PlantMetWiki metabolite by the categories of the pathways it occurs in.
    Super-pathways/clusters are ignored (they only regroup other pathways); hormones count as specialized."""
    pw = pathways[pathways["category"].isin(["primary", "specialized (secondary)", "hormones"])]
    cats = pw.assign(is_spec=pw["category"] != "primary").groupby("key14")["is_spec"].agg(["any", "all"])
    label = pd.Series("primary only", index=cats.index)
    label[cats["all"]] = "specialized only"
    label[cats["any"] & ~cats["all"]] = "primary + specialized"
    return label.to_frame("metabolism_class")


def main():
    RESULTS.mkdir(exist_ok=True)
    res = build()
    res["hits"].sort_values(["mode", "feature_id", "tier_rank"]).drop(columns="tier_rank") \
        .to_csv(RESULTS / "feature_hits.csv", index=False)
    res["per_met"].to_csv(RESULTS / "matched_plantmetwiki_metabolites.csv")
    print(f"Matched {len(res['per_met'])} PlantMetWiki metabolites. "
          f"Explore the results in explore_results.ipynb; CSVs written to {RESULTS}/")


if __name__ == "__main__":
    main()
