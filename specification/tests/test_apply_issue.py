"""
Tests for apply_issue.py (the script behind the workflow that turns issue labels into changes of the CSV).
Run from the specification folder:   python -m unittest discover -s tests -v

Every test works on a temporary copy of ontology_terms.csv and feeds the script a GitHub event file.
The issue texts are examples written for these tests.
"""

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import apply_issue as ai  # noqa: E402
import check_terms as ct  # noqa: E402

FORM = """### Requirement ID

PMN-03

### Requirement

Experimental evidence, not further specified (EV-EXP)

### Term ID

{term}

### Ontology

{ontology}

### How well does it fit?

{fit}

### Why this term

{why}

### Checks

- [x] The term exists in the Ontology Lookup Service, or a link to its source is given above
- [ ] I volunteer to follow this suggestion up (assign the issue to me)
"""


def event(label, title, body="", number=42, pull_request=False):
    issue = {"number": number, "title": title, "body": body, "html_url": f"https://github.com/o/r/issues/{number}"}
    if pull_request:
        issue["pull_request"] = {"url": f"https://api.github.com/repos/o/r/pulls/{number}"}
    return {"action": "labeled", "label": {"name": label}, "issue": issue}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.csv = self.tmp / "ontology_terms.csv"
        shutil.copy(ct.CSV_PATH, self.csv)
        self.cwd = Path.cwd()
        import os
        os.chdir(self.tmp)               # apply_issue_summary.txt is written to the current folder

    def tearDown(self):
        import os
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp)

    def run_event(self, ev, dry=False):
        f = self.tmp / "event.json"
        f.write_text(json.dumps(ev), encoding="utf-8")
        args = [str(f), "--csv", str(self.csv)] + (["--dry-run"] if dry else [])
        return ai.main(args)

    def rows(self):
        return list(csv.DictReader(open(self.csv, encoding="utf-8")))


class Decisions(Base):
    def test_agreed_sets_the_decision_of_all_live_rows(self):
        before = [r for r in self.rows() if r["req_id"] == "PMN-07"]
        self.assertTrue(any(r["decision"] == "open" for r in before))
        self.assertEqual(self.run_event(event("decision:agreed", "[PMN-07] Discussion: computational evidence")), 0)
        after = [r for r in self.rows() if r["req_id"] == "PMN-07"]
        self.assertEqual({r["decision"] for r in after}, {"agreed"})
        self.assertTrue((self.tmp / "apply_issue_summary.txt").exists())

    def test_other_requirements_are_untouched(self):
        other_before = [r["decision"] for r in self.rows() if r["req_id"] != "PMN-07"]
        self.run_event(event("decision:agreed", "[PMN-07] Discussion"))
        self.assertEqual([r["decision"] for r in self.rows() if r["req_id"] != "PMN-07"], other_before)

    def test_rejected_rows_stay_rejected(self):
        # BGC-11 has a rejected alternative (GENEPIO:0100602)
        self.run_event(event("decision:agreed", "[BGC-11] Discussion"))
        rejected = [r for r in self.rows() if r["req_id"] == "BGC-11" and r["curie"] == "GENEPIO:0100602"]
        self.assertEqual(rejected[0]["decision"], "rejected")

    def test_dry_run_writes_nothing(self):
        before = self.csv.read_text(encoding="utf-8")
        self.run_event(event("decision:agreed", "[PMN-07] Discussion"), dry=True)
        self.assertEqual(self.csv.read_text(encoding="utf-8"), before)
        self.assertFalse((self.tmp / "apply_issue_summary.txt").exists())

    def test_unknown_decision_is_refused(self):
        before = self.csv.read_text(encoding="utf-8")
        self.assertEqual(self.run_event(event("decision:maybe", "[PMN-07] Discussion")), 1)
        self.assertEqual(self.csv.read_text(encoding="utf-8"), before)

    def test_rejecting_a_suggestion_rejects_only_that_term(self):
        body = FORM.format(term="ECO:0007631", ontology="ECO (evidence)", fit="Alternative (partial fit)", why="x")
        self.run_event(event("decision:rejected", "[PMN-07] Suggested term: ECO:0007631", body))
        rows = {r["curie"]: r["decision"] for r in self.rows() if r["req_id"] == "PMN-07"}
        self.assertEqual(rows["ECO:0007631"], "rejected")
        self.assertNotEqual(rows["ECO:0007668"], "rejected")


