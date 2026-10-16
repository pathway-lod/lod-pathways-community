#!/usr/bin/env python3
"""
Validate ontology_terms.csv, fill term labels from the Ontology Lookup Service, and regenerate the
tables in SPECIFICATION.md. The CSV is the source of truth; the tables in the Markdown are generated.

  python check_terms.py                    # validate the CSV (no network); also warns if the tables are stale
  python check_terms.py --online           # also check every term ID in the Ontology Lookup Service
  python check_terms.py --update           # like --online, and write label, IRI and check date of new or changed terms into the CSV
  python check_terms.py --update --reverify  # ... and refresh the check date of every term
  python check_terms.py --render           # regenerate the tables in SPECIFICATION.md and the dashboard index.html
  python check_terms.py --update --render  # both (the usual thing to run after editing the CSV)

Exit code: 0 = no errors, 1 = errors (warnings do not fail), 2 = stale tables with --check-render.
Only the standard library is needed; --online needs `requests`, and local labels need `rdflib` (optional).
"""

import argparse
import csv
import datetime
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CSV_PATH = HERE / "ontology_terms.csv"
MD_PATH = HERE / "SPECIFICATION.md"
HTML_PATH = HERE / "index.html"
VOCAB = HERE.parent / "shape_constraints" / "vocab" / "lodp.ttl"
LODP_NS = "https://example.org/lod-pathways/pilot/"

COLUMNS = ["row_id", "req_id", "use_case", "requirement", "element_type", "role", "curie", "label", "ontology", "iri",
           "coverage", "decision", "action", "used_in", "value_of", "notes", "source", "owner", "issue_url", "verified"]

USE_CASES = OrderedDict([   # key: (acronym = prefix of the requirement IDs, title shown everywhere)
    ("plantcyc", ("PMN", "PMN - PlantCyc computationally inferred")),
    ("bgc", ("BGC", "BGC - plantiSMASH BGCs")),
    ("metabolomics", ("MET", "MET - Metabolomics data")),
    ("paired_omics", ("PO", "PO - Paired omics data")),
    ("unsupervised", ("UN", "UN - Unsupervised predictions")),
    ("transcriptomics", ("TX", "TX - Transcriptomics data")),
    ("common", ("COM", "COM - Shared by all use cases")),
])
ACRONYMS = {   # what each acronym stands for
    "PMN": "Plant Metabolic Network (PlantCyc and the other Cyc databases)",
    "BGC": "biosynthetic gene cluster",
    "MET": "metabolomics",
    "PO": "paired omics (transcriptomics and metabolomics of the same samples)",
    "UN": "unsupervised (machine-learning) predictions",
    "TX": "transcriptomics",
    "COM": "common to all use cases",
}

ENUMS = {
    "element_type": {"class", "relation", "property", "evidence_type", "identifier", "method", "value_set", "other"},
    "role": {"primary", "alternative", "stand_in", "local", "gap"},
    "coverage": {"exact", "partial", "none"},
    "decision": {"proposed", "open", "agreed", "rejected"},
    "action": {"reuse", "request_term", "local_term", "review", "ask", "none"},
}
USED_IN = {"sample_graph", "shapes", "rdf"}

