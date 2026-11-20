"""Overlap of the CASMI 2026 (Enveda) training structures with PlantMetWiki compounds and pathways, on inchikey14.

Needs data/competitions/enveda-CASMI26-molecule-id-mass-spectra/train.parquet (see notebooks/00_download_and_columns.ipynb).
Writes results/: overlap_per_library.csv, overlap_compounds.csv, pathway_spectra_coverage.csv, overlap_summary.json
"""
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
TRAIN = HERE / "data/competitions/enveda-CASMI26-molecule-id-mass-spectra/train.parquet"
MD = HERE.parent / "metabolomics_overlap" / "data"
MAX_PPM = 10


def main():
    tr = pd.read_parquet(TRAIN, columns=["inchikey", "inchikey14", "ingest_lib", "adduct", "precursor_error_ppm", "molecular_formula"])
    pmw = pd.read_csv(MD / "plantmetwiki_metabolites.csv")
    pmw["k14"] = pmw.inchikey.str[:14]
    pw = pd.read_csv(MD / "plantmetwiki_metabolite_pathways.csv", dtype=str)
    pw = pw[~pw.plantcyc_id.str.contains("RXN")]; pw["k14"] = pw.inchikey.str[:14]
    pk = set(pmw.k14); pwk = set(pw.k14)
    good = tr[tr.precursor_error_ppm.abs() <= MAX_PPM]
    out = {"spectra": len(tr), "structures": tr.inchikey14.nunique(), "spectra_precursor_error_le_10ppm": len(good),
           "structures_with_good_spectrum": good.inchikey14.nunique(), "pmw_compounds": len(pk), "pmw_compounds_in_pathway": len(pwk)}

    rows = []
    for lib, d in list(tr.groupby("ingest_lib")) + [("ALL", tr)]:
        s = set(d.inchikey14); g = set(d[d.precursor_error_ppm.abs() <= MAX_PPM].inchikey14)
        rows.append({"library": lib, "spectra": len(d), "structures": len(s), "pmw_matches": len(s & pk), "pmw_in_pathway": len(s & pwk),
                     "pct_of_structures": round(100 * len(s & pk) / len(s), 2), "pmw_matches_good_spectrum": len(g & pk)})
    per = pd.DataFrame(rows).sort_values("structures", ascending=False)
    per.to_csv(HERE / "results/overlap_per_library.csv", index=False)

    m = tr[tr.inchikey14.isin(pk)]
    comp = (m.groupby("inchikey14").agg(spectra=("inchikey14", "size"), libraries=("ingest_lib", lambda x: ";".join(sorted(set(x)))), adducts=("adduct", lambda x: ";".join(sorted(set(x.dropna()))[:6])),
                                        formula=("molecular_formula", "first"), full_key_matches=("inchikey", "nunique")).reset_index()
            .merge(pmw[["k14", "name", "n_pathways"]].drop_duplicates("k14"), left_on="inchikey14", right_on="k14").drop(columns="k14"))
    comp.to_csv(HERE / "results/overlap_compounds.csv", index=False)
    out["overlap_compounds"] = len(comp); out["overlap_compounds_in_pathway"] = len(set(comp.inchikey14) & pwk)
    out["overlap_pct_of_pmw"] = round(100 * len(comp) / len(pk), 1)
    out["n_libraries_per_compound"] = comp.libraries.str.count(";").add(1).value_counts().sort_index().to_dict()

    have = set(comp.inchikey14)
    pcov = (pw.drop_duplicates(["k14", "plantcyc_id"]).assign(has=lambda d: d.k14.isin(have)).groupby(["plantcyc_id", "pathway"])
              .agg(members=("k14", "nunique"), with_spectra=("has", "sum")).reset_index())
    pcov["fraction"] = (pcov.with_spectra / pcov.members).round(3)
    pcov.sort_values(["with_spectra", "members"], ascending=False).to_csv(HERE / "results/pathway_spectra_coverage.csv", index=False)
    out["pathways"] = len(pcov); out["pathways_with_any_spectrum"] = int((pcov.with_spectra > 0).sum())
    out["pathways_ge_50pct_with_spectra_and_ge4_members"] = int(((pcov.fraction >= 0.5) & (pcov.members >= 4)).sum())
    (HERE / "results/overlap_summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)); print(per.to_string())


if __name__ == "__main__":
    main()