class IgnoredEvents(Base):
    def test_unrelated_labels_pull_requests_and_missing_ids_do_nothing(self):
        before = self.csv.read_text(encoding="utf-8")
        for ev in (event("bug", "[PMN-07] Discussion"),
                   event("decision:agreed", "[PMN-07] A pull request", pull_request=True),
                   event("decision:agreed", "A title without a requirement ID"),
                   event("decision:agreed", "[ZZZ-99] Unknown requirement")):
            self.run_event(ev)
        self.assertEqual(self.csv.read_text(encoding="utf-8"), before)


class AcceptTerm(Base):
    def suggestion(self, **kw):
        values = dict(term="ECO:0000363", ontology="ECO (evidence)", fit="Alternative (partial fit)",
                      why="Computational inference used in automatic assertion.")
        values.update(kw)
        return event("accept-term", "[PMN-03] Suggested term: ECO:0000363", FORM.format(**values))

    def test_adds_a_row_to_the_requirement(self):
        n_before = len(self.rows())
        self.assertEqual(self.run_event(self.suggestion()), 0)
        rows = self.rows()
        self.assertEqual(len(rows), n_before + 1)
        new = rows[-1]
        self.assertEqual((new["req_id"], new["curie"], new["ontology"], new["role"], new["coverage"], new["decision"]),
                         ("PMN-03", "ECO:0000363", "ECO", "alternative", "partial", "proposed"))
        self.assertEqual(new["requirement"], next(r["requirement"] for r in rows if r["req_id"] == "PMN-03"))
        self.assertIn("issue #42", new["source"])
        self.assertTrue(new["issue_url"].endswith("/issues/42"))
        self.assertEqual(ct.validate(*ct.read_rows(self.csv))[0], [])

    def test_best_fit_and_stand_in_map_to_role_and_coverage(self):
        self.run_event(self.suggestion(term="ECO:0007631", fit="Best fit (exact)"))
        self.assertEqual((self.rows()[-1]["role"], self.rows()[-1]["coverage"]), ("primary", "exact"))
        self.run_event(self.suggestion(term="ECO:0000352", fit="Stand-in (used for lack of a better term)"))
        self.assertEqual((self.rows()[-1]["role"], self.rows()[-1]["coverage"]), ("stand_in", "partial"))

    def test_ontology_is_found_from_the_prefix_when_the_dropdown_says_other(self):
        self.run_event(self.suggestion(term="PO:0025034", ontology="Other"))
        self.assertEqual(self.rows()[-1]["ontology"], "PO")

    def test_term_already_listed_is_refused(self):
        n = len(self.rows())
        self.run_event(self.suggestion(term="ECO:0000006"))      # PMN-03's primary term
        self.assertEqual(len(self.rows()), n)

    def test_hostile_text_cannot_break_the_csv(self):
        why = "first line\n| fake | table |\n" + "A" * 2000 + '\n"quote,comma,\n'
        self.run_event(self.suggestion(why=why))
        new = self.rows()[-1]
        self.assertNotIn("\n", new["notes"])
        self.assertNotIn("|", new["notes"])
        self.assertLessEqual(len(new["notes"]), ai.MAX_FIELD + 40)
        self.assertEqual(ct.validate(*ct.read_rows(self.csv))[0], [])

    def test_invalid_term_ids_are_refused(self):
        n = len(self.rows())
        for bad in ("ECO:1; rm -rf /", "not a term", "", "http://example.org/x", "FAKE:0000001"):
            with self.subTest(bad):
                self.run_event(self.suggestion(term=bad, ontology="Other"))
                self.assertEqual(len(self.rows()), n)

    def test_accept_term_on_a_plain_discussion_is_refused(self):
        n = len(self.rows())
        self.assertEqual(self.run_event(event("accept-term", "[PMN-03] Discussion: no form fields", "Just a comment.")), 1)
        self.assertEqual(len(self.rows()), n)


class FormParsing(unittest.TestCase):
    def test_parse_form_and_empty_fields(self):
        form = ai.parse_form("### A\n\nvalue a\n\n### B\n\n_No response_\n\n### C\n\nline 1\nline 2")
        self.assertEqual(form, {"A": "value a", "B": "", "C": "line 1\nline 2"})

    def test_requirement_of(self):
        self.assertEqual(ai.requirement_of("[PMN-03] Suggested term: ECO:0000314 (EV-EXP)"), "PMN-03")
        self.assertEqual(ai.requirement_of("Discussion about PO-12 and BGC-01"), "PO-12")
        self.assertIsNone(ai.requirement_of("No identifier, only EV-EXP and ECO:0000314"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
