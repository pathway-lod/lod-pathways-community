
# Extended PlantCyc pathway relationships

This offline Python script adds **shared reaction** and **parent–subpathway** comparisons to the annotated correlation CSV files produced by the basic Arabidopsis pathway mapper. It preserves all original data columns and does not overwrite the original annotations.

## Requirements

```bash
pip install pandas
```

The **basic mapper must have run first**, producing files under `results/annotated_correlations/*_annotated.csv`. You do not need to rerun it if those files already exist.

## Recommended: extract hierarchy and reaction membership from PlantCyc

Obtain the official PlantCyc database export according to PMN's download terms and locate its `pathways.dat` file. Run:

```bash
python add_extended_pathway_relationships.py --plantcyc-dat data/plantcyc/pathways.dat
```

The script reads two documented fields from `pathways.dat`:

- `SUPER-PATHWAYS` / `SUB-PATHWAYS` for explicit pathway containment.
- `REACTION-LIST` for **direct** pathway-to-reaction memberships.

For stricter filtering, also supply the official `reactions.dat` file from the **same PlantCyc release**:

```bash
python add_extended_pathway_relationships.py \
  --plantcyc-dat data/plantcyc/pathways.dat \
  --reactions-dat data/plantcyc/reactions.dat
```

This excludes `REACTION-LIST` references that are not defined in `reactions.dat`. The script also excludes entries that resolve to known pathway IDs. The `reactions.dat` file is used **for validation**, not for discovering pathway membership; pathway memberships come from `pathways.dat`.

## Reuse existing CSV inputs

After extraction, you may rerun the comparison without the original `.dat` file:

```bash
python add_extended_pathway_relationships.py
```

The script reads:

```text
results/mapping_tables/pathway_hierarchy.csv
results/mapping_tables/pathway_reactions.csv
```

Their required column headers are:

```csv
child_pathway_id,parent_pathway_id
```

and

```csv
pathway_id,reaction_id
```

You may also provide alternate CSV paths with `--hierarchy` and `--reactions`.

## Output

```text
results/
├── mapping_tables/
│   ├── pathway_hierarchy.csv
│   ├── pathway_reactions.csv
│   ├── pathway_hierarchy_skipped.csv   # if applicable
│   └── pathway_reactions_skipped.csv   # if applicable
├── annotated_correlations/            # unchanged source files
└── annotated_correlations_extended/
    └── *_annotated.csv
```

Every extended correlation table retains the original fields and adds:

| Column | Meaning |
| --- | --- |
| `pathway_relationship_extended` | Highest-priority supported relationship |
| `extended_related_pathway_pairs` | Supporting feature-1/feature-2 pathway ID pairs (`ID1\|ID2`) |
| `extended_shared_reaction_ids` | Shared PlantCyc reaction IDs when the result is `shared_reaction` |

Classification priority:

1. `same_pathway`: at least one exactly identical pathway ID.
2. `hierarchy_related`: one pathway is an ancestor or descendant of another, using explicit PlantCyc containment links.
3. `shared_reaction`: the two different pathways share a direct `REACTION-LIST` entry.
4. `no_extended_match`: no relationship is found in the supplied hierarchy or reaction data.
5. `not_evaluated`: neither hierarchy nor reaction data is available.
6. `not_comparable`: at least one feature lacks mapped pathways.

The original `pathway_relationship` column is **not changed**. A higher-priority classification does not report additional lower-priority relationships in that same row.

## Diagnostics

The terminal shows counts for hierarchy links, direct reaction memberships, unique mapped pathway IDs, mapped IDs present in the hierarchy, mapped IDs having reaction membership, and correlations with both sides mapped. These statistics are important when interpreting `no_extended_match`: a negative comparison **does not demonstrate that two features are biologically unrelated**, especially when pathway coverage is incomplete.

## Options

```bash
python add_extended_pathway_relationships.py --help
```

- `--project-dir`: project directory containing `results/` (defaults to script directory).
- `--plantcyc-dat`: extract hierarchy and reaction membership from local PlantCyc `pathways.dat`.
- `--reactions-dat`: optionally validate reaction IDs against local PlantCyc `reactions.dat`; requires `--plantcyc-dat`.
- `--hierarchy`: existing hierarchy CSV or extraction destination.
- `--reactions`: existing reaction-membership CSV or extraction destination.
- `--output-dir`: directory for extended correlation tables.

No online BioCyc authentication or network requests are performed.

## Interpretation and limitations

- Shared reactions indicate **overlap in pathway annotation**, not a direct protein–metabolite interaction, enzymatic reaction between the two features, or causal biological mechanism.
- The script uses exact reaction IDs and exact pathway IDs; it does not infer equivalences between different identifiers.
- `REACTION-LIST` is interpreted as direct pathway membership. The script does not automatically expand subpathways to include all descendant reactions.
- With no `reactions.dat`, non-pathway identifiers in `REACTION-LIST` are assumed to be reactions, and may require additional validation.
- The mapping quality of the **basic mapper** (direct vs. EC-based vs. InChIKey connectivity) is unchanged by this extension.
- Database licensing and citation requirements for PMN/PlantCyc still apply.

### References

- [PMN download information](https://plantcyc.org/downloads/)
- [Pathway Tools flat-file specification](https://pathwaytools.org/flatfile-format.html)
- [Pathway Tools schema documentation](https://pathway.yeastgenome.org/schema.shtml)