# code -> (name, homepage, CURIE prefix of its terms, resolvable in the Ontology Lookup Service?)
ONTOLOGIES = {
    "ECO": ("Evidence & Conclusion Ontology", "https://www.evidenceontology.org/", "ECO", True),
    "SO": ("Sequence Ontology", "http://www.sequenceontology.org/", "SO", True),
    "SIO": ("Semanticscience Integrated Ontology", "https://github.com/MaastrichtU-IDS/semanticscience", "SIO", True),
    "STATO": ("Statistical Methods Ontology", "https://stato-ontology.org/", "STATO", True),
    "OBI": ("Ontology for Biomedical Investigations", "https://obi-ontology.org/", "OBI", True),
    "RO": ("Relation Ontology", "https://oborel.github.io/", "RO", True),
    "BFO": ("Basic Formal Ontology", "https://basic-formal-ontology.org/", "BFO", True),
    "EDAM": ("EDAM (data analysis and management)", "https://edamontology.org/", "EDAM", True),
    "SWO": ("Software Ontology", "https://github.com/allysonlister/swo", "SWO", True),
    "MS": ("PSI-MS (mass spectrometry ontology)", "https://www.psidev.info/", "MS", True),
    "MSIO": ("Metabolomics Standards Initiative Ontology", "https://github.com/MSI-Metabolomics-Standards-Initiative/MSIO", "MSIO", True),
    "CHEMINF": ("Chemical Information Ontology", "https://github.com/semanticchemistry/semanticchemistry", "CHEMINF", True),
    "SEPIO": ("Scientific Evidence and Provenance Information Ontology", "https://github.com/monarch-initiative/SEPIO-ontology", "SEPIO", True),
    "NCIT": ("NCI Thesaurus", "https://ncithesaurus.nci.nih.gov/", "NCIT", True),
    "AIO": ("Artificial Intelligence Ontology", "https://github.com/berkeleybop/artificial-intelligence-ontology", "AIO", True),
    "GENEPIO": ("Genomic Epidemiology Ontology", "https://genepio.org/", "GENEPIO", True),
    "PO": ("Plant Ontology", "https://planteome.org/", "PO", True),
    "EFO": ("Experimental Factor Ontology", "https://www.ebi.ac.uk/efo/", "EFO", True),
    "INO": ("Interaction Network Ontology", "https://github.com/INO-ontology/ino", "INO", True),
    "AGRO": ("Agronomy Ontology", "https://github.com/AgriculturalSemantics/agro", "AGRO", True),
    "PROV": ("PROV-O (provenance)", "https://www.w3.org/TR/prov-o/", "prov", False),
    "SKOS": ("SKOS (mapping relations)", "https://www.w3.org/TR/skos-reference/", "skos", False),
    "DCTERMS": ("Dublin Core Terms", "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/", "dcterms", False),
    "RDF": ("RDF", "https://www.w3.org/TR/rdf11-concepts/", "rdf", False),
    "WP": ("WikiPathways vocabulary", "https://vocabularies.wikipathways.org/wp", "wp", False),
    "identifiers.org": ("identifiers.org IRIs", "https://identifiers.org/", "identifiers.org", False),
    "lodp": ("Local placeholder vocabulary (draft)", "../shape_constraints/vocab/lodp.ttl", "lodp", False),
}
CURIE_RE = re.compile(r"^[A-Za-z][A-Za-z.]*:[A-Za-z0-9_]+$")
REQ_RE = re.compile(r"^([A-Z]+)-(\d{2,})$")
OLS_SEARCH = "https://www.ebi.ac.uk/ols4/api/search"

STATUS_ORDER = {"covered": 0, "partial": 1, "gap": 2}
STATUS_BADGE = {"covered": "🟢 covered", "partial": "🟡 partial", "gap": "🔴 gap"}
DECISION_BADGE = {"open": "🟠 open", "proposed": "🔵 proposed", "agreed": "✅ agreed", "rejected": "⛔ rejected"}
ACTION_PRIORITY = {"ask": 0, "request_term": 1, "review": 2, "local_term": 3, "reuse": 4, "none": 5}
DECISION_RANK = {"open": 0, "proposed": 1, "agreed": 2}


# --------------------------------------------------------------------------------------------- CSV
def read_rows(path=CSV_PATH):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = [dict(r) for r in reader]
    return header, rows


def write_rows(rows, path=CSV_PATH):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def tokens(cell):
    return [t.strip() for t in (cell or "").split(",") if t.strip()]


# --------------------------------------------------------------------------------------------- validation
def local_terms_in_vocab():
    """CURIEs of the terms defined in shape_constraints/vocab/lodp.ttl (needs rdflib), or None."""
    try:
        from rdflib import RDF, RDFS, Graph, URIRef
    except ImportError:
        return None, {}
    if not VOCAB.exists():
        return None, {}
    g = Graph().parse(str(VOCAB), format="turtle")
    labels = {}
    for s in set(g.subjects(RDF.type, None)):
        if isinstance(s, URIRef) and str(s).startswith(LODP_NS) and str(s) != LODP_NS:
            lab = g.value(s, RDFS.label)
            labels["lodp:" + str(s)[len(LODP_NS):]] = str(lab) if lab else ""
    return set(labels), labels


