#!/usr/bin/env python3
"""
Pilot: ipecac alkaloid biosynthesis (Colinas et al.) vs PlantMetWiki.

Data: Zenodo 10.5281/zenodo.23661892 (metabolite SMILES, and Pearson co-expression tables of two de novo transcriptomes:
Carapichea ipecacuanha "Ci" and Alangium salviifolium "As").

Four outputs in results/:
  metabolite_matches.csv      the 12 metabolites of the paper against PlantMetWiki: match level, pathways
  pathway_steps_PWY-7135.csv  the steps of PlantMetWiki's "emetine biosynthesis" with the enzymes it already lists,
                              and which metabolites of the paper are the substrates and products
  coexpression_selected_*.csv transcripts co-expressed with the bait gene, with the author's cut-offs
  coexpression_summary.csv    sizes of the tables, the bait, and how many transcripts chance alone would put above the cut-off
  gene_class_summary.csv      what the co-expressed transcripts are (family-level, from the eggNOG description)

  python match_ipecac.py            # uses the committed PlantMetWiki snapshots in data/
  python match_ipecac.py --refresh  # queries the live SPARQL endpoint again
"""

import argparse
import datetime
import hashlib
import io
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from rdkit import Chem, RDLogger
from rdkit.Chem.rdMolDescriptors import CalcMolFormula
from scipy import stats

RDLogger.DisableLog("rdApp.*")
HERE = Path(__file__).parent
DATA, RESULTS = HERE / "data", HERE / "results"
ZENODO = "https://zenodo.org/api/records/23661892/files"
FILES = {  # name -> MD5 listed by Zenodo
    "smiles.xlsx": "8b56c7ee2c66ea05382501b848317045",
    "Ci_transcriptome_pearson.xlsx": "12c1a621cb7da66432edda517efee3e3",
    "As_transcriptome_pearson.xlsx": "c867a1b402917fd0da7536ef0e244b0a",
}
ENDPOINT = "https://plantmetwiki.bioinformatics.nl/sparql"
PREFIXES = """PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>
"""
PATHWAY_ID = "PWY-7135"          # PlantCyc "emetine biosynthesis"

# the author's cut-offs (personal communication, see the README): Pearson >= 0.75 with the bait, and an expression of at
# least 50 in the tissue in which the genes are most highly expressed (leaf buds for Alangium, young leaf for Carapichea)
PEARSON_MIN, EXPR_MIN = 0.75, 50
SETS = {  # short name -> (file, description column, tissue of the expression cut-off)
    "Ci": ("Ci_transcriptome_pearson.xlsx", "eggNOGmapper description", "YL"),
    "As": ("As_transcriptome_pearson.xlsx", "eggnogmapper description", "As_LB"),
}
# family-level classes, searched in the eggNOG description (case-insensitive). These are hypotheses about what a
# transcript might do, not annotations of a function.
CLASSES = {
    "SAM-dependent methyltransferase": r"methyltransferase",
    "cytochrome P450": r"cytochrome p450",
    "decarboxylase": r"decarboxylase",
    "glycoside hydrolase (beta-glucosidase)": r"glycosyl hydrolase|glucosidase|glycoside hydrolase",
    "strictosidine synthase-like": r"strictosidine|pictet|norcoclaurine",
    "2-oxoglutarate-dependent oxygenase": r"2og|2-oxoglutarate|dioxygenase",
    "reductase / dehydrogenase": r"reductase|dehydrogenase",
    "acyltransferase (BAHD)": r"bahd|acyltransferase",
    "transporter (MATE, ABC, NPF)": r"multi antimicrobial extrusion|mate\b|abc transporter|nitrate/peptide|transporter",
}


# ------------------------------------------------------------------------------------------------- inputs
def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_inputs():
    DATA.mkdir(exist_ok=True)
    for name, md5 in FILES.items():
        path = DATA / name
        if not path.exists():
            print(f"downloading {name} from Zenodo", file=sys.stderr)
            r = requests.get(f"{ZENODO}/{name}/content", timeout=600)
            r.raise_for_status()
            path.write_bytes(r.content)
        if md5_of(path) != md5:
            sys.exit(f"{name}: MD5 does not match the one listed by Zenodo; delete the file and run again")


