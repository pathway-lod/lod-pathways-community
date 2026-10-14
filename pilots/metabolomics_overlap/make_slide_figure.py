#!/usr/bin/env python3
"""
Draw one feature of the Brassicaceae LC-MS/MS data (Wolters et al. 2026) as the graph that the proposed terms produce,
for use on a slide. Values come from the S6 node table, results/feature_hits.csv and the generated RDF; the requirement
badges (MET-xx) are looked up in specification/ontology_terms.csv, so they follow the table.

  python make_slide_figure.py                      # feature neg 589 (glucotropaeolin) -> results/example_feature_neg_589.svg
"""

import csv
import glob
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = HERE / "results" / "example_feature_neg_589.svg"
FEATURE, MODE, KEY14 = "589", "neg", "QQGLQYQXUKHWPX"

C = {"data": "#1f6feb", "ontology": "#1a7f37", "local": "#bc4c00", "pmw": "#8250df", "grey": "#6e7781", "ink": "#1f2328",
     "paper": "#ffffff", "line": "#8c959f"}
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def requirement_map():
    m = {}
    for r in csv.DictReader(open(ROOT / "specification" / "ontology_terms.csv", encoding="utf-8")):
        if r["curie"] and r["decision"] != "rejected":
            m.setdefault(r["curie"], [])
            if r["req_id"] not in m[r["curie"]]:
                m[r["curie"]].append(r["req_id"])
    return m


REQ = requirement_map()


def badge_for(curie):
    return ", ".join(REQ.get(curie, [])[:2])


def node_values():
    """Real values of the feature from the S6 node table."""
    f = glob.glob(str(HERE / "data" / "S6_*" / f"*{MODE}*nodetable.csv"))[0]
    with open(f, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["name"] == FEATURE:
                return r
    sys.exit(f"feature {FEATURE} not found in {f}")


def pathways():
    out = []
    for r in csv.DictReader(open(HERE / "data" / "plantmetwiki_metabolite_pathways.csv", encoding="utf-8")):
        if r["inchikey"].startswith(KEY14):
            out.append((r["plantcyc_id"], r["pathway"], r["inchikey"]))
    return out


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=13, fill=None, weight="normal", family=MONO, anchor="start"):
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill or C["ink"]}" text-anchor="{anchor}">{escape(s)}</text>')

    def box(self, x, y, w, h, color, title, rows, subtitle=None):
        """rows: list of (kind, predicate, value_lines, requirement badge)"""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{C["paper"]}" stroke="{color}" stroke-width="2.5"/>')
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
        return y + h

    def arrow(self, d, label=None, lx=0, ly=0, color=None, dashed=False):
        color = color or C["line"]
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.2" marker-end="url(#a)"'
                 + (' stroke-dasharray="6 5"' if dashed else "") + "/>")
        if label:
            self.text(lx, ly, label, size=12.5, fill=color, weight="600", anchor="middle")

    def render(self):
        defs = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{C["line"]}"/></marker></defs>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}">'
                f'<rect width="100%" height="100%" fill="{C["paper"]}"/>{defs}' + "".join(self.parts) + "</svg>")