def validate(header, rows):
    errors, warnings = [], []

    def err(row, msg):
        errors.append(f"{row['row_id'] or '?'} ({row['req_id']}): {msg}")

    def warn(row, msg):
        warnings.append(f"{row['row_id'] or '?'} ({row['req_id']}): {msg}")

    if sorted(header) != sorted(COLUMNS):
        missing, extra = set(COLUMNS) - set(header), set(header) - set(COLUMNS)
        errors.append(f"columns differ from the specification: missing {sorted(missing)}, unexpected {sorted(extra)}")
        return errors, warnings

    seen_ids, seen_pairs = set(), set()
    all_curies = {r["curie"].strip() for r in rows if r["curie"].strip()}
    per_req = defaultdict(list)
    vocab_terms, _ = local_terms_in_vocab()
    for r in rows:
        if not r["row_id"]:
            err(r, "row_id is empty")
        elif r["row_id"] in seen_ids:
            err(r, "duplicate row_id")
        seen_ids.add(r["row_id"])

        m = REQ_RE.match(r["req_id"])
        uc = r["use_case"]
        if uc not in USE_CASES:
            err(r, f"use_case '{uc}' is not one of {list(USE_CASES)}")
        elif not m or m.group(1) != USE_CASES[uc][0]:
            err(r, f"req_id must look like {USE_CASES.get(uc, ('?',))[0]}-01 for use case '{uc}'")
        if not r["requirement"].strip():
            err(r, "requirement is empty")
        per_req[r["req_id"]].append(r)

        for col, allowed in ENUMS.items():
            if r[col] not in allowed:
                err(r, f"{col} '{r[col]}' is not one of {sorted(allowed)}")
        bad = [t for t in tokens(r["used_in"]) if t not in USED_IN]
        if bad:
            err(r, f"used_in has unknown values {bad}; allowed: {sorted(USED_IN)}")

        role, curie, ont = r["role"], r["curie"].strip(), r["ontology"].strip()
        if role == "gap":
            if r["action"] == "ask" and not r["owner"].strip():
                err(r, "action 'ask' means asking a named person: fill the owner column")
            if curie or ont:
                err(r, "a gap row has no term: curie and ontology must be empty")
            if r["coverage"] != "none":
                err(r, "a gap row must have coverage 'none'")
            continue
        if not curie:
            err(r, f"role '{role}' needs a curie")
            continue
        if ont not in ONTOLOGIES:
            err(r, f"ontology '{ont}' is not in the list of known ontologies; add it to ONTOLOGIES in check_terms.py")
            continue
        prefix = ONTOLOGIES[ont][2]
        if ont != "identifiers.org" and not CURIE_RE.match(curie):
            err(r, f"'{curie}' is not a valid CURIE")
        if not curie.startswith(prefix + ":"):
            err(r, f"curie '{curie}' does not belong to ontology {ont} (expected prefix '{prefix}:')")
        if (role == "local") != (ont == "lodp"):
            err(r, "role 'local' and ontology 'lodp' go together")
        if role == "local" and r["coverage"] != "none":
            err(r, "a local term fills a gap: coverage must be 'none'")
        if role in ("primary", "alternative", "stand_in") and r["coverage"] == "none":
            err(r, f"a {role} term must have coverage 'exact' or 'partial'")
        if role == "stand_in" and r["coverage"] != "partial":
            warn(r, "a stand-in is by definition a partial fit")
        if (r["req_id"], curie) in seen_pairs:
            err(r, f"term {curie} appears twice for this requirement")
        seen_pairs.add((r["req_id"], curie))
        if r["decision"] == "rejected" and role in ("primary", "local"):
            warn(r, "a rejected term should not be primary or local")
        if r["action"] == "ask" and not r["owner"].strip():
            err(r, "action 'ask' means asking a named person: fill the owner column")
        if r["value_of"].strip() and r["value_of"].strip() not in all_curies:
            err(r, f"value_of '{r['value_of']}' is not a term (curie) of the table")
        if r["value_of"].strip() == curie:
            err(r, "a term cannot be a value of itself")
        if r["action"] == "local_term" and role != "local":
            warn(r, "action 'local_term' on a row that is not a local term")
        if role == "local" and vocab_terms is not None and curie not in vocab_terms:
            warn(r, f"{curie} is not defined in shape_constraints/vocab/lodp.ttl yet")

    for req_id, group in per_req.items():
        for col in ("use_case", "requirement"):
            if len({g[col] for g in group}) > 1:
                errors.append(f"{req_id}: rows disagree on {col}")
        if not any(g["role"] in ("primary", "stand_in", "local", "gap") for g in group):
            warnings.append(f"{req_id}: only alternatives; add a primary, stand-in, local or gap row")
    return errors, warnings