def read_table(name):
    cache = DATA / (name.replace(".xlsx", "") + ".pkl")      # reading the 24 MB workbook takes a minute
    if cache.exists():
        return pd.read_pickle(cache)
    df = pd.read_excel(DATA / name)
    df.to_pickle(cache)
    return df


# ------------------------------------------------------------------------------------------------- PlantMetWiki
def sparql(query):
    r = requests.post(ENDPOINT, data={"query": query}, headers={"Accept": "text/csv"}, timeout=240)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def snapshot(name, query_fn, refresh):
    path = DATA / name
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = query_fn()
    df.to_csv(path, index=False)
    (DATA / "SNAPSHOT_INFO.txt").write_text(f"endpoint: {ENDPOINT}\ndate: {datetime.date.today()}\n")
    return df


def metabolites_from_smiles():
    s = pd.read_excel(DATA / "smiles.xlsx").rename(columns={"Unnamed: 0": "name", "Pubchem": "pubchem", "Smiles": "smiles"})
    rows = []
    for r in s.itertuples():
        mol = Chem.MolFromSmiles(r.smiles)
        rows.append({"name": r.name, "pubchem": r.pubchem, "formula": CalcMolFormula(mol), "inchikey": Chem.MolToInchiKey(mol)})
    return pd.DataFrame(rows)


def q_nodes(blocks):
    pattern = "|".join(blocks)
    return sparql(PREFIXES + f"""SELECT ?node ?label WHERE {{ ?node a wp:Metabolite ; dc:source "InChIKey" .
      OPTIONAL {{ ?node rdfs:label ?label }} FILTER(REGEX(STR(?node), "inchikey/({pattern})")) }}""")


def q_pathways(nodes):
    vals = " ".join(f"<{n}>" for n in nodes)
    return sparql(PREFIXES + f"""SELECT DISTINCT ?node ?pid ?title WHERE {{ VALUES ?node {{ {vals} }}
      ?node dcterms:isPartOf ?pw . ?pw a wp:Pathway ; v:plantcycId ?pid ; dc:title ?title }}""")


def q_steps():
    return sparql(PREFIXES + f"""SELECT DISTINCT ?conv ?src ?srcLabel ?tgt ?tgtLabel ?enzyme ?enzLabel WHERE {{
      ?pw a wp:Pathway ; v:plantcycId "{PATHWAY_ID}" .
      ?conv dcterms:isPartOf ?pw ; a wp:Conversion ; wp:source ?src ; wp:target ?tgt .
      ?src rdfs:label ?srcLabel . ?tgt rdfs:label ?tgtLabel .
      OPTIONAL {{ ?cat a wp:Catalysis ; wp:target ?conv ; wp:source ?enzyme . OPTIONAL {{ ?enzyme rdfs:label ?enzLabel }} }}
      FILTER(?src != ?tgt) }}""")


def key_blocks(k):
    return k.split("-") if isinstance(k, str) else [None, None, None]


def match_level(paper_key, pmw_key):
    a, b = key_blocks(paper_key), key_blocks(pmw_key)
    if a[0] != b[0]:
        return "none"
    if a[1] != b[1]:
        return "connectivity"
    if a[2] != b[2]:
        return "stereo (protonation differs)"
    return "full"


LEVEL_RANK = {"none": 0, "connectivity": 1, "stereo (protonation differs)": 2, "full": 3}


def metabolite_matches(refresh):
    mets = metabolites_from_smiles()
    nodes = snapshot("plantmetwiki_ipecac_nodes.csv", lambda: q_nodes(sorted(set(mets.inchikey.str[:14]))), refresh)
    nodes["key"] = nodes.node.str.rsplit("/", n=1).str[-1]
    pws = snapshot("plantmetwiki_ipecac_pathways.csv", lambda: q_pathways(list(nodes.node)), refresh)
    pws["key"] = pws.node.str.rsplit("/", n=1).str[-1]
    out = []
    for m in mets.itertuples():
        cand = nodes[nodes.key.str[:14] == m.inchikey[:14]]
        best = max(((match_level(m.inchikey, k), k, l) for k, l in zip(cand.key, cand.label)), key=lambda t: LEVEL_RANK[t[0]], default=("none", "", ""))
        mine = pws[pws.key == best[1]] if best[1] else pws.iloc[0:0]
        out.append({"name": m.name, "pubchem": m.pubchem, "formula": m.formula, "inchikey": m.inchikey, "match_level": best[0],
                    "plantmetwiki_key": best[1], "plantmetwiki_label": best[2],
                    "pathways": "; ".join(f"{p} {t}" for p, t in sorted(set(zip(mine.pid, mine.title)))),
                    "in_" + PATHWAY_ID: PATHWAY_ID in set(mine.pid)})
    return pd.DataFrame(out)


