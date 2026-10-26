"""
Pilot: link all plantiSMASH 2.0 predicted BGCs (precalculated database, 430 genomes) to
PlantMetWiki genes and pathways, and collect the evidence needed to describe each link.

Evidence collected per BGC (the statements of the BGC use case in specification/SPECIFICATION.md):
  - there is a BGC                    plantiSMASH prediction (pHMM rules + genomic co-location)
  - detected by rule X                cluster `type` (e.g. "terpene", "saccharide-alkaloid") and core domains
  - from plantiSMASH version X        precalculated database v2 (plantiSMASH 2.0)
  - complete / partial MIBiG match    KnownClusterBLAST vs MIBiG 4.0: "% of genes show similarity"
  - X overlap with pathway nodes      BGC genes / enzyme functions shared with a PlantMetWiki pathway

BGC gene -> PlantMetWiki pathway, three tiers (strongest first):
  1. gene_direct   the BGC gene's TAIR locus is a gene of the pathway (A. thaliana only; = PlantMetWiki's
                   existing BGC-pathway links)
  2. gene_uniprot  the BGC protein (RefSeq/GenBank -> UniProt) is an enzyme of the pathway (any species)
  3. gene_ec       the BGC protein's EC number (UniProt) catalyses a reaction of the pathway (any species)
Tiers 2-3 use only genes that plantiSMASH marks as *biosynthetic*; tier 1 uses all genes of the BGC,
as in PlantMetWiki.

Usage:
  .venv/bin/python match_plantismash.py            # download (cached), map, write results/
"""

import gzip
import importlib.util
import io
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).parent
DATA = HERE / "data"
RESULTS = HERE / "results"
CACHE = DATA / "plantismash_v2"          # one compact json.gz per genome (gitignored)

# Reuse the PlantMetWiki snapshots (pathway ECs / UniProt ids / PC -> PlantCyc) of the MEANtools pilot,
# which in turn reuses the metabolite snapshots and pathway classes of the first pilot
PILOT2 = HERE.parent / "meantools_overlap" / "match_meantools.py"
_spec = importlib.util.spec_from_file_location("match_meantools", PILOT2)
mm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mm)
pmw_pilot = mm.pmw_pilot

PLANTISMASH = "https://plantismash.bioinformatics.nl/precalc/v2/"
PLANTISMASH_VERSION = "2.0 (precalculated database v2)"
SPARQL_ENDPOINT = mm.SPARQL_ENDPOINT

TAIR_GENE_QUERY = """
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT DISTINCT ?locus ?pc WHERE {
  ?gene a wp:GeneProduct ; dcterms:isPartOf ?pathway .
  FILTER(STRSTARTS(STR(?gene), "https://identifiers.org/tair.name/"))
  FILTER(STRSTARTS(STR(?pathway), "http://rdf-plantmetwiki.bioinformatics.nl/pathways/"))
  BIND(UCASE(STRAFTER(STR(?gene), "tair.name/")) AS ?locus)
  BIND(REPLACE(STR(?pathway), "^.*/pathways/(PC[0-9]+)_.*$", "$1") AS ?pc)
}"""

GENE_TIERS = {
    "gene_direct": "BGC gene (TAIR locus) is a gene of the PlantMetWiki pathway",
    "gene_uniprot": "BGC biosynthetic protein (RefSeq/GenBank -> UniProt) is an enzyme of the pathway",
    "gene_ec": "BGC biosynthetic protein's EC number catalyses a reaction of the pathway",
}
TAIR = re.compile(r"^AT[1-5CM]G\d{5}$", re.I)


# ----------------------------
# plantiSMASH database
# ----------------------------
def list_genomes():
    html = requests.get(PLANTISMASH, timeout=60).text
    return sorted(set(re.findall(r'href="/precalc/v2/([^"/]+)/"', html)))


def parse_known_cluster(text):
    """'thalianol/thaliandiol (66% of genes show similarity)' -> ('thalianol/thaliandiol', 66)."""
    m = re.match(r"^(.*) \((\d+)% of genes show similarity\)$", str(text))
    return (m.group(1), int(m.group(2))) if m else (None, None)


