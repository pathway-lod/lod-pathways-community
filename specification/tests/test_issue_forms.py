"""
Checks that the GitHub issue forms in .github/ISSUE_TEMPLATE/ follow GitHub's form schema and that the
fields used by the dashboard (prefilled links) and by apply_issue.py (labels read from the form) exist.
Needs PyYAML; the tests are skipped when it is not installed.
"""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import apply_issue as ai  # noqa: E402
import check_terms as ct  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

FORMS = HERE.parent.parent / ".github" / "ISSUE_TEMPLATE"
TYPES = {"markdown", "textarea", "input", "dropdown", "checkboxes"}


@unittest.skipIf(yaml is None, "PyYAML is not installed")
class IssueForms(unittest.TestCase):
    def forms(self):
        return {f.name: yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted(FORMS.glob("*.yml")) if f.name != "config.yml"}

    def test_every_form_follows_the_schema(self):
        forms = self.forms()
        self.assertGreaterEqual(len(forms), 3)
        for name, d in forms.items():
            with self.subTest(name):
                for key in ("name", "description", "body"):
                    self.assertIn(key, d)
                ids = []
                for item in d["body"]:
                    self.assertIn(item["type"], TYPES)
                    attrs = item.get("attributes", {})
                    if item["type"] == "markdown":
                        self.assertTrue(attrs.get("value"))
                        continue
                    self.assertTrue(attrs.get("label"))
                    if item["type"] == "dropdown":
                        opts = attrs["options"]
                        self.assertTrue(opts)
                        self.assertEqual(len(opts), len(set(opts)))
                    if item["type"] == "checkboxes":
                        self.assertTrue(attrs["options"])
                    if "id" in item:
                        self.assertRegex(item["id"], r"^[A-Za-z0-9_-]+$")
                        ids.append(item["id"])
                self.assertEqual(len(ids), len(set(ids)), "duplicate field ids")

    def test_dashboard_prefill_fields_exist(self):
        forms = self.forms()
        for name in ("requirement-discussion.yml", "term-suggestion.yml"):
            ids = [i.get("id") for i in forms[name]["body"]]
            for field in ("req_id", "requirement"):
                self.assertIn(field, ids, f"{name} lacks the field '{field}' that the dashboard fills in")

    def test_term_suggestion_labels_match_what_apply_issue_reads(self):
        form = self.forms()["term-suggestion.yml"]
        labels = {i["attributes"]["label"] for i in form["body"] if i["type"] != "markdown"}
        for needed in ("Term ID", "Ontology", "How well does it fit?", "Why this term"):
            self.assertIn(needed, labels)
        roles = next(i for i in form["body"] if i.get("id") == "role")["attributes"]["options"]
        for option in roles:
            self.assertTrue(any(option.lower().startswith(k) for k in ai.ROLE_MAP), f"apply_issue cannot read the fit '{option}'")

    def test_every_ontology_option_resolves_to_a_known_ontology(self):
        form = self.forms()["term-suggestion.yml"]
        options = next(i for i in form["body"] if i.get("id") == "ontology")["attributes"]["options"]
        for option in options:
            code = ai.ONTOLOGY_MAP.get(option.split(" (")[0].strip(), option.split(" (")[0].strip())
            self.assertTrue(code is None or code in ct.ONTOLOGIES, f"'{option}' is not a known ontology code")

    def test_use_case_dropdown_matches_the_use_cases_of_the_specification(self):
        form = self.forms()["new-requirement.yml"]
        options = next(i for i in form["body"] if i.get("id") == "use_case")["attributes"]["options"]
        self.assertEqual(options, [title for _, title in ct.USE_CASES.values()])

    def test_labels_exist_in_the_label_list_of_sync_issues(self):
        import sync_issues as si
        for form in self.forms().values():
            for label in form.get("labels", []):
                self.assertIn(label, si.LABEL_COLORS, f"label '{label}' is not created by sync_issues.py --labels-only")


if __name__ == "__main__":
    unittest.main(verbosity=2)