def uniprot_info(accessions, refresh):
    path = DATA / "uniprot_pwy7135_enzymes.tsv"
    if path.exists() and not refresh:
        return pd.read_csv(path, sep="\t")
    r = requests.get("https://rest.uniprot.org/uniprotkb/accessions",
                     params={"accessions": ",".join(sorted(accessions)), "format": "tsv", "fields": "accession,protein_name,gene_names,organism_name,ec"}, timeout=120)
    r.raise_for_status()
    path.write_text(r.text)
    return pd.read_csv(path, sep="\t")


def pathway_steps(matches, refresh):
    st = snapshot(f"plantmetwiki_{PATHWAY_ID}_steps.csv", q_steps, refresh)
    key = lambda iri: iri.rsplit("/", 1)[-1]   # noqa: E731
    paper = {}
    for r in matches.itertuples():
        if r.plantmetwiki_key:
            paper.setdefault(r.plantmetwiki_key, []).append(f"{r.name} [{r.match_level.split(' ')[0]}]")
    accs = {key(e) for e in st.enzyme.dropna() if "/uniprot/" in e}
    info = uniprot_info(accs, refresh).set_index("Entry") if accs else pd.DataFrame()
    rows = []
    for conv, g in st.groupby("conv"):
        r = g.iloc[0]
        enz = sorted(set(g.enzyme.dropna()))
        uni = [key(e) for e in enz if "/uniprot/" in e]
        names = "; ".join(f"{a}: {info.loc[a, 'Protein names'][:45]} ({info.loc[a, 'Organism'].split(' (')[0]})" for a in uni if a in info.index)
        status = "UniProt-linked" if uni else ("PlantCyc monomer only (no sequence)" if enz else "no enzyme listed")
        rows.append({"substrate": r.srcLabel, "product": r.tgtLabel,
                     "substrate_in_paper": "; ".join(paper.get(key(r.src), [])), "product_in_paper": "; ".join(paper.get(key(r.tgt), [])),
                     "enzyme_status": status, "enzymes_uniprot": names or "; ".join(key(e) for e in enz)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------- genes
def coexpression(name):
    file, desc, tissue_cut = SETS[name]
    d = read_table(file)
    tissues = [c for c in d.columns if c not in ("Pearson", "Name", "Length", desc)]
    bait = d[np.isclose(d.Pearson, 1.0)].iloc[0]
    # the reported Pearson values are reproduced from the expression columns (raw values, the bait row as reference)
    b = bait[tissues].astype(float).values
    x = d[tissues].astype(float).values
    with np.errstate(all="ignore"):
        rc = np.array([np.corrcoef(r, b)[0, 1] if np.std(r) > 0 else np.nan for r in x])
    ok = ~np.isnan(rc) & d.Pearson.notna().values
    max_diff = float(np.max(np.abs(rc[ok] - d.Pearson.values[ok])))
    k = len(tissues)
    sel = d[(d.Pearson >= PEARSON_MIN) & (d[tissue_cut] >= EXPR_MIN)].copy()
    r = sel.Pearson.clip(upper=0.999999)
    sel["p_value_derived"] = 2 * stats.t.sf(r * np.sqrt((k - 2) / (1 - r * r)), k - 2)   # two-sided, n = number of tissues
    sel = sel.rename(columns={desc: "description"})
    sel["description"] = sel.description.fillna("none")
    sel["max_expression"] = sel[tissues].max(axis=1)
    sel["peak_tissue"] = sel[tissues].idxmax(axis=1)
    return d, desc, tissues, bait, max_diff, sel.sort_values("Pearson", ascending=False)


def class_summary(name, d, desc, sel):
    background = d[desc].fillna("").astype(str)
    background = background[~background.isin(["", "none", "-"])]
    chosen = sel.description[~sel.description.isin(["none", "-"])]
    rows = []
    for cls, pat in CLASSES.items():
        a = int(chosen.str.contains(pat, case=False, regex=True).sum())
        b = int(background.str.contains(pat, case=False, regex=True).sum())
        odds, p = stats.fisher_exact([[a, len(chosen) - a], [b - a, len(background) - len(chosen) - (b - a)]], alternative="greater")
        rows.append({"transcriptome": name, "class": cls, "co_expressed": a, "annotated_co_expressed": len(chosen),
                     "all_annotated": len(background), "in_all": b,
                     "fold_enrichment": round((a / max(len(chosen), 1)) / (b / len(background)), 2) if b else np.nan, "fisher_p_greater": p})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="query the PlantMetWiki SPARQL endpoint again")
    args = ap.parse_args(argv)
    fetch_inputs()
    RESULTS.mkdir(exist_ok=True)

    matches = metabolite_matches(args.refresh)
    matches.to_csv(RESULTS / "metabolite_matches.csv", index=False)
    print("== metabolites of the paper vs PlantMetWiki")
    print(matches[["name", "match_level", "plantmetwiki_label", "in_" + PATHWAY_ID]].to_string(index=False))
    print(matches.match_level.value_counts().to_string())

    steps = pathway_steps(matches, args.refresh)
    steps.to_csv(RESULTS / f"pathway_steps_{PATHWAY_ID}.csv", index=False)
    print(f"\n== steps of {PATHWAY_ID} in PlantMetWiki")
    print(steps.to_string(index=False, max_colwidth=60))

    summary, sizes = [], []
    for name in SETS:
        d, desc, tissues, bait, max_diff, sel = coexpression(name)
        sel.drop(columns=[]).to_csv(RESULTS / f"coexpression_selected_{name}.csv", index=False)
        print(f"\n== {name}: {len(d)} transcripts, {len(tissues)} tissues; bait {bait.Name} ({str(bait[desc])[:50]}); "
              f"Pearson recomputed from the table: max difference {max_diff:.2e}")
        print(f"   selected (Pearson >= {PEARSON_MIN}, expression >= {EXPR_MIN}): {len(sel)}; derived p at r = {PEARSON_MIN}: "
              f"{2 * stats.t.sf(PEARSON_MIN * np.sqrt((len(tissues) - 2) / (1 - PEARSON_MIN ** 2)), len(tissues) - 2):.3f}")
        summary += class_summary(name, d, desc, sel)
        k = len(tissues)
        p_null = stats.t.sf(PEARSON_MIN * np.sqrt((k - 2) / (1 - PEARSON_MIN ** 2)), k - 2)   # P(r >= cut-off) for unrelated profiles, normal data
        n_ok = int(d.Pearson.notna().sum())
        sizes.append({"transcriptome": name, "transcripts": len(d), "with_pearson": n_ok, "tissues": k, "bait": bait.Name,
                      "bait_description": str(bait[desc]), "pearson_ge_cutoff": int((d.Pearson >= PEARSON_MIN).sum()),
                      "expected_by_chance_normal_null": round(n_ok * p_null), "after_expression_cutoff": len(sel),
                      "p_value_at_cutoff_two_sided": round(2 * p_null, 4)})
    pd.DataFrame(sizes).to_csv(RESULTS / "coexpression_summary.csv", index=False)
    print("\n== sizes"); print(pd.DataFrame(sizes).drop(columns=["bait_description"]).to_string(index=False))
    cls = pd.DataFrame(summary)
    p = cls.fisher_p_greater.values            # Benjamini-Hochberg over all tests of both transcriptomes
    order = np.argsort(p)
    adj = np.empty_like(p)
    adj[order] = np.minimum.accumulate((p[order] * len(p) / (np.arange(len(p)) + 1))[::-1])[::-1].clip(max=1)
    cls["fdr_bh"] = adj
    cls.to_csv(RESULTS / "gene_class_summary.csv", index=False)
    print("\n== classes among the co-expressed transcripts")
    print(cls[["transcriptome", "class", "co_expressed", "in_all", "fold_enrichment", "fisher_p_greater", "fdr_bh"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