def fetch_genome(genome, session):
    """Download geneclusters.js for one genome and keep only what the analysis needs."""
    path = CACHE / f"{genome}.json.gz"
    if path.exists():
        return json.loads(gzip.decompress(path.read_bytes()))
    r = session.get(f"{PLANTISMASH}{genome}/geneclusters.js", timeout=300)
    r.raise_for_status()
    s = r.text
    clusters, _ = json.JSONDecoder().raw_decode(s[s.index("{"):])
    compact = []
    for cid, c in clusters.items():
        name, sim = parse_known_cluster(c.get("knowncluster", "-"))
        compact.append({
            "cluster": cid, "type": c.get("type"), "start": c.get("start"), "end": c.get("end"),
            "domains": c.get("domains", []), "substrates": c.get("substrates", []),
            "mibig_name": name, "mibig_similarity": sim,
            "mibig_id": None if c.get("BGCid", "-") == "-" else c["BGCid"].split(".")[0],
            "genes": [{"locus_tag": o.get("locus_tag"), "biosynthetic": o.get("type") == "biosynthetic",
                       "protein_id": (re.findall(r"Protein-ID: ([^<\s;]+)", o.get("description", "")) or [None])[0],
                       "domains": o.get("domains", [])} for o in c.get("orfs", [])],
        })
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(compact).encode()))
    return compact


def download_all(delay=0.5):
    """Fetch every genome once (cached). Returns the list of genomes that failed."""
    genomes = list_genomes()
    failed = []
    with requests.Session() as s:
        for i, g in enumerate(genomes):
            if (CACHE / f"{g}.json.gz").exists():
                continue
            try:
                fetch_genome(g, s)
            except Exception as e:  # keep going; report at the end
                failed.append((g, repr(e)[:120]))
            if i % 25 == 0:
                print(f"  {i}/{len(genomes)} genomes")
            time.sleep(delay)
    return genomes, failed


def load_plantismash():
    """Tables of all cached genomes: clusters (one row per BGC) and genes (one row per BGC gene)."""
    crow, grow = [], []
    for path in sorted(CACHE.glob("*.json.gz")):
        genome = path.name.removesuffix(".json.gz")
        m = re.match(r"^(.*)_(GC[AF]_\d+\.\d+)$", genome)
        species, assembly = (m.group(1).replace("_", " "), m.group(2)) if m else (genome, None)
        for c in json.loads(gzip.decompress(path.read_bytes())):
            bgc = f"{genome}/#{c['cluster']}"
            crow.append({"bgc": bgc, "genome": genome, "species": species, "assembly": assembly,
                         "type": c["type"], "n_genes": len(c["genes"]),
                         "n_biosynthetic": sum(g["biosynthetic"] for g in c["genes"]),
                         "core_domains": ", ".join(sorted({d.split("/")[-1] for d in c["domains"]})),
                         "mibig_id": c["mibig_id"], "mibig_name": c["mibig_name"],
                         "mibig_similarity": c["mibig_similarity"]})
            for g in c["genes"]:
                grow.append({"bgc": bgc, "species": species, "locus_tag": g["locus_tag"],
                             "protein_id": g["protein_id"], "biosynthetic": g["biosynthetic"]})
    clusters, genes = pd.DataFrame(crow), pd.DataFrame(grow)
    clusters["genus"] = clusters["species"].str.split().str[0]
    clusters["rules"] = clusters["type"].str.split("-")
    return clusters, genes


# ----------------------------
# Protein -> UniProt -> EC (UniProt ID mapping, cached)
# ----------------------------
ID_TYPES = {  # UniProt ID-mapping source database: pattern of the protein IDs plantiSMASH reports
    "RefSeq_Protein": r"^[NXY]P_\d+\.\d+$",
    "EMBL-GenBank-DDBJ_CDS": r"^[A-Z]{3}\d{5,}\.\d+$",
}


