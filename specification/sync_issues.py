#!/usr/bin/env python3
"""
Open one GitHub issue per requirement that needs a term request or a question, and write the
issue URL back into the `issue_url` column of ontology_terms.csv.

  python sync_issues.py                  # DRY RUN: list the issues that would be created (the default)
  python sync_issues.py --show-body      # ... and print each issue text
  python sync_issues.py --select open    # choose other requirements (see below)
  python sync_issues.py --create         # really create them (needs `gh auth login`)
  python sync_issues.py --labels-only    # only create all labels used by the forms and workflows (needs `gh auth login`)

Which requirements get an issue (--select):
  requests  action is `request_term` or `ask`: a term to request from an ontology, or a question to a named person (default)
  open      every requirement whose decision is `open`
  all       every requirement that is not fully covered or has an open decision

A requirement is skipped when one of its rows already has an `issue_url`, so the script can be run again
after the CSV changed. Labels (`ontology-terms`, `uc:<use case>`, `term-request`, `question`) are created when missing.
GitHub Discussions cannot be created with the `gh` command line; use issues, or open a discussion by hand and paste
its link into `issue_url`.
"""

import argparse
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import check_terms as ct  # noqa: E402

LABEL_COLORS = {   # every label that the issue forms, the workflows and this script use
    "ontology-terms": "0e8a16", "term-suggestion": "1d76db", "new-requirement": "5319e7", "term-request": "d93f0b", "question": "fbca04",
    "accept-term": "0e8a16", "decision:agreed": "0e8a16", "decision:proposed": "1d76db", "decision:open": "fbca04", "decision:rejected": "b60205",
}
ALL_LABELS = list(LABEL_COLORS)


def repo_from_git():
    url = subprocess.run(["git", "-C", str(HERE), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        sys.exit(f"cannot find the GitHub repository in the git remote '{url}'; pass --repo owner/name")
    return m.group(1)


def select(reqs, mode):
    out = []
    for d in reqs.values():
        if any(r["issue_url"].strip() for r in d["rows"]):
            continue
        live = [r for r in d["rows"] if r["decision"] != "rejected"]
        if mode == "requests":
            ok = any(r["action"] in ("request_term", "ask") for r in live)
        elif mode == "open":
            ok = d["decision"] == "open"
        else:
            ok = d["decision"] == "open" or d["status"] != "covered"
        if ok:
            out.append(d)
    return out


def labels_for(d):
    labels = ["ontology-terms", f"uc:{d['use_case']}"]
    actions = {r["action"] for r in d["rows"] if r["decision"] != "rejected"}
    if "request_term" in actions:
        labels.append("term-request")
    if "ask" in actions:
        labels.append("question")
    return labels


def issue_body(d):
    title = ct.USE_CASES[d["use_case"]][1]
    owners = ct.owners_of(d)
    lines = [f"**Requirement {d['id']}** ({title})", "", d["text"], "",
             f"Status: **{d['status']}**. Decision: **{d['decision']}**. Owner: {', '.join(owners) or 'nobody yet'}.", "",
             "| Role | Term | Ontology | Coverage | Decision | Action |", "|---|---|---|---|---|---|"]
    for r in d["rows"]:
        term = ct.term_text(r) or "(no term)"
        lines.append(f"| {r['role'].replace('_', '-')} | {term} | {r['ontology'] or '-'} | {r['coverage']} | {r['decision']} | {r['action']} |")
    notes = [f"- {r['notes']}" for r in d["rows"] if r["notes"]]
    if notes:
        lines += ["", "Notes:", *notes]
    lines += ["", "The terms are tracked in `specification/ontology_terms.csv` and described in `specification/SPECIFICATION.md`. "
              "Record the outcome in the `decision` column of the CSV (and re-run `check_terms.py --update --render`) when this issue is resolved."]
    return "\n".join(lines)


def gh(*args, input_text=None):
    return subprocess.run(["gh", *args], input=input_text, capture_output=True, text=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--select", choices=["requests", "open", "all"], default="requests")
    ap.add_argument("--create", action="store_true", help="create the issues (default: dry run)")
    ap.add_argument("--yes", action="store_true", help="allow creating more than 10 issues at once")
    ap.add_argument("--show-body", action="store_true")
    ap.add_argument("--repo", help="owner/name; default: taken from the git remote 'origin'")
    ap.add_argument("--labels-only", action="store_true", help="create the labels used by the issue forms and workflows, and stop")
    args = ap.parse_args(argv)

    if args.labels_only:
        repo = args.repo or repo_from_git()
        if gh("api", "user", "--jq", ".login").returncode != 0:
            sys.exit("the GitHub CLI is not logged in, or its token is invalid: run `gh auth login`")
        for label in ALL_LABELS:
            res = gh("label", "create", label, "--repo", repo, "--color", LABEL_COLORS[label], "--force")
            print(("created/updated " if res.returncode == 0 else "failed: ") + label + (f" ({res.stderr.strip()})" if res.returncode else ""))
        return 0

    header, rows = ct.read_rows()
    errors, _ = ct.validate(header, rows)
    if errors:
        sys.exit("fix the CSV first (python check_terms.py):\n" + "\n".join(errors[:5]))
    reqs = ct.requirements(rows)
    todo = select(reqs, args.select)
    repo = args.repo or repo_from_git()
    print(f"{len(todo)} requirement(s) selected with --select {args.select} for {repo}"
          f" ({'CREATING' if args.create else 'dry run, nothing is created'})")
    for d in todo:
        print(f"\n[{d['id']}] {d['text'][:110]}\n    labels: {', '.join(labels_for(d))}")
        if args.show_body:
            print("    " + issue_body(d).replace("\n", "\n    "))
    if not args.create or not todo:
        if not args.create and todo:
            print("\nNothing was created. Re-run with --create (after `gh auth login`) to open these issues.")
        return 0

    if len(todo) > 10 and not args.yes:
        sys.exit(f"{len(todo)} issues is a lot to open at once; check the list above and add --yes if you mean it")
    # `gh auth status` succeeds even when the stored token is invalid, so test the token with a real call
    if gh("api", "user", "--jq", ".login").returncode != 0:
        sys.exit("the GitHub CLI is not logged in, or its token is invalid: run `gh auth login`")
    for label in {l for d in todo for l in labels_for(d)}:
        color = LABEL_COLORS.get(label, "5319e7")
        gh("label", "create", label, "--repo", repo, "--color", color, "--force")
    created = OrderedDict()
    for d in todo:
        title = f"[{d['id']}] {d['text']}"[:120]
        cmd = ["issue", "create", "--repo", repo, "--title", title, "--body-file", "-"]
        for label in labels_for(d):
            cmd += ["--label", label]
        res = gh(*cmd, input_text=issue_body(d))
        if res.returncode != 0:
            print(f"failed for {d['id']}: {res.stderr.strip()}", file=sys.stderr)
            continue
        url = res.stdout.strip().splitlines()[-1]
        created[d["id"]] = url
        print(f"created {d['id']}: {url}")
    for r in rows:
        if r["req_id"] in created:
            r["issue_url"] = created[r["req_id"]]
    ct.write_rows(rows)
    print(f"wrote {len(created)} issue link(s) into {ct.CSV_PATH.name}; run check_terms.py --render to refresh the tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
