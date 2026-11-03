# Ontology term specification: dashboard and discussion

This folder holds the specification of the ontology terms for predicted-pathway data, and a small web app to review and discuss it. The app has no server. It consists of:

- a **dashboard** (`index.html`), generated from the term table, which shows every requirement with its status, decision, owner and GitHub discussion;
- **GitHub issues** as the place where the discussion happens, created through three prefilled **issue forms**;
- **GitHub Actions** that check the files on every pull request, publish the dashboard with GitHub Pages, and turn a maintainer's label on an issue into a pull request that changes the term table.

The term table (`ontology_terms.csv`) stays the single source of truth. Everything else is either written text (`SPECIFICATION.md`) or generated from the table.

## What to do

### Contributors (any GitHub account)

1. Open the dashboard (published address: <https://pathway-lod.github.io/lod-pathways-community/> once Pages is set up; otherwise open `index.html` from a download).
2. The charts are in a collapsed "Charts" bar under the summary cards (a link with `#charts=1` opens it). They show how many distinct terms each ontology (and the local placeholder vocabulary `lodp`) contributes to the list, optionally split by use case. It follows the filters, and selecting a bar filters the requirements by that ontology; the table view below the chart gives the same numbers as text. A second chart shows the coverage: requirements by use case (covered, partial, gap) or terms by ontology (exact fit, partial fit, no fit, the last being the local placeholder terms); selecting a bar filters the list.
   Find the requirement with the search box or the filters (use case, status, decision, owner, action, ontology). Select its ID to see the candidate terms.
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
| Edit the table by hand | Edit `ontology_terms.csv`, run `python check_terms.py --update --render`, commit all changed files. In the GitHub web editor, only the CSV needs to be edited: on a pull request from this repository the checks workflow regenerates `SPECIFICATION.md` and `index.html` and commits them to the branch. |

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
| [`ols_search_phrases.csv`](ols_search_phrases.csv) | The phrases that were searched in the Ontology Lookup Service to find the first candidate terms (reconstructed from the working session; not the final terms). |
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
| `specification-checks.yml` | pull request or push that changes the specification, the shapes or the templates | On a pull request from this repository: regenerates the generated files from the CSV and commits them to the branch when they differ. Then validates the CSV, checks that the generated files are up to date, runs the tests of the issue script, the issue forms and the shapes, and validates the sample graph. |
| `specification-pages.yml` | push to `main` that changes `specification/`, or by hand | Regenerates the dashboard and the tables from the CSV, so that the published page always follows the term table, then publishes them with GitHub Pages. |
| `issue-to-csv.yml` | a label is put on an issue | For `decision:*` and `accept-term`: changes the CSV, looks the term up, regenerates the files, runs the checks, opens a pull request and comments on the issue. Otherwise comments why nothing changed. |

## How the dashboard gets the discussion

The page reads the public issues of the repository with the label `ontology-terms` from the GitHub API when it is opened, and matches each issue to a requirement by the ID in its title. Pull requests and issues without a known ID are ignored. The numbers are always current and need no regeneration.

## How the terms were found and checked

### Finding the candidate terms

For each requirement, candidate terms were searched in the [Ontology Lookup Service](https://www.ebi.ac.uk/ols4/) (OLS4) with its search API (`https://www.ebi.ac.uk/ols4/api/search`). The query was a free-text phrase taken from the requirement (for example "co-expression", "mass error" or "area under the ROC curve"), usually restricted to one ontology (ECO, PSI-MS, EDAM, SIO, STATO, SO, CHEMINF, CHMO, SWO, AIO, OBI and others), and the first four to six hits (identifier, label and sometimes the definition) were read. The searches were typed in throwaway scripts that were **not kept**. The phrases below were reconstructed afterwards from the log of the working session: 223 distinct phrases in 12 rounds, in the order they were run (a phrase that was searched again in a later round is listed once). They are the starting point of the work and **do not have to match the final terms**: terms were also taken from other sources (the BioCyc evidence ontology page for the PlantCyc evidence codes, the papers and supplementary tables of the pilot data sets), and many searched phrases led to no term or to a term that was not used. The same table is in [`ols_search_phrases.csv`](ols_search_phrases.csv).

The hits were then chosen by reading the labels and definitions, and the role (primary, alternative, stand-in, local, gap) and the coverage (exact, partial, none) of each term were set by hand. The table is then **reviewed manually** by the project members and **revised by the community** through the dashboard: discussions and term suggestions are GitHub issues, decisions are labels on the issues, and every change to the table is a reviewed pull request.

### What `check_terms.py` does

[`check_terms.py`](check_terms.py) keeps the term table consistent and generates everything that is derived from it. It needs only the Python standard library (`requests` for the online check, `rdflib` optionally for the labels of local terms).

| Command | What it does |
|---|---|
| `python check_terms.py` | **Validates** `ontology_terms.csv` without network access: a unique `row_id`; a requirement ID of the form `PMN-03` that matches its use case; allowed values for `element_type`, `role`, `coverage`, `decision`, `action` and `used_in`; a valid CURIE whose prefix belongs to the named ontology, and an ontology that is in the list of known ones; the rules between the columns (a gap row has no term and coverage `none`; a local term goes with the ontology `lodp` and coverage `none`; primary and alternative terms have coverage `exact` or `partial`; `ask` needs an owner; `value_of` points to a term that is in the table; no term twice for one requirement). Some inconsistencies are only warnings (for example a stand-in that is not partial, or a local term not yet defined in `shape_constraints/vocab/lodp.ttl`). |
| `--online` | After a successful validation, looks every term up in OLS (exact search on the `obo_id`, taking the hit of the ontology that matches the prefix, preferring terms that are not obsolete). It is an **error** when a term is not found or is obsolete, and a warning when the stored label differs from the one in OLS. Ontologies that are not in OLS (PROV, SKOS, DCTERMS, RDF, WikiPathways, identifiers.org and the local vocabulary `lodp`) are not looked up. |
| `--update` | Like `--online`, and writes the label, the IRI and the check date (`verified`) of new or changed terms into the CSV. Local `lodp` terms get their IRI from the local namespace and their label from `lodp.ttl`. `--reverify` refreshes the date of every term. |
| `--render` | Regenerates the tables of `SPECIFICATION.md` (between its `BEGIN`/`END` markers) and the dashboard `index.html` from the CSV. |
| `--check-render` | Exits with code 2 when a generated file is out of date. Exit code 1 means errors, 0 means none. |

The usual command after editing the table is `python check_terms.py --update --render`. The workflows of this repository run it for pull requests and for term suggestions that are accepted with a label, and the publishing workflow runs `--render` before the dashboard is deployed.

### Phrases used to search OLS

<details>
<summary>Table of the 223 search phrases</summary>

| Round | Topic | Search phrase | Ontology |
|---|---|---|---|
| 1 | evidence types, gene clusters, similarity | biosynthetic gene cluster | so |
| 1 | evidence types, gene clusters, similarity | gene cluster | so |
| 1 | evidence types, gene clusters, similarity | computational evidence used in automatic assertion | eco |
| 1 | evidence types, gene clusters, similarity | match to sequence model evidence | eco |
| 1 | evidence types, gene clusters, similarity | sequence similarity evidence | eco |
| 1 | evidence types, gene clusters, similarity | genomic context evidence | eco |
| 1 | evidence types, gene clusters, similarity | correlation evidence | eco |
| 1 | evidence types, gene clusters, similarity | expression pattern evidence | eco |
| 1 | evidence types, gene clusters, similarity | co-expression | eco |
| 1 | evidence types, gene clusters, similarity | mass spectrometry evidence | eco |
| 1 | evidence types, gene clusters, similarity | combinatorial computational and experimental evidence | eco |
| 1 | evidence types, gene clusters, similarity | author inference | eco |
| 1 | evidence types, gene clusters, similarity | curator inference | eco |
| 1 | evidence types, gene clusters, similarity | imported information | eco |
| 1 | evidence types, gene clusters, similarity | biosynthetic gene cluster | mibig |
| 1 | evidence types, gene clusters, similarity | percent identity | sio |
| 1 | evidence types, gene clusters, similarity | overlap | sio |
| 2 | evidence, paired omics, annotation tools | coexpression evidence | eco |
| 2 | evidence, paired omics, annotation tools | statistical association evidence | eco |
| 2 | evidence, paired omics, annotation tools | gene neighbors evidence used in automatic assertion | eco |
| 2 | evidence, paired omics, annotation tools | machine learning | eco |
| 2 | evidence, paired omics, annotation tools | inference from background scientific knowledge | eco |
| 2 | evidence, paired omics, annotation tools | genomic context evidence used in automatic assertion | eco |
| 2 | evidence, paired omics, annotation tools | Pearson correlation coefficient | stato |
| 2 | evidence, paired omics, annotation tools | Spearman | stato |
| 2 | evidence, paired omics, annotation tools | mutual rank | stato |
| 2 | evidence, paired omics, annotation tools | p-value | obi |
| 2 | evidence, paired omics, annotation tools | has version | swo |
| 2 | evidence, paired omics, annotation tools | software version | iao |
| 2 | evidence, paired omics, annotation tools | antiSMASH | edam |
| 2 | evidence, paired omics, annotation tools | gene cluster prediction | edam |
| 2 | evidence, paired omics, annotation tools | metabolic pathway prediction | edam |
| 2 | evidence, paired omics, annotation tools | tandem mass spectrometry | msio |
| 3 | paired omics | coexpression | eco |
| 3 | paired omics | gene expression correlation | eco |
| 3 | paired omics | correlation | eco |
| 3 | paired omics | statistical inference | eco |
| 3 | paired omics | network | eco |
| 3 | paired omics | clustering | eco |
| 3 | paired omics | mutual rank | all |
| 3 | paired omics | co-expression network | all |
| 3 | paired omics | gene-metabolite association | all |
| 3 | paired omics | correlation coefficient | stato |
| 3 | paired omics | association | sio |
| 3 | paired omics | cluster | edam |
| 3 | paired omics | gene-chemical association | sio |
| 3 | paired omics | chemical-gene association | sio |
| 3 | paired omics | has evidence | sio |
| 3 | paired omics | has value | sio |
| 3 | paired omics | refers to | sio |
| 3 | paired omics | p-value | sio |
| 3 | paired omics | gene | sio |
| 3 | paired omics | chemical entity | sio |
| 3 | paired omics | expression pattern evidence used in automatic assertion | eco |
| 3 | paired omics | clustering | edam |
| 3 | paired omics | gene expression correlation analysis | edam |
| 4 | gene clusters, evidence | gene cluster | edam |
| 4 | gene clusters, evidence | biosynthetic gene cluster | edam |
| 4 | gene clusters, evidence | secondary metabolite | edam |
| 4 | gene clusters, evidence | combinatorial computational evidence used in automatic assertion | eco |
| 4 | gene clusters, evidence | imported information used in automatic assertion | eco |
| 4 | gene clusters, evidence | sequence similarity evidence used in automatic assertion | eco |
| 4 | gene clusters, evidence | match to sequence model evidence used in automatic assertion | eco |
| 4 | gene clusters, evidence | has part | ro |
| 4 | gene clusters, evidence | overlaps | ro |
| 4 | gene clusters, evidence | percent identity | all |
| 4 | gene clusters, evidence | similarity score | sio |
| 5 | PlantCyc evidence codes | EV-EXP-IDA | eco |
| 5 | PlantCyc evidence codes | EV-EXP-IEP | eco |
| 5 | PlantCyc evidence codes | EV-COMP-HINF-SEQ-ORTHOLOGY | eco |
| 5 | PlantCyc evidence codes | EV-IC | eco |
| 5 | PlantCyc evidence codes | EV-AS-TAS | eco |
| 5 | PlantCyc evidence codes | EV-COMP-AINF | eco |
| 5 | PlantCyc evidence codes | direct assay evidence used in manual assertion | eco |
| 5 | PlantCyc evidence codes | expression pattern evidence used in manual assertion | eco |
| 5 | PlantCyc evidence codes | sequence orthology evidence used in manual assertion | eco |
| 5 | PlantCyc evidence codes | traceable author statement used in manual assertion | eco |
| 5 | PlantCyc evidence codes | inferred by curator | eco |
| 5 | PlantCyc evidence codes | automatic assertion computational inference | eco |
| 6 | evidence, identification confidence | experimental evidence | eco |
| 6 | evidence, identification confidence | metabolite identification confidence level | all |
| 6 | evidence, identification confidence | metabolomics standards initiative level | all |
| 6 | evidence, identification confidence | machine learning method evidence used in automatic assertion | eco |
| 6 | evidence, identification confidence | spectral library match evidence | eco |
| 6 | evidence, identification confidence | deep learning neural network method evidence used in automatic assertion | eco |
| 6 | evidence, identification confidence | compound identification confidence level | ms |
| 7 | metabolomics, evidence model | spectral library search | all |
| 7 | metabolomics, evidence model | spectral library search | edam |
| 7 | metabolomics, evidence model | mass spectra similarity | edam |
| 7 | metabolomics, evidence model | positive scan | ms |
| 7 | metabolomics, evidence model | negative scan | ms |
| 7 | metabolomics, evidence model | retention time | ms |
| 7 | metabolomics, evidence model | selected ion m/z | ms |
| 7 | metabolomics, evidence model | adduct ion | ms |
| 7 | metabolomics, evidence model | InChIKey | cheminf |
| 7 | metabolomics, evidence model | topic model | all |
| 7 | metabolomics, evidence model | topic modelling | edam |
| 7 | metabolomics, evidence model | substructure | cheminf |
| 7 | metabolomics, evidence model | mass spectrometry feature | all |
| 7 | metabolomics, evidence model | SEPIO | all |
| 7 | metabolomics, evidence model | evidence line | sepio |
| 7 | metabolomics, evidence model | assertion | sepio |
| 7 | metabolomics, evidence model | probability value | sio |
| 7 | metabolomics, evidence model | software | swo |
| 7 | metabolomics, evidence model | evidence | eco |
| 7 | metabolomics, evidence model | nanopublication | all |
| 7 | metabolomics, evidence model | molecular network | all |
| 7 | metabolomics, evidence model | fragmentation pattern | all |
| 8 | evidence (manual assertion) | computational evidence used in manual assertion | eco |
| 8 | evidence (manual assertion) | evidence used in manual assertion | eco |
| 8 | evidence (manual assertion) | computational inference used in manual assertion | eco |
| 8 | evidence (manual assertion) | author statement used in manual assertion | eco |
| 8 | evidence (spectral, unsupervised) | Mass2Motif | all |
| 8 | evidence (spectral, unsupervised) | MS2LDA | all |
| 8 | evidence (spectral, unsupervised) | unsupervised | eco |
| 8 | evidence (spectral, unsupervised) | unsupervised | all |
| 8 | evidence (spectral, unsupervised) | clustering evidence | eco |
| 8 | evidence (spectral, unsupervised) | spectral library | eco |
| 8 | evidence (spectral, unsupervised) | mass spectral library | eco |
| 8 | evidence (spectral, unsupervised) | spectrum matching | eco |
| 8 | evidence (spectral, unsupervised) | molecular family | all |
| 8 | evidence (spectral, unsupervised) | molecular networking | all |
| 8 | evidence (spectral, unsupervised) | mass spectrometry | eco |
| 9 | machine learning predictions | graph neural network | aio |
| 9 | machine learning predictions | link prediction | all |
| 9 | machine learning predictions | knowledge graph embedding | all |
| 9 | machine learning predictions | hyperparameter | all |
| 9 | machine learning predictions | machine learning model | aio |
| 9 | machine learning predictions | model evaluation | all |
| 9 | machine learning predictions | area under the ROC curve | all |
| 9 | machine learning predictions | area under curve | stato |
| 9 | machine learning predictions | average precision | all |
| 9 | machine learning predictions | precision at k | all |
| 9 | machine learning predictions | training data set | all |
| 9 | machine learning predictions | data split | aio |
| 9 | machine learning predictions | cross validation | stato |
| 9 | machine learning predictions | prediction score | all |
| 9 | machine learning predictions | protein language model | all |
| 9 | machine learning predictions | predicted | sio |
| 9 | machine learning predictions | confidence score | all |
| 9 | machine learning predictions | model | iao |
| 9 | machine learning predictions | data transformation | obi |
| 10 | transcriptomics | z-score | all |
| 10 | transcriptomics | z-score | stato |
| 10 | transcriptomics | standard score | all |
| 10 | transcriptomics | DESeq2 | all |
| 10 | transcriptomics | differential expression analysis | edam |
| 10 | transcriptomics | differential gene expression | all |
| 10 | transcriptomics | log fold change | all |
| 10 | transcriptomics | fold change | all |
| 10 | transcriptomics | false discovery rate | stato |
| 10 | transcriptomics | Benjamini-Hochberg | all |
| 10 | transcriptomics | adjusted p-value | all |
| 10 | transcriptomics | Wald test | all |
| 10 | transcriptomics | RNA sequencing assay | obi |
| 10 | transcriptomics | RNA-seq | all |
| 10 | transcriptomics | read count | all |
| 10 | transcriptomics | transcripts per million | all |
| 10 | transcriptomics | RPKM | all |
| 10 | transcriptomics | FPKM | all |
| 10 | transcriptomics | normalized read count | all |
| 10 | transcriptomics | gene expression level | all |
| 10 | transcriptomics | expression profile | all |
| 10 | transcriptomics | RNA-sequencing evidence | eco |
| 10 | transcriptomics | differential expression evidence | eco |
| 10 | transcriptomics | co-expression | all |
| 10 | transcriptomics | coexpression network | all |
| 10 | transcriptomics | rank correlation | all |
| 10 | transcriptomics | variance stabilizing transformation | all |
| 10 | transcriptomics | library size | all |
| 10 | transcriptomics | replicate | all |
| 10 | transcriptomics | biological replicate | obi |
| 10 | transcriptomics | treatment | all |
| 10 | transcriptomics | plant structure | po |
| 10 | transcriptomics | leaf | po |
| 10 | transcriptomics | experimental factor | efo |
| 10 | transcriptomics | base mean | all |
| 10 | transcriptomics | dispersion | stato |
| 10 | transcriptomics | standard error | stato |
| 10 | transcriptomics | mean | stato |
| 10 | transcriptomics | log2 | all |
| 11 | metabolomics acquisition and processing | Orbitrap Exploris 120 | ms |
| 11 | metabolomics acquisition and processing | instrument model | ms |
| 11 | metabolomics acquisition and processing | heated electrospray ionization | ms |
| 11 | metabolomics acquisition and processing | electrospray ionization | ms |
| 11 | metabolomics acquisition and processing | normalized collision energy | ms |
| 11 | metabolomics acquisition and processing | higher energy beam-type collision-induced dissociation | ms |
| 11 | metabolomics acquisition and processing | resolution | ms |
| 11 | metabolomics acquisition and processing | scan window | ms |
| 11 | metabolomics acquisition and processing | data-dependent acquisition | ms |
| 11 | metabolomics acquisition and processing | dynamic exclusion | ms |
| 11 | metabolomics acquisition and processing | exclusion list | ms |
| 11 | metabolomics acquisition and processing | isolation window | ms |
| 11 | metabolomics acquisition and processing | MZmine | ms |
| 11 | metabolomics acquisition and processing | SIRIUS | ms |
| 11 | metabolomics acquisition and processing | feature detection | ms |
| 11 | metabolomics acquisition and processing | peak picking | ms |
| 11 | metabolomics acquisition and processing | alignment | ms |
| 11 | metabolomics acquisition and processing | blank subtraction | ms |
| 11 | metabolomics acquisition and processing | feature-based molecular networking | edam |
| 11 | metabolomics acquisition and processing | molecular networking | edam |
| 11 | metabolomics acquisition and processing | mzmine | swo |
| 11 | metabolomics acquisition and processing | MS2LDA | swo |
| 11 | metabolomics acquisition and processing | liquid chromatography | chmo |
| 11 | metabolomics acquisition and processing | untargeted metabolomics | chmo |
| 11 | metabolomics acquisition and processing | peak area | all |
| 11 | metabolomics acquisition and processing | feature abundance | all |
| 11 | metabolomics acquisition and processing | ion intensity | all |
| 11 | metabolomics acquisition and processing | ClassyFire | all |
| 11 | metabolomics acquisition and processing | NPClassifier | all |
| 11 | metabolomics acquisition and processing | chemical taxonomy | all |
| 11 | metabolomics acquisition and processing | precursor exclusion | all |
| 11 | metabolomics acquisition and processing | mass spectral motif | all |
| 11 | metabolomics acquisition and processing | substructure motif | all |
| 11 | metabolomics acquisition and processing | heated electrospray | all |
| 11 | metabolomics acquisition and processing | blank | all |
| 12 | mass-only annotation | liquid chromatography mass spectrometry evidence | eco |
| 12 | mass-only annotation | accurate mass | ms |
| 12 | mass-only annotation | exact mass | chmo |
| 12 | mass-only annotation | mass-to-charge ratio | ms |
| 12 | mass-only annotation | MS1 spectrum | ms |
| 12 | mass-only annotation | full scan | ms |
| 12 | mass-only annotation | mass error | ms |

</details>

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

- **Regenerated files on pull requests.** Commits made with the workflow token do not start new workflow runs, so after the workflow has committed regenerated files, the checks do not run a second time; the run that made the commit has already checked the regenerated files. Pull requests from forks are not regenerated (their token is read-only): the check fails until the contributor runs `python check_terms.py --update --render`.

- **Rate limit.** GitHub allows 60 anonymous API requests per hour and address. Past that, the dashboard shows a message and the buttons keep working.
- **Pull requests made by the workflow do not start the checks workflow** (a GitHub rule for pull requests opened with the built-in token). The workflow runs the same checks itself before opening the pull request.
- **Self-assignment** needs write access. Everyone else comments, and a maintainer assigns.
- **The label workflow leaves a link instead of a pull request** when the organisation switches off "Allow GitHub Actions to create and approve pull requests" (the repository option is then greyed out). The issue gets a comment with a link that opens the pull request from the prepared branch in one click; an organisation owner can enable the option at Organization settings > Actions > General to make it automatic.
- **"Get Pages site failed ... Not Found"** in the publishing workflow means that Pages is not set up with the source *GitHub Actions* (Settings > Pages). Set it, then open the failed run under the Actions tab and choose **Re-run all jobs**, or use **Run workflow**. The workflow now skips the deployment with a warning instead of failing while the setting is missing.
- **Forms and workflows** work from the default branch only; until the merge, the dashboard buttons open the forms on a branch where they are not available.
- **A private repository** cannot be read by the dashboard without a login. Pages for a private repository depends on the GitHub plan.
- **A fork** sets the environment variable `LOD_REPO=owner/name` when regenerating, so that the dashboard talks to the fork.