# --------------------------------------------------------------------------------------------- Ontology Lookup Service
def ols_resolve(curie, cache):
    import requests

    if curie in cache:
        return cache[curie]
    prefix = curie.split(":")[0]
    r = requests.get(OLS_SEARCH, params={"q": curie, "queryFields": "obo_id", "exact": "true", "rows": 30}, timeout=60)
    r.raise_for_status()
    hits = [d for d in r.json()["response"]["docs"] if d.get("obo_id") == curie]
    if not hits:
        cache[curie] = None
        return None
    hits.sort(key=lambda d: (d.get("ontology_name") != prefix.lower(), bool(d.get("is_obsolete")),
                             (d.get("label") or "").replace("_", "") == curie.replace(":", "").replace("_", "")))
    d = hits[0]
    cache[curie] = {"label": d.get("label") or "", "iri": d.get("iri") or "", "obsolete": bool(d.get("is_obsolete"))}
    return cache[curie]


def online_check(rows, update, reverify=False):
    """Look every OLS-resolvable term up. Returns (errors, warnings, rows changed)."""
    errors, warnings, changed = [], [], 0
    cache = {}
    today = datetime.date.today().isoformat()
    _, local_labels = local_terms_in_vocab()
    for r in rows:
        curie, ont = r["curie"].strip(), r["ontology"].strip()
        if not curie:
            continue
        if ont == "lodp":
            if update:
                iri = LODP_NS + curie.split(":", 1)[1]
                lab = local_labels.get(curie, "") or r["label"]
                if (r["label"], r["iri"]) != (lab, iri):
                    r["label"], r["iri"], changed = lab, iri, changed + 1
            continue
        if not ONTOLOGIES.get(ont, ("", "", "", False))[3]:
            continue
        found = ols_resolve(curie, cache)
        where = f"{r['row_id']} ({r['req_id']}) {curie}"
        if not found:
            errors.append(f"{where}: not found in the Ontology Lookup Service")
            continue
        if found["obsolete"]:
            errors.append(f"{where}: term is obsolete")
        if r["label"] and r["label"] != found["label"] and not update:
            warnings.append(f"{where}: label '{r['label']}' differs from '{found['label']}'")
        if update:
            # keep the old check date when nothing changed, so that a daily run does not rewrite every row
            if (r["label"], r["iri"]) != (found["label"], found["iri"]) or not r["verified"] or reverify:
                r["label"], r["iri"], r["verified"] = found["label"], found["iri"], today
                changed += 1
    return errors, warnings, changed


