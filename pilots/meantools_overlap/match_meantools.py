"""
Pilot: how much of the MEANtools tomato case study (paired transcriptomics + metabolomics,
Jeon et al. 2020; MEANtools, Singh et al.) can be mapped to PlantMetWiki?

MEANtools correlates metabolite features with gene transcripts (Pearson r), turns mutual ranks (MR)
into edge weights exp(-(MR-1)/DR) for several decay rates (DR), and groups genes and metabolites
into functional clusters with ClusterONE. Here we map both sides of each gene-metabolite pair in a
functional cluster to PlantMetWiki and ask whether they meet in the same PlantCyc pathway.

Gene -> PlantMetWiki pathway, three tiers (strongest first):
  1. gene_locus    the Solyc locus is itself a gene in the pathway (SGN IDs / synonyms in PlantMetWiki)
  2. gene_uniprot  the gene's UniProt protein is an enzyme in the pathway
  3. gene_ec       the gene's EC number (UniProt) catalyses a reaction in the pathway
Metabolite feature -> PlantMetWiki pathway:
  mass_match       the feature m/z matches a PlantMetWiki metabolite of the pathway as a common
                   positive-mode adduct within MASS_PPM (MS1 mass only: weak, often ambiguous)
                   (MEANtools' own NPDB_annotations table is not used: its rows are not mass-consistent,
                   see the notebook)

Usage (writes results/*.csv and results/associations.ttl; explore them in explore_results.ipynb):
  .venv/bin/python match_meantools.py
"""

import hashlib
import importlib.util
import io
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).parent
DATA = HERE / "data"
RESULTS = HERE / "results"

# Reuse the PlantMetWiki metabolite snapshots, structure matching and pathway classes of the first pilot
PILOT1 = HERE.parent / "metabolomics_overlap" / "match_plantmetwiki.py"
_spec = importlib.util.spec_from_file_location("match_plantmetwiki", PILOT1)
pmw_pilot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pmw_pilot)

ZENODO_RECORD = "https://zenodo.org/records/15697913"
MEANTOOLS_DATASETS = {
    # name: (file, md5 from the Zenodo record v3.0.0, table prefix)
    "fungal": ("Jeon_fungal.sqlite", "b5080825a727b99c660a4a5437ec596d", "Jeon_fungal_correlations"),
    "bacterial": ("Jeon_bacterial.sqlite", "3421dc196693370d6fd3ee3fa88a4b2d", "Jeon_bacterial_correlations"),  # 2.6 GB
}
DECAY_RATES = [5, 10, 25, 50]

# XCMS feature table of the same experiment (exact m/z and RT per feature), pinned to a commit
FEATURE_TABLE = ("https://raw.githubusercontent.com/sattely-lab/falcarindiol_pathway_metabolomics/"
                 "7a7e0f692c1f15048ce54a96bd9d27d056b5bedd/metabolite_induction_analysis_with_rtmed_mzmed.csv")
FEATURE_TABLE_MD5 = "39ba472fe131d7b56874fa65a8c6c9f6"

# MetaboLights MTBLS1039 was acquired in positive ion mode
MASS_PPM = 10
ADDUCTS = {  # name: m/z = neutral mass + delta
    "[M+H]+": 1.007276,
    "[M+Na]+": 22.989218,
    "[M+NH4]+": 18.033823,
    "[M+K]+": 38.963158,
    "[M+H-H2O]+": 1.007276 - 18.010565,
}

UNIPROT_TOMATO = ("https://rest.uniprot.org/uniprotkb/stream?query=organism_id:4081"
                  "&fields=accession,reviewed,protein_name,ec,xref_ensemblplants&format=tsv&compressed=true")