def main():
    v = node_values()
    pw = pathways()
    mz, rt = float(v["mz"]), float(v["rt"])
    ms2q = float(v["ms2query_ms2query_model_prediction"])
    dmz = float(v["ms2query_precursor_mz_difference"])
    lib = v["library_compound_name"]
    ik = [p[2] for p in pw][0]

    s = Svg(1600, 900)
    s.text(40, 48, "One feature of the Brassicaceae LC-MS/MS data, written with the proposed terms", size=26, weight="700", family=SANS)
    s.text(40, 78, f"Feature {FEATURE} ({MODE}ative mode), annotated as glucotropaeolin. Values from the S6 node table; "
                   "badges name the specification requirement (MET-xx, COM-xx) that holds each term.", size=14, fill=C["grey"], family=SANS)

    # feature
    s.box(40, 230, 380, 300, C["data"], f"Feature {FEATURE} · {MODE}ative mode", [
        ("local", "a lodp:MetaboliteFeature", [], "MET-13"),
        ("local", "lodp:featureId", [f'"{FEATURE}"'], "MET-14"),
        ("ontology", "obo:MS_1000465 (scan polarity)", ["→ MS:1000129 negative scan"], badge_for("MS:1000465")),
        ("local", "lodp:dataset", ["→ MetaboLights MTBLS14270"], "MET-18"),
        ("grey", "m/z and retention time (data)", [f"{mz:.4f}   ·   RT {rt:.2f} min",
                                                   "RT is not in the generated RDF yet (MET-15)"], ""),
    ], subtitle="from the S6 node table, row " + FEATURE)

    # claim
    s.box(520, 290, 330, 220, C["local"], "Annotation claim", [
        ("local", "a lodp:MetaboliteAnnotation", [], "MET-09"),
        ("local", "lodp:matchLevel", ['"connectivity" (first InChIKey block)'], "MET-08"),
        ("local", "lodp:anchorTier", ['"structure_match"'], ""),
        ("ontology", "skos:closeMatch", ["→ Wikidata Q27125128"], "MET-09"),
    ])
    s.arrow("M520,400 L420,400", "lodp:feature", 470, 388)

    # evidence 1 and 2
    s.box(920, 150, 350, 240, C["ontology"], "Evidence 1 · GNPS library match", [
        ("ontology", "a ECO:0001580", ["LC-MS/MS evidence"], badge_for("ECO:0001580")),
        ("local", "lodp:identificationTier", ['"gnps_library"'], ""),
        ("local", "lodp:libraryCompoundName", [f'"{lib.split(" ", 1)[0]}', f'{lib.split(" ", 1)[1]}"'], "MET-04"),
        ("ontology", "prov:wasGeneratedBy", ["→ lodp:run_gnps_library"], badge_for("prov:wasGeneratedBy")),
    ])
    s.box(920, 410, 350, 262, C["ontology"], "Evidence 2 · MS2Query, exact mass", [
        ("ontology", "a ECO:0001580, ECO:0007669", ["LC-MS/MS and computational evidence"], "MET-01, MET-03"),
        ("local", "lodp:identificationTier", ['"ms2query_exact"'], ""),
        ("local", "lodp:ms2queryModelScore", [f"{ms2q:.3f}"], "MET-12"),
        ("local", "lodp:precursorMzDifference", [f"{dmz:.4f}"], "MET-12"),
        ("ontology", "prov:wasGeneratedBy", ["→ lodp:run_ms2query"], badge_for("prov:wasGeneratedBy")),
    ])
    s.arrow("M850,360 C890,360 880,255 920,255", None, color=C["ontology"])
    s.arrow("M850,440 C890,440 880,535 920,535", None, color=C["ontology"])
    s.text(685, 540, "sio:SIO_000772 has evidence (to both evidence nodes)", size=12.5, fill=C["ontology"], weight="600", anchor="middle")

    # PlantMetWiki
    s.box(1320, 150, 250, 215, C["pmw"], "PlantMetWiki (existing)", [
        ("pmw", "a wp:Metabolite", [], ""),
        ("pmw", "IRI = InChIKey", ["identifiers.org/inchikey/", ik[:14] + "-", ik[15:]], ""),
        ("pmw", "rdfs:label", ['"glucotropaeolin"'], ""),
    ])
    # anchor edge along the top
    s.arrow("M685,290 L685,118 L1445,118 L1445,150", "lodp:anchoredToMetabolite  (the claim points at the node that already exists)",
            1065, 108, color=C["pmw"])
    y = 410
    for n, (pid, name, _) in enumerate(pw[:2]):
        lines, cur = [], ""
        for w in name.split():
            if len(cur) + len(w) + 1 > 27 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        h = 74 + 18 * len(lines)
        s.box(1320, y, 250, h, C["pmw"], f"PlantCyc {pid}", [("pmw", "a wp:Pathway", lines, "")])
        if n == 0:
            s.arrow(f"M1445,365 L1445,{y}", None, color=C["pmw"])
            s.text(1435, 392, "dcterms:isPartOf", size=12.5, fill=C["pmw"], weight="600", anchor="end")
        else:
            s.arrow(f"M1320,340 L1296,340 L1296,{y + 40} L1320,{y + 40}", None, color=C["pmw"])
        y += h + 24

    # what to look at
    for i, t in enumerate(["The claim is its own node: it says how the feature was identified and how well. PlantMetWiki itself is not changed.",
                           "Two independent pieces of evidence (spectral library, MS2Query) support the same claim, each from its own run.",
                           "Orange terms are not in an ontology yet: these are the points for discussion."]):
        s.add(f'<circle cx="52" cy="{708 + i * 26}" r="4" fill="{C["ink"]}"/>')
        s.text(66, 713 + i * 26, t, size=15, family=SANS)
    # legend
    ly = 810
    s.text(40, ly - 10, "Legend", size=14, weight="700", family=SANS)
    for i, (col, lab) in enumerate([(C["data"], "data of the dataset"), (C["ontology"], "existing ontology term, reused"),
                                    (C["local"], "local term lodp: (to be agreed)"),
                                    (C["pmw"], "already in PlantMetWiki"), (C["grey"], "in the data, not in the RDF yet")]):
        x = 40 + i * 310
        s.add(f'<rect x="{x}" y="{ly + 8}" width="18" height="18" rx="4" fill="{col}"/>')
        s.text(x + 26, ly + 22, lab, size=13, family=SANS)
    s.text(40, ly + 62, "Source: Wolters et al. 2026, Zenodo 10.5281/zenodo.19391098 (S6); pilot pilots/metabolomics_overlap; "
                        "specification pathway-lod/lod-pathways-community.", size=12, fill=C["grey"], family=SANS)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(s.render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
