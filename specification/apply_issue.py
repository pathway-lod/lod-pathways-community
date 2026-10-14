#!/usr/bin/env python3
"""
Apply the outcome of a GitHub issue to ontology_terms.csv. Used by the workflow .github/workflows/issue-to-csv.yml,
which runs when a maintainer puts a label on an issue; it can also be run by hand on a saved event file.

  python apply_issue.py event.json            # reads the GitHub event (issues: labeled) from a file
  python apply_issue.py event.json --dry-run  # shows what would change, writes nothing

Labels that trigger a change (only people with triage or write access can set labels, so this is the gate):
  decision:agreed | decision:proposed | decision:open | decision:rejected
      sets `decision` on the rows of the requirement named in the issue title ([PMN-03] ...); rejected rows are left alone,
      and `decision:rejected` on a *term suggestion* issue rejects only the suggested term
  accept-term
      on a "Suggest an ontology term" issue: adds the suggested term as a new row of its requirement

The issue text is untrusted input: it is read from the event file, never put into a shell command, checked against
the lists of the specification (ontology prefixes, roles) and cut to one short line per field. The result is always
reviewed in a pull request before it reaches the main branch.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import check_terms as ct  # noqa: E402

REQ_IN_TITLE = re.compile(r"\b([A-Z]{2,4}-\d{2,})\b")
# dropdown text of the issue form -> (role, coverage)
ROLE_MAP = {"best fit": ("primary", "exact"), "alternative": ("alternative", "partial"), "stand-in": ("stand_in", "partial")}
# dropdown text of the issue form -> ontology code of the CSV
ONTOLOGY_MAP = {"PSI-MS": "MS", "PROV-O, SKOS or Dublin Core": None, "Other": None}
MAX_FIELD = 400


def parse_form(body):
    """GitHub issue forms render as '### Label' followed by the answer."""
    fields, current = {}, None
    for line in (body or "").replace("\r", "").split("\n"):
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = m.group(1)
            fields[current] = []
        elif current is not None:
            fields[current].append(line)
    clean = {k: "\n".join(v).strip() for k, v in fields.items()}
    return {k: ("" if v == "_No response_" else v) for k, v in clean.items()}


def one_line(text, limit=MAX_FIELD):
    t = re.sub(r"\s+", " ", (text or "").replace("|", "/")).strip()
    return t[:limit]


def requirement_of(title):
    m = REQ_IN_TITLE.search(title or "")
    return m.group(1) if m else None


def set_decision(rows, req_id, decision, term=None):
    changed = []
    for r in rows:
        if r["req_id"] != req_id or r["decision"] == "rejected":
            continue
        if term and r["curie"] != term:
            continue
        if r["decision"] != decision:
            r["decision"] = decision
            changed.append(r["row_id"])
    return changed


def add_term(rows, req_id, form, issue):
    term = form.get("Term ID", "").strip().split()[0] if form.get("Term ID", "").strip() else ""
    if not ct.CURIE_RE.match(term):
        raise ValueError(f"'{term}' is not a valid term ID (expected a CURIE such as ECO:0000314)")
    ont_text = form.get("Ontology", "")
    code = ont_text.split(" (")[0].strip()
    code = ONTOLOGY_MAP.get(code, code)
    prefix = term.split(":")[0]
    code = code if code in ct.ONTOLOGIES and ct.ONTOLOGIES[code][2] == prefix else next(
        (c for c, v in ct.ONTOLOGIES.items() if v[2] == prefix), None)
    if code is None:
        raise ValueError(f"no known ontology has the prefix '{prefix}'; add it to ONTOLOGIES in check_terms.py first")
    fit = form.get("How well does it fit?", "").lower()
    role, coverage = next((v for k, v in ROLE_MAP.items() if fit.startswith(k)), (None, None))
    if role is None:
        raise ValueError(f"cannot read the fit from '{fit}'")
    same = [r for r in rows if r["req_id"] == req_id]
    if not same:
        raise ValueError(f"requirement {req_id} does not exist")
    if any(r["curie"] == term for r in same):
        raise ValueError(f"{term} is already listed for {req_id}")
    template = same[0]
    new = dict(template)
    nid = max(int(r["row_id"][1:]) for r in rows if re.fullmatch(r"T\d+", r["row_id"])) + 1
    new.update({"row_id": f"T{nid:03d}", "role": role, "curie": term, "label": "", "ontology": code, "iri": "",
                "coverage": coverage, "decision": "proposed", "action": "review", "used_in": "", "value_of": "",
                "notes": one_line(form.get("Why this term", "")) + f" (suggested in issue #{issue['number']})",
                "source": f"issue #{issue['number']}", "owner": "", "issue_url": issue.get("html_url", ""), "verified": ""})
    rows.append(new)
    return new["row_id"], term


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("event", help="path of the GitHub event JSON")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--csv", default=str(ct.CSV_PATH))
    args = ap.parse_args(argv)

    event = json.loads(Path(args.event).read_text(encoding="utf-8"))
    issue, label = event.get("issue") or {}, (event.get("label") or {}).get("name", "")
    if "pull_request" in issue:
        print("pull request, ignored"); return 0
    req_id = requirement_of(issue.get("title"))
    kind = "decision" if label.startswith("decision:") else "accept" if label == "accept-term" else None
    if kind is None:
        print(f"label '{label}' does not trigger a change"); return 0
    if not req_id:
        print("no requirement ID such as [PMN-03] at the start of the title: nothing to do"); return 0

    path = Path(args.csv)
    header, rows = ct.read_rows(path)
    if not any(r["req_id"] == req_id for r in rows):
        print(f"requirement {req_id} is not in the CSV"); return 1
    form = parse_form(issue.get("body"))
    suggestion = "Term ID" in form

    if kind == "decision":
        decision = label.split(":", 1)[1]
        if decision not in ct.ENUMS["decision"]:
            print(f"unknown decision '{decision}'"); return 1
        term = None
        if suggestion and decision == "rejected":
            term = (form.get("Term ID", "").split() or [""])[0]
        changed = set_decision(rows, req_id, decision, term)
        summary = f"{req_id}: decision set to '{decision}' on {len(changed)} row(s)" + (f" (term {term})" if term else "")
    else:
        if not suggestion:
            print("accept-term works on 'Suggest an ontology term' issues only"); return 1
        try:
            row_id, term = add_term(rows, req_id, form, issue)
        except ValueError as e:
            print(f"refused: {e}"); return 1
        changed = [row_id]
        summary = f"{req_id}: term {term} added as {row_id}"

    errors, _ = ct.validate(header, rows)
    if errors:
        print("the change would make the CSV invalid:\n" + "\n".join(errors[:5])); return 1
    print(summary)
    if not changed:
        print("nothing changed"); return 0
    if not args.dry_run:
        ct.write_rows(rows, path)
        # the workflow reads this file to name the pull request
        Path("apply_issue_summary.txt").write_text(summary + f"\nIssue: {issue.get('html_url', '')}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