SPARQL_ENDPOINT = pmw_pilot.SPARQL_ENDPOINT
PREFIXES = """
PREFIX v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
"""
# PlantMetWiki has two layers: wp:Pathway (with the PlantCyc id) and the GPML drawing (reactions with EC
# numbers, enzyme nodes with UniProt ids, gene nodes with SGN loci). Both carry the same PC number.
QUERIES = {
    "plantmetwiki_pc_pathways.csv": PREFIXES + """
SELECT DISTINCT ?pc ?plantcyc_id ?pathway WHERE {
  ?pw a <http://vocabularies.wikipathways.org/wp#Pathway> ; v:plantcycId ?plantcyc_id ; dc:identifier ?id ; dc:title ?pathway .
  BIND(REPLACE(STR(?id), "^.*/", "") AS ?pc)
}""",
    "plantmetwiki_pathway_ec.csv": PREFIXES + """
SELECT DISTINCT ?pc ?ec WHERE {
  ?i dcterms:isPartOf ?gp ; v:gpmlProperty ?b . ?b v:key ?k ; v:value ?val .
  FILTER(STRSTARTS(?k, "EC_Number"))
  BIND(REPLACE(STR(?val), "^EC-", "") AS ?ec)
  BIND(REPLACE(STR(?gp), "^.*/Pathway/(PC[0-9]+)_.*$", "$1") AS ?pc)
}""",
    "plantmetwiki_pathway_uniprot.csv": PREFIXES + """
SELECT DISTINCT ?pc ?uniprot WHERE {
  ?n dcterms:isPartOf ?gp ; v:gpmlProperty ?b . ?b v:key "AlternativeId_Uniprot" ; v:value ?uniprot .
  BIND(REPLACE(STR(?gp), "^.*/Pathway/(PC[0-9]+)_.*$", "$1") AS ?pc)
}""",
    "plantmetwiki_metabolite_inchi.csv": PREFIXES + """
SELECT DISTINCT ?inchikey ?inchi WHERE {
  ?n v:gpmlProperty ?b1 , ?b2 . ?b1 v:key "InchiKey" ; v:value ?ik . ?b2 v:key "Inchi" ; v:value ?inchi .
  BIND(REPLACE(STR(?ik), "^InChIKey=", "") AS ?inchikey)
}""",
    "plantmetwiki_pathway_solyc.csv": PREFIXES + """
SELECT DISTINCT ?pc ?locus ?gene_label WHERE {
  ?n dcterms:isPartOf ?gp ; v:gpmlProperty ?b . ?b v:value ?val .
  FILTER(REGEX(STR(?val), "^Solyc[0-9]+g[0-9]+", "i"))
  BIND(CONCAT("Solyc", SUBSTR(STR(?val), 6, 9)) AS ?locus)
  OPTIONAL { ?n <http://vocabularies.wikipathways.org/gpml#textlabel> ?gene_label }
  BIND(REPLACE(STR(?gp), "^.*/Pathway/(PC[0-9]+)_.*$", "$1") AS ?pc)
}""",
}

GENE_TIERS = {
    "gene_locus": "Solyc locus listed as a gene of the PlantMetWiki pathway",
    "gene_uniprot": "gene's UniProt protein is an enzyme of the pathway",
    "gene_ec": "gene's EC number (UniProt) catalyses a reaction of the pathway",
}
LOCUS = r"(Solyc\d{2}g\d{6})"


# ----------------------------
# Inputs
# ----------------------------
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_meantools(dataset):
    """Download the MEANtools SQLite output from Zenodo (once) and verify its MD5 checksum."""
    fname, checksum, _ = MEANTOOLS_DATASETS[dataset]
    path = DATA / fname
    if not path.exists():
        print(f"Downloading {fname} from Zenodo...")
        with requests.get(f"{ZENODO_RECORD}/files/{fname}?download=1", stream=True, timeout=1200) as r:
            r.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
    if md5(path) != checksum:
        sys.exit(f"Checksum mismatch for {path}. Delete it and retry.")
    return path


def load_meantools(dataset, decay_rate):
    path = ensure_meantools(dataset)
    prefix = MEANTOOLS_DATASETS[dataset][2]
    with sqlite3.connect(path) as con:
        corr = pd.read_sql(f"SELECT * FROM {prefix}", con)
        weights = pd.read_sql(f"SELECT * FROM {prefix}_MR_weights_DR_{decay_rate}", con)
        clusters = pd.read_sql(f'SELECT * FROM "{prefix}_clone_DR_{decay_rate}"', con)
        npdb = pd.read_sql("SELECT * FROM NPDB_annotations", con)
    return corr, weights, clusters, npdb


