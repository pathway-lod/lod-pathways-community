#!/usr/bin/env python3
"""Add hierarchy- and shared-reaction relationships to mapped omics correlations.

Run the BASIC pathway mapper first to create
    results/annotated_correlations/**/*_annotated.csv

Extract pathway hierarchy AND pathway-to-reaction memberships from an official,
locally downloaded PlantCyc pathways.dat:
    python add_extended_pathway_relationships.py --plantcyc-dat data/plantcyc/pathways.dat

Use already extracted CSVs (no pathways.dat needed):
    python add_extended_pathway_relationships.py

Optional: Validate REACTION-LIST IDs against official reactions.dat:
    python add_extended_pathway_relationships.py \
      --plantcyc-dat data/plantcyc/pathways.dat \
      --reactions-dat data/plantcyc/reactions.dat

Output:
  results/mapping_tables/pathway_hierarchy.csv
  results/mapping_tables/pathway_reactions.csv
  results/annotated_correlations_extended/**/*_annotated.csv

Original annotated CSV files are NEVER modified. No network access is used.
Requires: pip install pandas
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

HIERARCHY_COLUMNS = ["child_pathway_id", "parent_pathway_id"]
REACTION_COLUMNS = ["pathway_id", "reaction_id"]
PATHWAY_ID = re.compile(r"\|?([A-Za-z0-9][A-Za-z0-9_.-]*)\|?\Z")


def normalize_id(raw):
    text = str(raw or "").strip().strip("|")
    if ":" in text:
        prefix, text = text.split(":", 1)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
            return None
    match = PATHWAY_ID.fullmatch(text)
    return match.group(1) if match else None


def split_ids(value):
    if pd.isna(value):
        return set()
    return {p for x in re.split(r"[;,]", str(value)) if (p := normalize_id(x))}


def read_relationships(path, columns):
    if not path.is_file():
        return pd.DataFrame(columns=columns), False
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.columns = data.columns.str.strip()
    missing = set(columns) - set(data.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    for col in columns:
        data[col] = data[col].str.strip()
    data = data.loc[(data[columns] != "").all(axis=1), columns].drop_duplicates()
    return data, not data.empty


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(columns)
        writer.writerows(sorted(rows))


def iter_dat_records(path):
    """Read Pathway Tools attribute-value flat file records separated by //."""
    record = {}
    with path.open(encoding="utf-8-sig", errors="replace") as stream:
        for raw in stream:
            line = raw.rstrip("\r\n")
            if line.strip() == "//":
                if record:
                    yield record
                record = {}
                continue
            # '//' is the record delimiter; '/' in values is otherwise valid.
            if not line or line.startswith(("#", "^")) or " - " not in line:
                continue
            field, value = line.split(" - ", 1)
            record.setdefault(field.upper().strip(), []).append(value.strip())
    if record:
        yield record


def read_dat_ids(path):
    """Read identifiers from a separate reaction flat file, if provided."""
    if not path.is_file():
        raise FileNotFoundError(f"Reaction database file not found: {path}")
    return {pid for rec in iter_dat_records(path)
            for raw in rec.get("UNIQUE-ID", []) if (pid := normalize_id(raw))}


def extract_plantcyc_evidence(path, known_reactions=None):
    """Extract hierarchy edges and *direct* REACTION-LIST memberships.

    REACTION-LIST contains reaction references; some datasets may also contain
    pathway references. Pathway references are excluded by known pathway IDs.
    If known_reactions is provided, retain only IDs from reactions.dat.
    """
    records = list(iter_dat_records(path))
    pathways = {pid for rec in records for raw in rec.get("UNIQUE-ID", [])
                if (pid := normalize_id(raw))}
    hierarchy, memberships, unresolved, rejected = set(), set(), set(), set()
    with_reactions = 0
    for rec in records:
        own = next((pid for raw in rec.get("UNIQUE-ID", [])
                    if (pid := normalize_id(raw))), None)
        if not own:
            continue
        for slot, child_first in (("SUPER-PATHWAYS", True), ("SUB-PATHWAYS", False)):
            for raw in rec.get(slot, []):
                other = normalize_id(raw)
                if not other or other not in pathways or other == own:
                    unresolved.add((own, slot, raw))
                else:
                    hierarchy.add((own, other) if child_first else (other, own))
        has_any_reactions = False
        for raw in rec.get("REACTION-LIST", []):
            rid = normalize_id(raw)
            if not rid:
                rejected.add((own, raw, "invalid_identifier"))
            elif rid in pathways:
                rejected.add((own, raw, "pathway_reference_not_reaction"))
            elif known_reactions is not None and rid not in known_reactions:
                rejected.add((own, raw, "absent_from_reactions_dat"))
            else:
                memberships.add((own, rid))
                has_any_reactions = True
        with_reactions += int(has_any_reactions)
    return hierarchy, memberships, unresolved, rejected, len(pathways), with_reactions