# --------------------------------------------------------------------------------------------- rendering
def esc(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def term_text(r):
    parts = []
    if r["curie"]:
        parts.append(f"`{r['curie']}`")
    if r["label"]:
        parts.append(esc(r["label"]))
    if r.get("value_of", "").strip():
        parts.append(f"(value of `{r['value_of'].strip()}`)")
    return " ".join(parts)


def requirements(rows):
    """req_id -> dict with the requirement text, use case, rows and the derived status."""
    out = OrderedDict()
    for r in sorted(rows, key=lambda r: (list(USE_CASES).index(r["use_case"]) if r["use_case"] in USE_CASES else 99,
                                         r["req_id"], r["row_id"])):
        d = out.setdefault(r["req_id"], {"id": r["req_id"], "use_case": r["use_case"], "text": r["requirement"], "rows": []})
        d["rows"].append(r)
    for d in out.values():
        live = [r for r in d["rows"] if r["decision"] != "rejected"]
        if any(r["role"] == "primary" and r["coverage"] == "exact" for r in live):
            d["status"] = "covered"
        elif any(r["role"] in ("primary", "stand_in") for r in live):
            d["status"] = "partial"
        else:
            d["status"] = "gap"
        ranks = [DECISION_RANK[r["decision"]] for r in live] or [2]
        d["decision"] = {v: k for k, v in DECISION_RANK.items()}[min(ranks)]
        actions = [a for a in OrderedDict.fromkeys(r["action"] for r in live) if a != "none"]
        d["actions"] = actions
    return out


def table(header, body):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def render_use_case(reqs, use_case):
    body = []
    for d in (d for d in reqs.values() if d["use_case"] == use_case):
        rows = d["rows"]
        primary = [term_text(r) for r in rows if r["role"] == "primary" and r["decision"] != "rejected"]
        others = [f"{term_text(r)} ({r['role'].replace('_', '-')}{', rejected' if r['decision'] == 'rejected' else ''})"
                  for r in rows if r["role"] in ("alternative", "stand_in")]
        local = [term_text(r) for r in rows if r["role"] == "local"]
        gaps = [esc(r["notes"]) for r in rows if r["role"] == "gap" and r["notes"]]
        owners = list(OrderedDict.fromkeys(r["owner"] for r in rows if r["owner"].strip()))
        body.append([f"**{d['id']}**", esc(d["text"]), "<br>".join(primary) or "-", "<br>".join(others) or "-",
                     "<br>".join(local + gaps) or "-", STATUS_BADGE[d["status"]], DECISION_BADGE[d["decision"]],
                     ", ".join(d["actions"]) or "-", ", ".join(owners) or "-"])
    return table(["ID", "Requirement", "Fitting terms", "Stand-ins and alternatives", "Local terms needed / gap",
                  "Status", "Decision", "Action", "Owner"], body)


def render_usecases(reqs):
    body = []
    for uc, (acr, title) in USE_CASES.items():
        ids = [d["id"] for d in reqs.values() if d["use_case"] == uc]
        span = f"{ids[0]} to {ids[-1]}" if ids else "-"
        body.append([f"**{acr}**", title.split(' - ', 1)[1], ACRONYMS[acr], str(len(ids)), span])
    return table(["Acronym", "Use case", "Stands for", "Requirements", "IDs"], body)


def render_overview(reqs, rows):
    body = []
    for uc, (_, title) in USE_CASES.items():
        rs = [d for d in reqs.values() if d["use_case"] == uc]
        locals_ = {r["curie"] for r in rows if r["use_case"] == uc and r["role"] == "local"}
        body.append([title, str(len(rs))] + [str(sum(d["status"] == s for d in rs)) for s in ("covered", "partial", "gap")] +
                    [str(sum(d["decision"] == "open" for d in rs)), str(len(locals_))])
    total = list(reqs.values())
    body.append(["**All**", f"**{len(total)}**"] + [f"**{sum(d['status'] == s for d in total)}**" for s in ("covered", "partial", "gap")] +
                [f"**{sum(d['decision'] == 'open' for d in total)}**", f"**{len({r['curie'] for r in rows if r['role'] == 'local'})}**"])
    return table(["Use case", "Requirements", "Covered", "Partial", "Gap", "Open decisions", "Local terms"], body)


def render_gaps(reqs):
    items = []
    for d in reqs.values():
        if d["status"] == "covered":
            continue
        notes = [r["notes"] for r in d["rows"] if r["role"] in ("gap", "stand_in", "local") and r["notes"]]
        items.append((-STATUS_ORDER[d["status"]], d["id"], [f"**{d['id']}**", USE_CASES[d["use_case"]][1], esc(d["text"]),
                      STATUS_BADGE[d["status"]], ", ".join(d["actions"]) or "-", esc(notes[0]) if notes else "-"]))
    items.sort(key=lambda t: t[:2])
    return table(["ID", "Use case", "Requirement", "Status", "Action", "What is missing"], [t[2] for t in items])


def render_requests(reqs):
    """Requirements for which a term should be requested from an existing ontology (rows with action request_term)."""
    body = []
    for d in reqs.values():
        asks = [r for r in d["rows"] if r["action"] == "request_term" and r["decision"] != "rejected"]
        if not asks:
            continue
        closest = [term_text(r) for r in d["rows"] if r["curie"] and r["role"] in ("primary", "stand_in") and r["decision"] != "rejected"]
        notes = [esc(r["notes"]) for r in asks if r["notes"]]
        owners = list(OrderedDict.fromkeys(r["owner"] for r in asks if r["owner"].strip()))
        body.append([f"**{d['id']}**", esc(d["text"]), "<br>".join(closest) or "-", " ".join(notes) or "-", ", ".join(owners) or "-"])
    head = f"{len(body)} requirements are marked `request_term`: no suitable term exists, and the term should be proposed to an existing ontology."
    return head + "\n\n" + table(["ID", "Requirement", "Closest existing term", "Request", "Owner"], body)


def first_sentence(text):
    t = text.strip()
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    return m.group(1) if m else t


def owners_of(d):
    return list(OrderedDict.fromkeys(r["owner"] for r in d["rows"] if r["owner"].strip() and r["decision"] != "rejected"))


def render_decisions(reqs):
    items = [d for d in reqs.values() if d["decision"] == "open"]
    prio = lambda d: min((ACTION_PRIORITY[a] for a in d["actions"]), default=9)  # noqa: E731
    items.sort(key=lambda d: (0 if owners_of(d) else 1, prio(d), d["id"]))
    body = []
    for d in items:
        notes = [r["notes"] for r in d["rows"] if r["decision"] == "open" and r["notes"]]
        body.append([f"**{d['id']}**", USE_CASES[d["use_case"]][1], esc(d["text"]), ", ".join(owners_of(d)) or "-",
                     ", ".join(d["actions"]) or "-", esc(first_sentence(notes[0])) if notes else "-"])
    head = (f"{len(items)} requirements wait for a decision; {sum(1 for d in items if owners_of(d))} have a named owner "
            "and are listed first, then the ones that need a term request or a question to someone.")
    return head + "\n\n" + table(["ID", "Use case", "Requirement", "Owner", "Action", "Why it is open"], body)


def render_ontologies(reqs, rows):
    count = defaultdict(lambda: defaultdict(set))
    for r in rows:
        if r["curie"] and r["decision"] != "rejected":
            count[r["ontology"]][r["use_case"]].add(r["req_id"])
    order = sorted(count, key=lambda o: (o == "lodp", -len({q for s in count[o].values() for q in s}), o))
    header = ["Ontology"] + [USE_CASES[u][1] for u in USE_CASES] + ["All"]
    body = []
    for o in order:
        name, url, _, _ = ONTOLOGIES[o]
        link = f"[{o}]({url})" if url.startswith("http") else o
        cells = [str(len(count[o][u])) if count[o][u] else "-" for u in USE_CASES]
        body.append([f"{link}: {esc(name)}"] + cells + [str(len({q for s in count[o].values() for q in s}))])
    return table(header, body)


MISSING_BLOCKS = []


def render_all(text, rows):
    MISSING_BLOCKS.clear()
    reqs = requirements(rows)
    blocks = {"usecases": render_usecases(reqs), "overview": render_overview(reqs, rows), "decisions": render_decisions(reqs), "gaps": render_gaps(reqs), "requests": render_requests(reqs),
              "ontologies": render_ontologies(reqs, rows)}
    for uc in USE_CASES:
        blocks[f"terms:{uc}"] = render_use_case(reqs, uc)
    for name, content in blocks.items():
        pattern = re.compile(rf"(<!-- BEGIN:{re.escape(name)} -->\n)(?:.*?\n)?(<!-- END:{re.escape(name)} -->)", re.S)
        if not pattern.search(text):
            MISSING_BLOCKS.append(name)   # the block was removed from the document on purpose: leave it out
            continue
        text = pattern.sub(lambda m: m.group(1) + content + "\n" + m.group(2), text)
    return text


# --------------------------------------------------------------------------------------------- HTML dashboard
DASHBOARD_TEMPLATE = HERE / "dashboard_template.html"   # edit the page design there, not in this script


REPO = "pathway-lod/lod-pathways-community"   # the repository the dashboard talks to (a fork sets LOD_REPO)


def repo_slug():
    """owner/name of the GitHub repository. Fixed, so the generated dashboard does not depend on which clone built it."""
    import os

    return os.environ.get("LOD_REPO", REPO)


def html_data(rows):
    out = []
    for d in requirements(rows).values():
        rs = d["rows"]
        haystack = " ".join([d["id"], d["text"]] + [f"{r['curie']} {r['label']} {r['notes']} {r['ontology']} {r['owner']}" for r in rs]).lower()
        out.append({
            "id": d["id"], "use_case": d["use_case"], "use_case_title": USE_CASES[d["use_case"]][1], "text": d["text"],
            "status": d["status"], "decision": d["decision"], "actions": d["actions"], "owners": owners_of(d),
            "ontologies": list(OrderedDict.fromkeys(r["ontology"] for r in rs if r["ontology"])), "haystack": haystack,
            "issue_urls": list(OrderedDict.fromkeys(r["issue_url"] for r in rs if r["issue_url"].strip())),
            "rows": [{k: r[k] for k in ("row_id", "role", "curie", "label", "ontology", "iri", "coverage", "decision",
                                        "action", "used_in", "value_of", "notes", "owner", "issue_url", "verified")} for r in rs],
        })
    return {"repo": repo_slug(), "requirements": out}


def render_html(rows):
    import json

    data = json.dumps(html_data(rows), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return DASHBOARD_TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", data)


# --------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true", help="check term IDs in the Ontology Lookup Service")
    ap.add_argument("--update", action="store_true", help="write label, IRI and check date into the CSV (implies --online)")
    ap.add_argument("--reverify", action="store_true", help="with --update: refresh the check date of every term, not only of new or changed ones")
    ap.add_argument("--render", action="store_true", help="regenerate the tables in SPECIFICATION.md and the dashboard index.html")
    ap.add_argument("--check-render", action="store_true", help="exit with 2 if the generated files are stale")
    args = ap.parse_args(argv)

    header, rows = read_rows()
    errors, warnings = validate(header, rows)
    if not errors and (args.online or args.update):
        e, w, changed = online_check(rows, args.update, args.reverify)
        errors, warnings = errors + e, warnings + w
        if args.update:
            write_rows(rows)
            print(f"updated {changed} rows in {CSV_PATH.name}")
    stale = []
    if not errors:
        generated = []
        if MD_PATH.exists():
            generated.append((MD_PATH, render_all(MD_PATH.read_text(encoding="utf-8"), rows)))
        generated.append((HTML_PATH, render_html(rows)))
        for path, new in generated:
            old = path.read_text(encoding="utf-8") if path.exists() else None
            if new == old:
                if args.render:
                    print(f"{path.name} already up to date")
            elif args.render:
                path.write_text(new, encoding="utf-8")
                print(f"regenerated {path.name}")
            else:
                stale.append(path.name)
        if MISSING_BLOCKS:
            warnings.append(f"{MD_PATH.name} has no generated block for: {', '.join(MISSING_BLOCKS)} (skipped; add <!-- BEGIN:name --> and <!-- END:name --> lines to show it)")
        if stale:
            warnings.append(f"out of date: {', '.join(stale)}; run with --render")

    print(f"{len(rows)} rows, {len({r['req_id'] for r in rows})} requirements, {len(errors)} errors, {len(warnings)} warnings")
    for e in errors:
        print("error:", e)
    for w in warnings:
        print("warning:", w)
    if not errors:
        reqs = requirements(rows)
        print({s_: sum(d['status'] == s_ for d in reqs.values()) for s_ in ("covered", "partial", "gap")},
              "| open decisions:", sum(d["decision"] == "open" for d in reqs.values()))
    if errors:
        return 1
    return 2 if (stale and args.check_render) else 0


if __name__ == "__main__":
    sys.exit(main())