def cluster_summary(dataset):
    """One row per decay rate: how many clusters, how many significant, how many genes/metabolites."""
    path = ensure_meantools(dataset)
    prefix = MEANTOOLS_DATASETS[dataset][2]
    rows = []
    with sqlite3.connect(path) as con:
        for dr in DECAY_RATES:
            cl = pd.read_sql(f'SELECT * FROM "{prefix}_clone_DR_{dr}"', con)
            members = cl["Members"].str.split().explode()
            is_gene = members.str.match(LOCUS)
            rows.append({"decay_rate": dr, "clusters": len(cl),
                         "clusters_P<0.05": int((cl["P-value"] < 0.05).sum()),
                         "median_size": cl["Size"].median(),
                         "genes": members[is_gene].nunique(), "metabolites": members[~is_gene].nunique()})
    return pd.DataFrame(rows).set_index("decay_rate")


def load_feature_table():
    """Exact m/z and retention time of every XCMS feature (Sattely lab, pinned commit)."""
    path = DATA / "xcms_feature_table.csv"
    if not path.exists():
        print("Downloading the XCMS feature table...")
        r = requests.get(FEATURE_TABLE, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    if md5(path) != FEATURE_TABLE_MD5:
        sys.exit(f"Checksum mismatch for {path}. Delete it and retry.")
    ft = pd.read_csv(path, usecols=[0, 1, 2])
    ft.columns = ["feature", "mz", "rt"]
    return ft


def neutral_mass_from_inchi(inchi):
    """Monoisotopic mass of the neutral parent. The InChI formula layer describes the neutral form
    (protons removed/added are in the /p layer), so charged PlantMetWiki entries get their neutral mass."""
    import re
    from rdkit import Chem

    m = re.match(r"InChI=1S?/([^/]+)", str(inchi))
    if not m or "." in m.group(1) or m.group(1)[0].isdigit():
        return None  # skip salts / multi-component entries
    pt = Chem.GetPeriodicTable()
    try:
        return sum(pt.GetMostCommonIsotopeMass(el) * int(n or 1)
                   for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", m.group(1)))
    except RuntimeError:
        return None


def load_uniprot():
    """Tomato UniProt entries -> Solyc locus, accession, complete EC numbers."""
    path = DATA / "uniprot_tomato.tsv.gz"
    if not path.exists():
        print("Downloading tomato UniProt entries...")
        r = requests.get(UNIPROT_TOMATO, timeout=600)
        r.raise_for_status()
        path.write_bytes(r.content)
    up = pd.read_csv(path, sep="\t", dtype=str, compression="gzip")
    up["locus"] = up["EnsemblPlants"].fillna("").str.findall(LOCUS)
    up = up.explode("locus").dropna(subset=["locus"])
    up["ec"] = up["EC number"].fillna("").str.split("; ")
    up = up.explode("ec")
    up.loc[~up["ec"].fillna("").str.fullmatch(r"\d+\.\d+\.\d+\.\d+"), "ec"] = None  # drop partial ECs like 2.1.1.-
    return up.rename(columns={"Entry": "uniprot", "Protein names": "protein_name", "Reviewed": "reviewed"})[
        ["locus", "uniprot", "reviewed", "protein_name", "ec"]]


def load_plantmetwiki_genes():
    """PlantMetWiki snapshots: PC number -> PlantCyc pathway, and pathway ECs / UniProt ids / Solyc loci."""
    out = {}
    for fname, query in QUERIES.items():
        path = DATA / fname
        if not path.exists():
            print(f"Querying PlantMetWiki: {fname}")
            r = requests.get(SPARQL_ENDPOINT, params={"query": query}, headers={"Accept": "text/csv"}, timeout=300)
            r.raise_for_status()
            path.write_text(r.text)
        out[fname.removeprefix("plantmetwiki_").removesuffix(".csv")] = pd.read_csv(path, dtype=str)
    pcs = out.pop("pc_pathways")
    pcs = pcs[~pcs["plantcyc_id"].str.contains("RXN")]  # keep the 1,162 PlantCyc pathways (as in pilot 1)
    for k in ["pathway_ec", "pathway_uniprot", "pathway_solyc"]:
        out[k] = out[k].merge(pcs, on="pc")
    out["pathway_ec"] = out["pathway_ec"][out["pathway_ec"]["ec"].str.fullmatch(r"\d+\.\d+\.\d+\.\d+")]
    out["pc_pathways"] = pcs
    return out


def snapshot_info(dataset="fungal"):
    import datetime

    files = sorted(DATA.glob("plantmetwiki_*.csv")) + [DATA / "uniprot_tomato.tsv.gz", DATA / "xcms_feature_table.csv",
                                                       DATA / MEANTOOLS_DATASETS[dataset][0]]
    files += sorted((PILOT1.parent / "data").glob("plantmetwiki_*.csv")) + [pmw_pilot.CLASS_CATEGORIES]
    return pd.DataFrame([{
        "file": str(f.relative_to(HERE.parent)),
        "size_MB": round(f.stat().st_size / 1e6, 2),
        "md5": md5(f),
        "last_modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
    } for f in files]).set_index("file")


# ----------------------------
# Mapping
# ----------------------------
def gene_pathways(genes, uniprot, pmw_genes):
    """Long table: locus -> PlantMetWiki pathway, per gene tier."""
    genes = pd.DataFrame({"locus": sorted(genes)})
    up = uniprot[uniprot["locus"].isin(genes["locus"])]
    parts = [
        genes.merge(pmw_genes["pathway_solyc"], on="locus").assign(tier="gene_locus", via=lambda d: d["gene_label"]),
        up.merge(pmw_genes["pathway_uniprot"], on="uniprot").assign(tier="gene_uniprot", via=lambda d: d["uniprot"]),
        up.dropna(subset=["ec"]).merge(pmw_genes["pathway_ec"], on="ec").assign(tier="gene_ec", via=lambda d: "EC " + d["ec"]),
    ]
    cols = ["locus", "tier", "plantcyc_id", "pathway", "via"]
    return pd.concat([p[cols] for p in parts], ignore_index=True).drop_duplicates()


def metabolite_pathways(features, pmw, pmw_inchi, pmw_met_pathways, ppm=MASS_PPM):
    """Long table: feature -> PlantMetWiki metabolite (MS1 mass match, any listed adduct) -> pathway."""
    import numpy as np

    mets = pmw_inchi.assign(key14=pmw_inchi["inchikey"].str[:14])
    mets = mets[mets["key14"].isin(pmw.index)].copy()
    mets["neutral_mass"] = mets["inchi"].map(neutral_mass_from_inchi)
    mets = mets.dropna(subset=["neutral_mass"]).drop_duplicates("key14")
    rows = []
    for adduct, delta in ADDUCTS.items():
        neutral = features["mz"].values - delta
        tol = features["mz"].values * ppm / 1e6
        i, j = np.where(np.abs(neutral[:, None] - mets["neutral_mass"].values[None, :]) <= tol[:, None])
        rows.append(pd.DataFrame({"feature": features["feature"].values[i], "mz": features["mz"].values[i],
                                  "adduct": adduct, "key14": mets["key14"].values[j],
                                  "neutral_mass": mets["neutral_mass"].values[j]}))
    cand = pd.concat(rows, ignore_index=True)
    cand["ppm_error"] = (1e6 * (cand["mz"] - cand["adduct"].map(ADDUCTS) - cand["neutral_mass"]) / cand["mz"]).round(2)
    cand = cand.join(pmw[["pmw_names"]], on="key14")
    hits = cand.merge(pmw_met_pathways[["key14", "plantcyc_id", "pathway"]], on="key14")
    return cand, hits


def cluster_pairs(clusters, corr, weights):
    """All gene x metabolite pairs within each functional cluster, with correlation, MR and cluster stats."""
    cl = clusters.rename(columns={"P-value": "cluster_P", "Internal weight": "internal_weight",
                                  "External weight": "external_weight"})
    members = cl.assign(member=cl["Members"].str.split()).explode("member")
    members["is_gene"] = members["member"].str.match(LOCUS)
    genes = members[members["is_gene"]].rename(columns={"member": "gene"})
    mets = members[~members["is_gene"]][["Cluster", "member"]].rename(columns={"member": "metabolite"})
    pairs = genes.merge(mets, on="Cluster")[["Cluster", "Size", "Density", "Quality", "cluster_P", "gene", "metabolite"]]
    pairs = pairs.merge(corr, on=["metabolite", "gene"], how="left").merge(weights, on=["metabolite", "gene"], how="left")
    pairs["locus"] = pairs["gene"].str.extract(LOCUS)[0]
    return pairs


def classify_pairs(pairs, gmap, mmap):
    """Do gene and metabolite of a pair share a PlantMetWiki pathway? Keep the strongest gene tier."""
    rank = {t: i for i, t in enumerate(GENE_TIERS)}
    g = gmap[["locus", "tier", "plantcyc_id"]].drop_duplicates()
    m = mmap[["feature", "plantcyc_id"]].drop_duplicates().rename(columns={"feature": "metabolite"})
    shared = pairs[["Cluster", "locus", "metabolite"]].drop_duplicates() \
        .merge(g, on="locus").merge(m, on=["metabolite", "plantcyc_id"])
    shared["rank"] = shared["tier"].map(rank)
    best = shared.sort_values("rank").groupby(["Cluster", "locus", "metabolite"]).agg(
        support_tier=("tier", "first"),
        shared_pathways=("plantcyc_id", lambda s: ", ".join(sorted(set(s)))),
        n_shared_pathways=("plantcyc_id", "nunique"),
    ).reset_index()
    out = pairs.merge(best, on=["Cluster", "locus", "metabolite"], how="left")
    g_ok, m_ok = out["locus"].isin(gmap["locus"]), out["metabolite"].isin(mmap["feature"])
    out["mapping"] = "neither mapped"
    out.loc[g_ok & ~m_ok, "mapping"] = "gene only"
    out.loc[~g_ok & m_ok, "mapping"] = "metabolite only"
    out.loc[g_ok & m_ok, "mapping"] = "both mapped, no shared pathway"
    out.loc[out["support_tier"].notna(), "mapping"] = "both mapped, shared pathway"
    return out, shared


def expected_shared_fraction(pairs, gmap, mmap):
    """Background: among ALL combinations of mapped genes x mapped metabolites (not only those in the
    same cluster), what fraction shares a PlantMetWiki pathway? Deterministic, so reproducible."""
    genes = set(pairs["locus"]) & set(gmap["locus"])
    mets = set(pairs["metabolite"]) & set(mmap["feature"])
    g = gmap[gmap["locus"].isin(genes)][["locus", "plantcyc_id"]].drop_duplicates()
    m = mmap[mmap["feature"].isin(mets)][["feature", "plantcyc_id"]].drop_duplicates()
    n_shared = g.merge(m, on="plantcyc_id")[["locus", "feature"]].drop_duplicates().shape[0]
    return n_shared, len(genes) * len(mets)


# ----------------------------
# Build
# ----------------------------
def build(dataset="fungal", decay_rate=10):
    """Run the whole mapping and return all tables as a dict (used by the notebook)."""
    corr, weights, clusters, npdb = load_meantools(dataset, decay_rate)
    uniprot = load_uniprot()
    pmw_genes = load_plantmetwiki_genes()
    pmw_raw, pmw = pmw_pilot.load_plantmetwiki()
    pmw_met_pathways = pmw_pilot.load_pathways()
    pathway_classes = pmw_pilot.classify_pathways(pmw_pilot.load_pathway_classes())

    pairs = cluster_pairs(clusters, corr, weights)
    gmap = gene_pathways(set(pairs["locus"]), uniprot, pmw_genes)
    features = load_feature_table()
    features = features[features["feature"].isin(pairs["metabolite"])]
    candidates, mmap = metabolite_pathways(features, pmw, pmw_genes["metabolite_inchi"], pmw_met_pathways)
    pairs, shared = classify_pairs(pairs, gmap, mmap)
    category = pathway_classes["category"].to_dict()
    pairs["shared_pathway_categories"] = pairs["shared_pathways"].map(
        lambda s: ", ".join(sorted({category.get(p, "unclassified") for p in s.split(", ")})) if isinstance(s, str) else None)

    return {"dataset": dataset, "decay_rate": decay_rate, "corr": corr, "weights": weights, "clusters": clusters,
            "npdb": npdb, "features": features, "uniprot": uniprot, "pmw_genes": pmw_genes, "pmw": pmw, "pmw_met_pathways": pmw_met_pathways,
            "pathway_classes": pathway_classes, "pairs": pairs, "gmap": gmap, "candidates": candidates,
            "mmap": mmap, "shared": shared}


# ----------------------------
# Evidence export (RDF, Turtle)
# ----------------------------
TTL_PREFIXES = """@prefix lodp: <https://example.org/lod-pathways/pilot/> .   # placeholder namespace
@prefix sio: <http://semanticscience.org/resource/> .
@prefix obo: <http://purl.obolibrary.org/obo/> .
@prefix edam: <http://edamontology.org/> .
@prefix swo: <http://www.ebi.ac.uk/swo/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


def to_turtle(pairs, dataset, decay_rate, path):
    """One sio:chemical-gene association per gene-metabolite pair, with its MEANtools evidence and,
    when present, the PlantMetWiki pathway(s) that support it. Placeholder namespace for local nodes."""
    run = f"lodp:meantools_run_{dataset}_DR{decay_rate}"
    lines = [TTL_PREFIXES, f"""{run} a edam:operation_3463 , edam:operation_3432 ;   # expression correlation analysis ; clustering
    rdfs:label "MEANtools functional clustering, {dataset} treatment, decay rate {decay_rate}" ;
    prov:used <{ZENODO_RECORD}> ;
    lodp:software "MEANtools" ; swo:SWO_0004000 "1.0.0" ;   # has version
    lodp:decayRate {decay_rate} .
"""]
    for _, r in pairs.iterrows():
        aid = f"{dataset}_DR{decay_rate}_C{r['Cluster']}_{r['locus']}_{r['metabolite']}"
        gene = f"<https://plants.ensembl.org/Solanum_lycopersicum/Gene/Summary?g={r['locus']}>"
        met = f"lodp:feature_MTBLS1039_{r['metabolite']}"
        ev = [f"a obo:ECO_0007590",  # high throughput expression pattern evidence used in automatic assertion
              f"prov:wasGeneratedBy {run}",
              f"lodp:functionalCluster \"{r['Cluster']}\"",
              f"lodp:clusterPValue \"{r['cluster_P']}\"^^xsd:double"]
        if pd.notna(r.get("correlation")):
            ev += [f"obo:STATO_0000280 \"{r['correlation']:.4f}\"^^xsd:double",  # Pearson's r
                   f"obo:OBI_0000175 \"{r['P']:.3g}\"^^xsd:double"]              # p-value
        if pd.notna(r.get("MR")):
            ev += [f"lodp:mutualRank \"{r['MR']:.3f}\"^^xsd:double",
                   f"lodp:edgeWeight \"{r['weight']:.4f}\"^^xsd:double"]
        block = [f"lodp:assoc_{aid} a sio:SIO_001257 ;   # chemical-gene association",
                 f"    sio:SIO_000628 {gene} , {met} ;   # refers to",
                 "    sio:SIO_000772 [ " + " ;\n        ".join(ev) + " ]"]
        if pd.notna(r.get("support_tier")):
            pws = " , ".join(f"<https://identifiers.org/plantcyc/{p}>" for p in r["shared_pathways"].split(", "))
            block[-1] += " ;"
            block.append(f"    lodp:supportedByPlantMetWikiPathway {pws} ;")
            block.append(f"    lodp:geneMappingTier \"{r['support_tier']}\"")
        lines.append("\n".join(block) + " .\n")
    Path(path).write_text("\n".join(lines))


def main():
    RESULTS.mkdir(exist_ok=True)
    res = build()
    pairs = res["pairs"]
    pairs.to_csv(RESULTS / "cluster_pairs.csv", index=False)
    res["gmap"].to_csv(RESULTS / "gene_pathway_map.csv", index=False)
    res["mmap"].to_csv(RESULTS / "metabolite_pathway_map.csv", index=False)
    export = pairs[(pairs["mapping"] == "both mapped, shared pathway") | (pairs["cluster_P"] < 0.05)]
    to_turtle(export, res["dataset"], res["decay_rate"], RESULTS / "associations.ttl")
    print(f"{len(pairs)} gene-metabolite pairs; {(pairs['mapping'] == 'both mapped, shared pathway').sum()} share a "
          f"PlantMetWiki pathway. {len(export)} associations written to results/associations.ttl")


if __name__ == "__main__":
    main()
