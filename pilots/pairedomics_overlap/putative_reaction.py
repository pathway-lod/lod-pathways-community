"""Putative reaction (ghost edge) for the THT example: from a gene-pathway link and an orphan feature to a new reaction in the pathway.

Steps (the three of the discussion):
 1. Template: read the reactions of the pathway with the EC of the gene (PlantMetWiki, live, resolved by PlantCyc id) and get the
    substrate/product pattern  acyl-CoA + tyramine => amide + CoA.
 2. Mass link: which pathway product differs from the feature (neutral mass of its [M+H]+) by a known group?
 3. Write the reaction by analogy (acid = amide - tyramine + H2O, then acyl-CoA), balance it by elemental formula, check the adduct and
    ask Rhea whether the reaction exists. A null shows how often step 3's mass inference finds *some* PlantMetWiki compound by chance.

Run:  python putative_reaction.py       (needs internet; writes results/putative_reaction_tht.json)
"""
import json, re, sqlite3, sys
from pathlib import Path
import numpy as np, pandas as pd, requests
from rdkit import Chem
from rdkit.Chem.Descriptors import ExactMolWt
from rdkit.Chem.rdMolDescriptors import CalcMolFormula

HERE = Path(__file__).parent
DATA, RES = HERE / "data", HERE / "results"
PMW, RHEA = "https://plantmetwiki.bioinformatics.nl/sparql", "https://sparql.rhea-db.org/sparql"
PLANTCYC, FEATURE, EC = "PWY-5474", "M300T887", "2.3.1.110"
H = 1.007276
MASS = {"C": 12.0, "H": 1.00782503, "N": 14.00307401, "O": 15.99491462, "P": 30.97376199, "S": 31.97207117}
COA = {"C": 21, "H": 36, "N": 7, "O": 16, "P": 3, "S": 1}            # coenzyme A (free thiol)
TYRAMINE = "NCCc1ccc(O)cc1"
CAFFEOYLTYRAMINE = "O=C(/C=C/c1ccc(O)c(O)c1)NCCc1ccc(O)cc1"          # hypothesis (hand-written)
CAFFEIC_ACID = "OC(=O)/C=C/c1ccc(O)c(O)c1"