def export_plantcyc_evidence(dat_path, hierarchy_path, reactions_path, reactions_dat=None):
    if not dat_path.is_file():
        raise FileNotFoundError(f"PlantCyc pathways.dat not found: {dat_path}")
    valid_reactions = read_dat_ids(reactions_dat) if reactions_dat else None
    hierarchy, reactions, unresolved, rejected, count, with_reactions = extract_plantcyc_evidence(
        dat_path, valid_reactions
    )
    if not hierarchy and not reactions:
        raise ValueError(f"No hierarchy or REACTION-LIST entries in {dat_path}; existing CSVs unchanged")
    # Write both outputs, including headers-only files for truly absent evidence.
    write_csv(hierarchy_path, HIERARCHY_COLUMNS, hierarchy)
    write_csv(reactions_path, REACTION_COLUMNS, reactions)
    if unresolved:
        path = hierarchy_path.with_name("pathway_hierarchy_skipped.csv")
        write_csv(path, ["pathway_id", "field", "unresolved_value"], unresolved)
        print(f"Unresolved hierarchy references: {len(unresolved)} -> {path}", flush=True)
    if rejected:
        path = reactions_path.with_name("pathway_reactions_skipped.csv")
        write_csv(path, ["pathway_id", "raw_reference", "reason"], rejected)
        print(f"Skipped reaction references: {len(rejected)} -> {path}", flush=True)
    print(f"PlantCyc records: {count}; hierarchy edges: {len(hierarchy)}; "
          f"direct reaction memberships: {len(reactions)} across {with_reactions} pathways", flush=True)
    if valid_reactions is None:
        print("NOTE: REACTION-LIST IDs were not validated against reactions.dat. "
              "Pass --reactions-dat for stricter validation.", flush=True)
    print(f"Hierarchy CSV: {hierarchy_path}\nReaction CSV: {reactions_path}", flush=True)


def build_indexes(hierarchy, reactions):
    parents, reaction_index = defaultdict(set), defaultdict(set)
    for rec in hierarchy.itertuples(index=False):
        parents[rec.child_pathway_id].add(rec.parent_pathway_id)
    for rec in reactions.itertuples(index=False):
        reaction_index[rec.pathway_id].add(rec.reaction_id)
    return parents, reaction_index


def ancestors(pathway, parents):
    found, pending = set(), list(parents.get(pathway, ()))
    while pending:
        current = pending.pop()
        if current == pathway or current in found:
            continue
        found.add(current)
        pending.extend(parents.get(current, ()))
    return found


def compare_extended(left, right, parents, reactions, has_hierarchy, has_reactions):
    """Priority: identical pathway > explicit hierarchy > shared reaction."""
    if not left or not right:
        return "not_comparable", set(), set()
    common = left & right
    if common:
        return "same_pathway", {(p, p) for p in common}, set()

    if has_hierarchy:
        lineage = {p: ancestors(p, parents) for p in left | right}
        pairs = {(a, b) for a in left for b in right
                 if b in lineage[a] or a in lineage[b]}
        if pairs:
            return "hierarchy_related", pairs, set()

    if has_reactions:
        pairs, shared_reaction_ids = set(), set()
        for a in left:
            for b in right:
                common_rxns = reactions.get(a, set()) & reactions.get(b, set())
                if common_rxns:
                    pairs.add((a, b))
                    shared_reaction_ids.update(common_rxns)
        if pairs:
            return "shared_reaction", pairs, shared_reaction_ids

    if not has_hierarchy and not has_reactions:
        return "not_evaluated", set(), set()
    # Absence of an explicit relationship is not proof of biological unrelatedness.
    return "no_extended_match", set(), set()


