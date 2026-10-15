#!/usr/bin/env python3
"""
Version 2 of the slide figure (v1 is kept: make_slide_figure.py). Same feature (neg 589), now with the prediction that did NOT
match PlantMetWiki (SIRIUS) next to the two predictions that did (GNPS library, MS2Query), and the class-level agreement of the tools.

  python make_slide_figure_v2.py        # -> results/example_feature_neg_589_v2.svg

Values come from the S6 node table and the PlantMetWiki snapshot of the pilot. The unmatched claim is a PROPOSAL: the current RDF
export drops predictions that are not in PlantMetWiki and the annotation shape requires lodp:anchoredToMetabolite. Dashed borders
mark everything that is not in the current RDF or shapes.
"""

import csv
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import make_slide_figure as v1
from make_slide_figure import C, MONO, SANS, ROOT

OUT = Path(__file__).parent / "results" / "example_feature_neg_589_v2.svg"
DY = 110           # room for the three reading hints at the top


class Svg2(v1.Svg):
    def box(self, x, y, w, h, color, title, rows, subtitle=None, dashed=False):
        dash = ' stroke-dasharray="9 6"' if dashed else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{C["paper"]}" stroke="{color}" stroke-width="2.5"{dash}/>')
        self.add(f'<path d="M{x},{y + 10} a10,10 0 0 1 10,-10 h{w - 20} a10,10 0 0 1 10,10 v{34 - 10} h-{w} z" fill="{color}"/>')
        self.text(x + 14, y + 23, title, size=15, fill="#fff", weight="600", family=SANS)
        cy = y + 58
        if subtitle:
            self.text(x + 14, cy, subtitle, size=12, fill=C["grey"], family=SANS)
            cy += 22
        for kind, pred, values, badge in rows:
            col = {"ontology": C["ontology"], "local": C["local"], "grey": C["grey"], "data": C["data"], "pmw": C["pmw"]}[kind]
            self.text(x + 14, cy, pred, size=12.5, fill=col, weight="600")
            if badge:
                bw = 7 * len(badge) + 14
                self.add(f'<rect x="{x + w - bw - 10}" y="{cy - 14}" width="{bw}" height="19" rx="9.5" fill="{col}" opacity="0.14"/>')
                self.text(x + w - bw / 2 - 10, cy, badge, size=11, fill=col, weight="600", family=SANS, anchor="middle")
            cy += 19
            for v in values:
                self.text(x + 28, cy, v, size=12.5, fill=C["ink"])
                cy += 18
            cy += 5


def wrap(name, width):
    lines, cur = [], ""
    for w in name.split():
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur]


def sirius_values():
    row = v1.node_values()
    return {k: row[k] for k in ("sirius_name", "sirius_molecularFormula", "sirius_InChIkey2D", "sirius_ConfidenceScoreApproximate",
                                "match_type_class", "match_value_class", "match_columns_class", "match_type_inchi",
                                "canopus_npc_class", "ms2query_npc_class_results")}


def in_plantmetwiki(key14):
    with open(Path(__file__).parent / "data" / "plantmetwiki_metabolites.csv", encoding="utf-8") as fh:
        return any(key14 in line for line in fh)


