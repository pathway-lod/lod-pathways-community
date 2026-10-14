# Ontology term specification: dashboard and discussion

This folder holds the specification of the ontology terms for predicted-pathway data, and a small web app to review and discuss it. The app has no server. It consists of:

- a **dashboard** (`index.html`), generated from the term table, which shows every requirement with its status, decision, owner and GitHub discussion;
- **GitHub issues** as the place where the discussion happens, created through three prefilled **issue forms**;
- **GitHub Actions** that check the files on every pull request, publish the dashboard with GitHub Pages, and turn a maintainer's label on an issue into a pull request that changes the term table.

The term table (`ontology_terms.csv`) stays the single source of truth. Everything else is either written text (`SPECIFICATION.md`) or generated from the table.

## What to do

### Contributors (any GitHub account)

1. Open the dashboard (published address: <https://pathway-lod.github.io/lod-pathways-community/> once Pages is set up; otherwise open `index.html` from a download).
2. Find the requirement with the search box or the filters (use case, status, decision, owner, action, ontology). Select its ID to see the candidate terms.
3. Choose one of the buttons:
   - **Open a discussion**: a question or comment about the requirement.
   - **Suggest a term**: a term ID, its ontology, how well it fits and why. The term should exist in the [Ontology Lookup Service](https://www.ebi.ac.uk/ols4/).
   - **Open the issue to comment or assign yourself**: appears when the requirement already has an issue.
4. To take a requirement on, tick the volunteering box of the form, or ask a maintainer to assign the issue. People with write access can assign themselves.
5. A new requirement is proposed with the form *Propose a new requirement* ([new issue](https://github.com/pathway-lod/lod-pathways-community/issues/new/choose)).

Issues need the label `ontology-terms` and the requirement ID at the start of the title (for example `[PMN-03]`). The forms set both.

### Maintainers

| Situation | Action |
|---|---|
| A question or comment | Answer in the issue. Assign the owner (the dashboard then shows the GitHub user next to the owners of the table). |
| A decision is reached | Put the label `decision:agreed` (or `decision:rejected`, `decision:proposed`, `decision:open`) on the issue. The workflow opens a pull request that sets `decision` for the requirement. |
| A suggested term is accepted | Put the label `accept-term` on its issue. The workflow adds the term as a new row of its requirement (role and coverage from the form) and opens a pull request. |
| A suggested term is rejected | Put the label `decision:rejected` on its issue. Only the suggested term is marked rejected. |
| Review the pull request | Check the changed rows in `ontology_terms.csv` and merge. The dashboard and the tables of `SPECIFICATION.md` are regenerated in the same pull request. |
| Edit the table by hand | Edit `ontology_terms.csv` (also possible in the GitHub web editor), run `python check_terms.py --update --render`, commit all changed files. |

Only people with triage or write access can set labels, so only they can trigger a change of the table. The issue text is read as data by the script: it is checked against the lists of the specification and cut to one short line per field, and the pull request is reviewed before anything reaches the main branch.

### One-time setup (repository administrators)

Do these after this branch has been merged into the default branch (`main`): GitHub reads issue forms and runs the publishing workflow from there only.

1. **Publish the dashboard with GitHub Pages.**
   1. Open the repository on GitHub and select **Settings**.
   2. In the left sidebar, select **Pages**.
   3. Under **Build and deployment**, set **Source** to **GitHub Actions**. (Not "Deploy from a branch".)
   4. Open the **Actions** tab, select **Publish the specification dashboard** in the left list, then **Run workflow** and confirm (this first run does not wait for a change).
   5. When the run is green, the address is shown in the run summary and under Settings → Pages: <https://pathway-lod.github.io/lod-pathways-community/>. Later runs happen automatically on every push to `main` that changes `specification/`.
   6. If the run waits for approval, open it and approve the `github-pages` environment. If the Pages setting is missing, an organisation owner has to allow Pages for the organisation.
2. **Allow the workflow to open pull requests.** Settings → **Actions** → **General** → *Workflow permissions*: select **Read and write permissions** and tick **Allow GitHub Actions to create and approve pull requests**, then save.
3. **Create the labels** that the forms and workflows use. Either log in with `gh auth login` and run `python sync_issues.py --labels-only`, or create them by hand under Issues → Labels → New label: `ontology-terms`, `term-suggestion`, `new-requirement`, `term-request`, `question`, `accept-term`, and one `decision:` label each for `agreed`, `proposed`, `open`, `rejected`.
4. **Check the forms.** Open <https://github.com/pathway-lod/lod-pathways-community/issues/new/choose>: the three forms should be listed. Open the dashboard, select a requirement and use **Open a discussion** to confirm that the form arrives filled in.
5. **Try the loop once.** Create an issue with a form, put `decision:agreed` on it, and check that a pull request appears within a minute or two. Close the test pull request and issue afterwards.

## Files

| File | What it is |
|---|---|
| [`SPECIFICATION.md`](SPECIFICATION.md) | The written specification; the tables in it are generated from the CSV. |
| [`ontology_terms.csv`](ontology_terms.csv) | The term table: one row per requirement and candidate term. Source of truth. |
| [`index.html`](index.html) | The dashboard, generated; do not edit by hand. |
| [`dashboard_template.html`](dashboard_template.html) | The design and the code of the dashboard; edit this to change how it looks or works. |
| [`check_terms.py`](check_terms.py) | Validates the CSV, fills in term labels from the Ontology Lookup Service, regenerates the tables and the dashboard. |
| [`sync_issues.py`](sync_issues.py) | Opens issues from the command line and creates the labels. Dry run unless `--create` is given. |
| [`apply_issue.py`](apply_issue.py) | Applies an issue label to the CSV; run by the workflow `issue-to-csv.yml`. |
| [`tests/`](tests/) | Tests of the issue script and of the issue forms. |
| [`../.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/) | The three issue forms. |
| [`../.github/workflows/`](../.github/workflows/) | The three workflows (below). |

## Workflows

| Workflow | Runs when | What it does |
|---|---|---|
| `specification-checks.yml` | pull request or push that changes the specification, the shapes or the templates | Validates the CSV, checks that the generated files are up to date, runs the tests of the issue script, the issue forms and the shapes, and validates the sample graph. |
| `specification-pages.yml` | push to `main` that changes `specification/`, or by hand | Publishes the dashboard and the term table with GitHub Pages. |
| `issue-to-csv.yml` | a label is put on an issue | For `decision:*` and `accept-term`: changes the CSV, looks the term up, regenerates the files, runs the checks, opens a pull request and comments on the issue. Otherwise comments why nothing changed. |

## How the dashboard gets the discussion

The page reads the public issues of the repository with the label `ontology-terms` from the GitHub API when it is opened, and matches each issue to a requirement by the ID in its title. Pull requests and issues without a known ID are ignored. The numbers are always current and need no regeneration.

## Local use

```bash
# from this folder, with the environment of ../shape_constraints
python check_terms.py                       # validate the CSV (no network)
python check_terms.py --update --render     # look up new terms, regenerate SPECIFICATION.md and index.html
python check_terms.py --check-render        # fail when generated files are stale (used by the workflow)
python sync_issues.py                       # dry run: which issues would be opened
python sync_issues.py --labels-only         # create the labels (needs gh auth login)
python -m unittest discover -s tests        # tests (the issue-form tests need PyYAML)
```

Open `index.html` directly in a browser to look at it. Discussion data needs internet access and a repository that is public.

## Known limits

- **Rate limit.** GitHub allows 60 anonymous API requests per hour and address. Past that, the dashboard shows a message and the buttons keep working.
- **Pull requests made by the workflow do not start the checks workflow** (a GitHub rule for pull requests opened with the built-in token). The workflow runs the same checks itself before opening the pull request.
- **Self-assignment** needs write access. Everyone else comments, and a maintainer assigns.
- **The label workflow leaves a link instead of a pull request** when the organisation switches off "Allow GitHub Actions to create and approve pull requests" (the repository option is then greyed out). The issue gets a comment with a link that opens the pull request from the prepared branch in one click; an organisation owner can enable the option at Organization settings > Actions > General to make it automatic.
- **"Get Pages site failed ... Not Found"** in the publishing workflow means that Pages is not set up with the source *GitHub Actions* (Settings > Pages). Set it, then open the failed run under the Actions tab and choose **Re-run all jobs**, or use **Run workflow**. The workflow now skips the deployment with a warning instead of failing while the setting is missing.
- **Forms and workflows** work from the default branch only; until the merge, the dashboard buttons open the forms on a branch where they are not available.
- **A private repository** cannot be read by the dashboard without a login. Pages for a private repository depends on the GitHub plan.
- **A fork** sets the environment variable `LOD_REPO=owner/name` when regenerating, so that the dashboard talks to the fork.