def _idmapping(ids, source):
    job = requests.post("https://rest.uniprot.org/idmapping/run",
                        data={"from": source, "to": "UniProtKB", "ids": ",".join(ids)}, timeout=300).json()["jobId"]
    while True:
        st = requests.get(f"https://rest.uniprot.org/idmapping/status/{job}", timeout=60, allow_redirects=False)
        if st.status_code in (302, 303) or st.json().get("jobStatus") == "FINISHED":
            break
        if st.json().get("jobStatus") in ("ERROR", "FAILED"):
            raise RuntimeError(st.text)
        time.sleep(5)
    r = requests.get(f"https://rest.uniprot.org/idmapping/uniprotkb/results/stream/{job}",
                     params={"fields": "accession,reviewed,ec", "format": "tsv"}, timeout=1800)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text), sep="\t", dtype=str)


def map_proteins_to_uniprot(protein_ids, batch=10_000):  # large jobs silently return partial results
    """BGC protein IDs (RefSeq or GenBank) -> UniProt accession + EC, via the UniProt ID-mapping service."""
    path = DATA / "protein_to_uniprot.tsv.gz"
    if path.exists():
        return pd.read_csv(path, sep="\t", dtype=str)
    ids = pd.Series(sorted({p for p in protein_ids if isinstance(p, str)}))
    parts = []
    for source, pattern in ID_TYPES.items():
        sel = ids[ids.str.match(pattern)].tolist()
        for i in range(0, len(sel), batch):
            chunk = sel[i:i + batch]
            print(f"UniProt ID mapping ({source}): {i + len(chunk)}/{len(sel)}")
            part = _idmapping(chunk, source).assign(id_type=source)
            print(f"   mapped {part["From"].nunique()} of {len(chunk)}")
            parts.append(part)
    out = pd.concat(parts, ignore_index=True).rename(
        columns={"From": "protein_id", "Entry": "uniprot", "Reviewed": "reviewed", "EC number": "ec"})
    out.to_csv(path, sep="\t", index=False, compression="gzip")
    return out


def protein_ec(mapping):
    ec = mapping.assign(ec=mapping["ec"].fillna("").str.split("; ")).explode("ec")
    return ec[ec["ec"].str.fullmatch(r"\d+\.\d+\.\d+\.\d+")][["protein_id", "uniprot", "ec"]].drop_duplicates()


# ----------------------------
# PlantMetWiki
# ----------------------------
def load_tair_pathways(pcs):
    path = DATA / "plantmetwiki_tair_gene_pathways.csv"
    if not path.exists():
        r = requests.get(SPARQL_ENDPOINT, params={"query": TAIR_GENE_QUERY}, headers={"Accept": "text/csv"}, timeout=300)
        r.raise_for_status()
        path.write_text(r.text)
    return pd.read_csv(path, dtype=str).merge(pcs, on="pc")


# ----------------------------
# Mapping
# ----------------------------
def bgc_gene_pathways(genes, uniprot_map, pmw_genes, tair_pw):
    """Long table: (bgc, gene) -> PlantMetWiki pathway, per tier, with the node that links them."""
    g = genes.copy()
    g["locus"] = g["locus_tag"].where(g["locus_tag"].fillna("").str.match(TAIR.pattern, case=False)).str.upper()
    direct = g.dropna(subset=["locus"]).merge(tair_pw, on="locus").assign(tier="gene_direct", via=lambda d: d["locus"])
    bio = g[g["biosynthetic"]].merge(uniprot_map[["protein_id", "uniprot"]].drop_duplicates(), on="protein_id")
    uni = bio.merge(pmw_genes["pathway_uniprot"], on="uniprot").assign(tier="gene_uniprot", via=lambda d: d["uniprot"])
    ec = g[g["biosynthetic"]].merge(protein_ec(uniprot_map), on="protein_id") \
        .merge(pmw_genes["pathway_ec"], on="ec").assign(tier="gene_ec", via=lambda d: "EC " + d["ec"])
    cols = ["bgc", "species", "locus_tag", "protein_id", "tier", "via", "plantcyc_id", "pathway"]
    return pd.concat([t[cols] for t in (direct, uni, ec)], ignore_index=True).drop_duplicates()