def main():
    v = v1.node_values()
    sv = sirius_values()
    pw = v1.pathways()
    mz, rt = float(v["mz"]), float(v["rt"])
    ms2q = float(v["ms2query_ms2query_model_prediction"])
    dmz = float(v["ms2query_precursor_mz_difference"])
    lib = v["library_compound_name"]
    ik = pw[0][2]
    skey = sv["sirius_InChIkey2D"]
    if in_plantmetwiki(skey):
        sys.exit(f"{skey} is in PlantMetWiki: this figure is about a prediction that is not")
    y0 = DY

    s = Svg2(1920, 1130)
    s.text(40, 46, "One feature, three predictions: how the graph holds the matches and the prediction without a match",
           size=26, weight="700", family=SANS)
    for i, t in enumerate([
            "Feature 589 (negative mode). GNPS library and MS2Query name glucotropaeolin, which is a PlantMetWiki node; SIRIUS proposes another structure, which is not.",
            "Matched claims point at the existing node. The unmatched claim stays on the same feature without an anchor, so nothing is lost and PlantMetWiki is not changed.",
            "Dashed borders: not in the current RDF export or shapes (proposal for discussion). Solid: generated today."]):
        s.text(40, 78 + i * 24, t, size=15, fill=C["grey"] if i < 2 else C["local"], family=SANS)

    # ---- feature
    s.box(40, y0 + 150, 400, 300, C["data"], "Feature 589 · negative mode", [
        ("local", "a lodp:MetaboliteFeature", [], "MET-13"),
        ("local", "lodp:featureId", ['"589"'], "MET-14"),
        ("ontology", "obo:MS_1000465 (scan polarity)", ["→ MS:1000129 negative scan"], v1.badge_for("MS:1000465")),
        ("local", "lodp:dataset", ["→ MetaboLights MTBLS14270"], "MET-18"),
        ("grey", "m/z and retention time (data)", [f"{mz:.4f}   ·   RT {rt:.2f} min", "RT is not in the generated RDF yet (MET-15)"], ""),
    ], subtitle="from the S6 node table, row 589")

    # ---- claim A (matched)
    s.box(560, y0 + 210, 350, 220, C["local"], "Claim A · matched", [
        ("local", "a lodp:MetaboliteAnnotation", [], "MET-09"),
        ("local", "lodp:matchLevel", ['"connectivity" (first block)'], "MET-08"),
        ("local", "lodp:anchorTier", ['"structure_match"'], ""),
        ("ontology", "skos:closeMatch", ["→ Wikidata Q27125128"], "MET-09"),
    ])
    s.arrow(f"M560,{y0 + 320} L440,{y0 + 320}", "lodp:feature", 500, y0 + 308)

    # evidence 1 and 2
    s.box(1010, y0 + 70, 380, 240, C["ontology"], "Evidence 1 · GNPS library match", [
        ("ontology", "a ECO:0001580", ["LC-MS/MS evidence"], v1.badge_for("ECO:0001580")),
        ("local", "lodp:identificationTier", ['"gnps_library"'], ""),
        ("local", "lodp:libraryCompoundName", [f'"{lib.split(" ", 1)[0]}', f'{lib.split(" ", 1)[1]}"'], "MET-04"),
        ("ontology", "prov:wasGeneratedBy", ["→ lodp:run_gnps_library"], v1.badge_for("prov:wasGeneratedBy")),
    ])
    s.box(1010, y0 + 330, 380, 262, C["ontology"], "Evidence 2 · MS2Query, exact mass", [
        ("ontology", "a ECO:0001580, ECO:0007669", ["LC-MS/MS and computational evidence"], "MET-01, MET-03"),
        ("local", "lodp:identificationTier", ['"ms2query_exact"'], ""),
        ("local", "lodp:ms2queryModelScore", [f"{ms2q:.3f}"], "MET-12"),
        ("local", "lodp:precursorMzDifference", [f"{dmz:.4f}"], "MET-12"),
        ("ontology", "prov:wasGeneratedBy", ["→ lodp:run_ms2query"], v1.badge_for("prov:wasGeneratedBy")),
    ])
    s.arrow(f"M910,{y0 + 280} C950,{y0 + 280} 940,{y0 + 175} 1010,{y0 + 175}", None, color=C["ontology"])
    s.arrow(f"M910,{y0 + 360} C950,{y0 + 360} 940,{y0 + 455} 1010,{y0 + 455}", None, color=C["ontology"])
    s.text(735, y0 + 460, "sio:SIO_000772 has evidence", size=12.5, fill=C["ontology"], weight="600", anchor="middle")

    # ---- PlantMetWiki (existing)
    s.box(1480, y0 + 70, 400, 215, C["pmw"], "PlantMetWiki (existing)", [
        ("pmw", "a wp:Metabolite", [], ""),
        ("pmw", "IRI = InChIKey", ["identifiers.org/inchikey/", ik[:14] + "-" + ik[15:]], ""),
        ("pmw", "rdfs:label", ['"glucotropaeolin"'], ""),
    ])
    s.arrow(f"M735,{y0 + 210} L735,{y0 + 38} L1680,{y0 + 38} L1680,{y0 + 70}",
            "lodp:anchoredToMetabolite  (points at the node that already exists)", 1210, y0 + 28, color=C["pmw"])
    y = y0 + 330
    for n, (pid, name, _) in enumerate(pw[:2]):
        lines = wrap(name, 40)
        h = 74 + 18 * len(lines)
        s.box(1480, y, 400, h, C["pmw"], f"PlantCyc {pid}", [("pmw", "a wp:Pathway", lines, "")])
        if n == 0:
            s.arrow(f"M1680,{y0 + 285} L1680,{y}", None, color=C["pmw"])
            s.text(1670, y0 + 312, "dcterms:isPartOf", size=12.5, fill=C["pmw"], weight="600", anchor="end")
        else:
            s.arrow(f"M1480,{y0 + 260} L1456,{y0 + 260} L1456,{y + 40} L1480,{y + 40}", None, color=C["pmw"])
        y += h + 24

    # ---- agreement across tools (class level)
    s.box(40, y0 + 500, 400, 252, C["data"], "Agreement across tools (consensus)", [
        ("local", "lodp:matchCategory", ['"class"  (NPClassifier)'], "MET-11"),
        ("local", "lodp:matchType", ['"partial"  (2 of 3 tools)'], "MET-11"),
        ("grey", "class, both tools", [f"{sv['match_value_class']}  (SIRIUS/CANOPUS, MS2Query)"], ""),
        ("grey", "structure level", ["none: the tools name different structures"], ""),
    ], subtitle="from S4 / S6 columns match_*_class and match_*_inchi")

    # ---- claim B (not matched): proposal
    s.box(560, y0 + 600, 350, 252, C["local"], "Claim B · no match in PlantMetWiki", [
        ("local", "a lodp:MetaboliteAnnotation", [], "MET-09"),
        ("local", "lodp:matchLevel", ['"connectivity" (first block)'], "MET-08"),
        ("local", "lodp:anchorTier", ['"none"   (new value)'], "proposal"),
        ("local", "lodp:predictedKey", [f'"{skey}"   (new term)'], "proposal"),
        ("grey", "lodp:anchoredToMetabolite", ["absent: no node with this key"], ""),
    ], dashed=True)
    s.arrow(f"M560,{y0 + 680} L500,{y0 + 680} L500,{y0 + 340} L440,{y0 + 340}", None, color=C["line"], dashed=True)

    s.box(1010, y0 + 620, 380, 288, C["ontology"], "Evidence 3 · SIRIUS CSI:FingerID", [
        ("ontology", "a ECO:0001580, ECO:0007669", ["LC-MS/MS and computational evidence"], "MET-01, MET-03"),
        ("local", "lodp:identificationTier", ['"sirius"'], ""),
        ("grey", "predicted structure (data)", [sv["sirius_name"][:38], f"{sv['sirius_molecularFormula']}  ·  {skey}"], ""),
        ("local", "lodp:siriusConfidenceApprox", ["no value in the data (file has -Infinity): left out"], "MET-12"),
        ("ontology", "prov:wasGeneratedBy", ["→ lodp:run_sirius"], v1.badge_for("prov:wasGeneratedBy")),
    ], dashed=True)
    s.arrow(f"M910,{y0 + 715} C950,{y0 + 715} 960,{y0 + 715} 1010,{y0 + 715}", None, color=C["ontology"], dashed=True)
    s.text(735, y0 + 874, "sio:SIO_000772 has evidence", size=12.5, fill=C["ontology"], weight="600", anchor="middle")

    # where the unmatched claim would anchor
    s.box(1480, y0 + 620, 400, 150, C["pmw"], "PlantMetWiki: no such node", [
        ("grey", f"first block {skey}", ["is not among the PlantMetWiki metabolites", "of the pilot snapshot (2026-09-29)", "candidate for a new metabolite entry"], ""),
    ], dashed=True)

    # legend
    ly = y0 + 800
    s.text(1480, ly, "Legend", size=14, weight="700", family=SANS)
    for i, (col, lab) in enumerate([(C["data"], "data of the dataset"), (C["ontology"], "existing ontology term, reused"),
                                    (C["local"], "local term lodp: (to be agreed)"), (C["pmw"], "already in PlantMetWiki"),
                                    (C["grey"], "in the data, not in the RDF yet")]):
        yy = ly + 22 + i * 24
        s.add(f'<rect x="1480" y="{yy - 13}" width="16" height="16" rx="4" fill="{col}"/>')
        s.text(1504, yy, lab, size=13, family=SANS)
    s.text(40, 1110, "Source: Wolters et al. 2026, Zenodo 10.5281/zenodo.19391098 (S4, S6); pilot pilots/metabolomics_overlap; "
                     "specification pathway-lod/lod-pathways-community.", size=12, fill=C["grey"], family=SANS)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(s.render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