def add_extended_columns(data, parents, reactions, has_hierarchy, has_reactions):
    required = {"Feature1_mapped_pathway", "Feature2_mapped_pathway"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Annotated CSV missing {sorted(missing)}")
    result = data.copy()
    labels, pairs_text, reaction_text = [], [], []
    for a, b in zip(data["Feature1_mapped_pathway"], data["Feature2_mapped_pathway"]):
        label, pairs, rxns = compare_extended(
            split_ids(a), split_ids(b), parents, reactions, has_hierarchy, has_reactions
        )
        labels.append(label)
        pairs_text.append("; ".join(f"{x}|{y}" for x, y in sorted(pairs)))
        reaction_text.append("; ".join(sorted(rxns)))
    result["pathway_relationship_extended"] = labels
    result["extended_related_pathway_pairs"] = pairs_text
    result["extended_shared_reaction_ids"] = reaction_text
    return result


def resolve_path(path, project):
    return path if path.is_absolute() else project / path


def coverage_summary(inputs, reaction_idx, parents):
    mapped = set()
    comparable = 0
    for source in inputs:
        frame = pd.read_csv(source, dtype=str, keep_default_na=False,
                            usecols=["Feature1_mapped_pathway", "Feature2_mapped_pathway"])
        for a, b in zip(frame.iloc[:, 0], frame.iloc[:, 1]):
            left, right = split_ids(a), split_ids(b)
            mapped.update(left | right)
            comparable += bool(left and right)
    hierarchy_ids = set(parents) | {x for values in parents.values() for x in values}
    with_rxns = mapped & set(reaction_idx)
    with_hierarchy = mapped & hierarchy_ids
    print(f"Mapped unique pathway IDs: {len(mapped)}; in hierarchy: {len(with_hierarchy)}; "
          f"with reaction memberships: {len(with_rxns)}; correlations with both sides mapped: {comparable}",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--plantcyc-dat", type=Path,
                        help="Local PlantCyc pathways.dat: extract hierarchy AND reactions")
    parser.add_argument("--reactions-dat", type=Path,
                        help="Optional PlantCyc reactions.dat to validate REACTION-LIST IDs")
    parser.add_argument("--hierarchy", type=Path, help="Existing/extracted hierarchy CSV")
    parser.add_argument("--reactions", type=Path, help="Existing/extracted pathway reaction CSV")
    parser.add_argument("--output-dir", type=Path, help="Extended annotated correlation CSV directory")
    args = parser.parse_args()
    if args.reactions_dat and not args.plantcyc_dat:
        parser.error("--reactions-dat requires --plantcyc-dat")

    project = args.project_dir.resolve()
    mapping_dir = project / "results" / "mapping_tables"
    input_dir = project / "results" / "annotated_correlations"
    inputs = sorted(input_dir.rglob("*_annotated.csv")) if input_dir.is_dir() else []
    if not inputs:
        parser.error(f"No *_annotated.csv files in {input_dir}. Run the basic mapper first.")
    hierarchy_path = (resolve_path(args.hierarchy, project) if args.hierarchy
                      else mapping_dir / "pathway_hierarchy.csv")
    reactions_path = (resolve_path(args.reactions, project) if args.reactions
                      else mapping_dir / "pathway_reactions.csv")
    output_dir = (resolve_path(args.output_dir, project) if args.output_dir
                  else project / "results" / "annotated_correlations_extended")

    if args.plantcyc_dat:
        export_plantcyc_evidence(
            resolve_path(args.plantcyc_dat, project), hierarchy_path, reactions_path,
            resolve_path(args.reactions_dat, project) if args.reactions_dat else None
        )
    hierarchy, has_hierarchy = read_relationships(hierarchy_path, HIERARCHY_COLUMNS)
    reactions, has_reactions = read_relationships(reactions_path, REACTION_COLUMNS)
    parents, reaction_idx = build_indexes(hierarchy, reactions)
    print(f"Hierarchy: {len(hierarchy)} links ({hierarchy_path if has_hierarchy else 'unavailable'})", flush=True)
    print(f"Reactions: {len(reactions)} memberships ({reactions_path if has_reactions else 'unavailable'})", flush=True)
    coverage_summary(inputs, reaction_idx, parents)

    for source in inputs:
        frame = pd.read_csv(source, dtype=str, keep_default_na=False)
        extended = add_extended_columns(frame, parents, reaction_idx, has_hierarchy, has_reactions)
        destination = output_dir / source.relative_to(input_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        extended.to_csv(destination, index=False)
        counts = extended["pathway_relationship_extended"].value_counts().to_dict()
        print(f"{source.name}: {counts} -> {destination}", flush=True)
    print("Finished. Original annotated CSVs were not modified.", flush=True)


if __name__ == "__main__":
    main()