def bgc_pathway_links(links, pmw_genes, tair_pw):
    """One row per BGC x pathway: best tier and the overlap with the pathway's nodes."""
    rank = {t: i for i, t in enumerate(GENE_TIERS)}
    n_ec = pmw_genes["pathway_ec"].groupby("plantcyc_id")["ec"].nunique()
    n_genes = tair_pw.groupby("plantcyc_id")["locus"].nunique()
    out = links.assign(rank=links["tier"].map(rank)).groupby(["bgc", "species", "plantcyc_id", "pathway"]).agg(
        best_tier=("tier", lambda s: min(s, key=rank.__getitem__)),
        tiers=("tier", lambda s: ", ".join(t for t in GENE_TIERS if t in set(s))),
        n_bgc_genes=("locus_tag", "nunique"),
        n_direct_genes=("via", lambda s: s[links.loc[s.index, "tier"] == "gene_direct"].nunique()),
        n_ecs=("via", lambda s: s[links.loc[s.index, "tier"] == "gene_ec"].nunique()),
        linking_nodes=("via", lambda s: ", ".join(sorted(set(s)))),
    ).reset_index()
    out["pathway_n_ecs"] = out["plantcyc_id"].map(n_ec).fillna(0).astype(int)
    out["pathway_n_tair_genes"] = out["plantcyc_id"].map(n_genes).fillna(0).astype(int)
    out["ec_overlap"] = (out["n_ecs"] / out["pathway_n_ecs"].where(out["pathway_n_ecs"] > 0)).round(3)
    return out


def build():
    """Run the whole mapping and return all tables (used by the notebook)."""
    clusters, genes = load_plantismash()
    pmw_genes = mm.load_plantmetwiki_genes()
    tair_pw = load_tair_pathways(pmw_genes["pc_pathways"])
    uniprot_map = map_proteins_to_uniprot(genes.loc[genes["biosynthetic"], "protein_id"])
    links = bgc_gene_pathways(genes, uniprot_map, pmw_genes, tair_pw)
    bp = bgc_pathway_links(links, pmw_genes, tair_pw)
    classes = pmw_pilot.classify_pathways(pmw_pilot.load_pathway_classes())
    bp = bp.merge(classes[["category"]], left_on="plantcyc_id", right_index=True, how="left")
    bp = bp.merge(clusters[["bgc", "type", "mibig_id", "mibig_name", "mibig_similarity"]], on="bgc")
    bp = bp.merge(pmw_genes["pc_pathways"][["plantcyc_id", "pc"]].drop_duplicates("plantcyc_id"), on="plantcyc_id", how="left")
    return {"clusters": clusters, "genes": genes, "pmw_genes": pmw_genes, "tair_pw": tair_pw,
            "uniprot_map": uniprot_map, "links": links, "bgc_pathways": bp, "pathway_classes": classes}


# ----------------------------
# Evidence export (RDF, Turtle)
# ----------------------------
TTL_PREFIXES = """@prefix lodp: <https://example.org/lod-pathways/pilot/> .   # placeholder namespace
@prefix obo: <http://purl.obolibrary.org/obo/> .
@prefix sio: <http://semanticscience.org/resource/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix swo: <http://www.ebi.ac.uk/swo/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix pmw: <http://rdf-plantmetwiki.bioinformatics.nl/pathways/> .
"""


def iri_bgc(bgc):
    return "<" + PLANTISMASH + bgc.replace("/#", "/index.html#") + ">"