def sparql(ep, q):
    r = requests.get(ep, params={"query": q}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
    r.raise_for_status()
    return [{k: v["value"] for k, v in b.items()} for b in r.json()["results"]["bindings"]]


def formula_counts(smiles):
    m = Chem.AddHs(Chem.MolFromSmiles(smiles)); c = {}
    for a in m.GetAtoms():
        c[a.GetSymbol()] = c.get(a.GetSymbol(), 0) + 1
    return c


def add(*ds, sign=1):
    out = {}
    for d in ds:
        for k, v in d.items():
            out[k] = out.get(k, 0) + sign * v
    return out


def mass(c):
    return sum(MASS[k] * v for k, v in c.items())


def ppm(a, b):
    return (a - b) / b * 1e6


def main():
    out = {}
    # 1. template from the pathway
    iri = sparql(PMW, f'SELECT ?pw WHERE {{ ?pw <http://xmlns.com/foaf/0.1/page> <https://pmn.plantcyc.org/pathway?orgid=PLANT&id={PLANTCYC}> }}')[0]["pw"]
    pc = re.search(r"/(PC\d+)_", iri).group(1)
    rows = sparql(PMW, f'''PREFIX v: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>
PREFIX gpml: <http://vocabularies.wikipathways.org/gpml#>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT ?e ?val WHERE {{ ?e a gpml:Interaction ; dcterms:isPartOf ?gp ; v:gpmlProperty ?b . FILTER(REGEX(STR(?gp), "/Pathway/{pc}_")) FILTER(!CONTAINS(STR(?e), "regulation"))
  ?b v:key "ReactionEquation" ; v:value ?val }}''')
    tht = [r["val"] for r in rows if "TYRAMINE" in r["val"] and "CO-A" in r["val"]]
    donors = sorted({m for v in tht for m in re.findall(r"([A-Z-]+-COA)\b", v) if m != "CO-A"})
    out["pathway"] = {"plantcyc": PLANTCYC, "pc": pc, "thT_reactions": tht, "acyl_donors_in_pathway": donors}

    # 2. mass link of the feature to the pathway products
    feat = pd.read_csv(DATA / "xcms_feature_table.csv", index_col=0)
    mz = float(feat.mzmed[FEATURE]); neutral = mz - H
    products = {"cinnamoyltyramine": "O=C(/C=C/c1ccccc1)NCCc1ccc(O)cc1", "p-coumaroyltyramine": "O=C(/C=C/c1ccc(O)cc1)NCCc1ccc(O)cc1",
                "feruloyltyramine": "O=C(/C=C/c1ccc(O)c(OC)c1)NCCc1ccc(O)cc1", "sinapoyltyramine": "O=C(/C=C/c1cc(OC)c(O)c(OC)c1)NCCc1ccc(O)cc1"}
    links = []
    for n, s in products.items():
        m = ExactMolWt(Chem.MolFromSmiles(s)); d = neutral - m
        links.append({"pathway_product": n, "mass": round(m, 4), "feature_minus_product": round(d, 4)})
    out["feature"] = {"id": FEATURE, "mz": round(mz, 4), "neutral_M_H": round(neutral, 4), "links_to_pathway_products": links,
                      "reading": "+15.9949 (O) from p-coumaroyltyramine, -14.0157 (CH2) from feruloyltyramine: both fit one more hydroxyl on the ring"}

    # 3. putative reaction by analogy and mass balance
    amide, tyr, acid = formula_counts(CAFFEOYLTYRAMINE), formula_counts(TYRAMINE), formula_counts(CAFFEIC_ACID)
    implied_acid = neutral - mass(tyr) + mass({"H": 2, "O": 1})
    acyl_coa = {k: add(COA, acid).get(k, 0) - {"H": 2, "O": 1}.get(k, 0) for k in "CHNOPS"}      # CoA-SH + acid - H2O
    left, right = add(acyl_coa, tyr), add(amide, COA)
    out["putative_reaction"] = {
        "equation": "caffeoyl-CoA + tyramine => caffeoyltyramine + CoA (EC 2.3.1.110, by analogy with RXN_8713/8714/8715 and the feruloyl reaction)",
        "amide_formula": CalcMolFormula(Chem.MolFromSmiles(CAFFEOYLTYRAMINE)), "amide_[M+H]+": round(mass(amide) + H, 4),
        "adduct_error_ppm": round(ppm(mass(amide) + H, mz), 2), "implied_acid_mass": round(implied_acid, 4), "caffeic_acid_mass": round(mass(acid), 4),
        "acid_error_ppm": round(ppm(implied_acid, mass(acid)), 2), "balanced": left == right, "left": left, "right": right}

    # does PlantMetWiki have caffeoyl-CoA / caffeic acid? does Rhea have the reaction?
    names = pd.read_csv(HERE.parent / "metabolomics_overlap" / "data" / "plantmetwiki_metabolites.csv")
    out["plantmetwiki_has"] = {k: names[names.name.str.contains(k, case=False, na=False)].name.tolist()[:6] for k in ("caffeoyl-CoA", "caffeate", "caffeic acid")}
    rh = sparql(RHEA, f'''PREFIX rh: <http://rdf.rhea-db.org/>
SELECT ?r ?eq WHERE {{ ?r rh:ec <http://purl.uniprot.org/enzyme/{EC}> ; rh:equation ?eq }}''')
    out["rhea_reactions_for_ec"] = [r["eq"] for r in rh]
    out["rhea_has_caffeoyl"] = any("caffeoyl" in r["eq"].lower() for r in rh)

    # null: how often does the same inference (implied acid in PlantMetWiki) hit by chance for any feature or random mass?
    ik = pd.read_csv(DATA / "plantmetwiki_metabolite_inchi.csv")
    pm = []
    for i in ik.inchi:
        try:
            m = Chem.MolFromInchi(i)
            if m is not None:
                pm.append(ExactMolWt(m))
        except Exception:
            pass
    pm = np.sort(np.unique(np.round(pm, 4)))

    def hit(x):
        i = np.searchsorted(pm, x)
        return any(0 <= j < len(pm) and abs(ppm(pm[j], x)) <= 5 for j in (i - 1, i))
    allf = feat.mzmed.to_numpy() - H
    imp = allf - mass(tyr) + mass({"H": 2, "O": 1})
    rnd = np.random.default_rng(1).uniform(imp[imp > 100].min(), imp.max(), 2000)
    out["null"] = {"features": len(allf), "features_with_implied_acid_in_plantmetwiki": int(sum(hit(x) for x in imp if x > 100)),
                   "random_masses_hit_rate": round(float(np.mean([hit(x) for x in rnd])), 3), "plantmetwiki_masses": int(len(pm))}
    (RES / "putative_reaction_tht.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