def to_turtle(clusters, bgc_pathways, path):
    """BGC evidence (prediction, rule, version, MIBiG match) and BGC-pathway overlap links."""
    run = "lodp:plantismash_v2_database"
    lines = [TTL_PREFIXES, f"""{run} a prov:Activity ;
    rdfs:label "plantiSMASH precalculated database" ;
    prov:used <{PLANTISMASH}> ;
    lodp:software "plantiSMASH" ; swo:SWO_0004000 "{PLANTISMASH_VERSION}" .   # has version
"""]
    for _, c in clusters[clusters["bgc"].isin(bgc_pathways["bgc"])].iterrows():
        ev = ["a obo:ECO_0000256 , obo:ECO_0007327",  # pHMM rule hits ; genomic co-location
              f"prov:wasGeneratedBy {run}",
              "lodp:detectionRule " + " , ".join(f'"{r}"' for r in c["rules"])]
        if c["core_domains"]:
            ev.append("lodp:coreDomain " + " , ".join(f'"{d}"' for d in c["core_domains"].split(", ")))
        block = [f"{iri_bgc(c['bgc'])} a obo:SO_0002357 ;   # biosynthetic_gene_cluster",
                 f"    rdfs:label \"{c['bgc']}\" ;",
                 "    sio:SIO_000772 [ " + " ;\n        ".join(ev) + " ]"]
        if pd.notna(c["mibig_id"]) and pd.notna(c["mibig_similarity"]):   # NaN is truthy in pandas
            rel = "skos:exactMatch" if c["mibig_similarity"] == 100 else "skos:closeMatch"
            block[-1] += " ;"
            block.append(f"    {rel} <https://mibig.secondarymetabolites.org/repository/{c['mibig_id']}> ;")
            block.append(f"    lodp:mibigMatchEvidence [ a obo:ECO_0000249 ;   # sequence similarity (KnownClusterBLAST)")
            block.append(f"        lodp:percentGenesSimilar \"{int(c['mibig_similarity'])}\"^^xsd:integer ]")
        lines.append("\n".join(block) + " .\n")
    for _, r in bgc_pathways.iterrows():
        aid = re.sub(r"[^A-Za-z0-9_]", "_", f"{r['bgc']}_{r['plantcyc_id']}")
        pathway = f"pmw:{r['pc']}"
        ev = ["a obo:ECO_0007679",   # combinatorial computational evidence, automatic assertion
              f"prov:wasGeneratedBy {run}",
              f'lodp:linkTier "{r["best_tier"]}"']
        for node in sorted(set(r["linking_nodes"].split(", "))):
            if TAIR.match(node):
                ev.append(f'lodp:linkingGene "{node}"')
            elif node.startswith("EC "):
                ev.append(f'lodp:linkingEC "{node[3:]}"')
            else:
                ev.append(f'lodp:linkingProtein "{node}"')
        ev.append(f'lodp:nSharedGenes "{int(r["n_bgc_genes"])}"^^xsd:integer')
        if r["n_direct_genes"] and r["pathway_n_tair_genes"]:
            ev.append(f'lodp:nPathwayGenes "{int(r["pathway_n_tair_genes"])}"^^xsd:integer')
            ev.append(f'lodp:fractionPathwayGenes "{r["n_direct_genes"] / r["pathway_n_tair_genes"]:.3f}"^^xsd:double')
        if r["n_ecs"]:
            ev.append(f'lodp:nSharedEC "{int(r["n_ecs"])}"^^xsd:integer')
            ev.append(f'lodp:fractionPathwayECs "{r["ec_overlap"]}"^^xsd:double')
        evidence = " ;\n        ".join(ev)
        lines.append(f"""lodp:link_{aid} a lodp:BGCPathwayLink ;
    obo:RO_0002131 {iri_bgc(r['bgc'])} , {pathway} ;   # overlaps
    lodp:anchoredInPathway {pathway} ;
    sio:SIO_000772 [ {evidence} ] .
""")
    Path(path).write_text("\n".join(lines))


def main():
    RESULTS.mkdir(exist_ok=True)
    genomes, failed = download_all()
    print(f"{len(genomes)} genomes listed; {len(failed)} failed: {failed[:5]}")
    res = build()
    res["bgc_pathways"].to_csv(RESULTS / "bgc_pathway_links.csv.gz", index=False, compression="gzip")
    res["clusters"].drop(columns="rules").to_csv(RESULTS / "plantismash_clusters.csv.gz", index=False, compression="gzip")
    strong = res["bgc_pathways"][res["bgc_pathways"]["best_tier"] != "gene_ec"]
    to_turtle(res["clusters"], strong, RESULTS / "bgc_evidence.ttl")
    print(f"{res['bgc_pathways']['bgc'].nunique()} BGCs linked to {res['bgc_pathways']['plantcyc_id'].nunique()} "
          f"pathways; {len(strong)} direct/UniProt links written to results/bgc_evidence.ttl")


if __name__ == "__main__":
    main()
