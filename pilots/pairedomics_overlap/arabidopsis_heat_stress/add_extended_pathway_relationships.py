#!/usr/bin/env python3
"""Add hierarchy/reaction-based pathway relationships to annotated correlation CSVs.

Run the basic mapper first to create results/annotated_correlations/*_annotated.csv.
This script never queries online databases and does not change the original files.

Use an existing hierarchy CSV:
    python add_extended_pathway_relationships.py

Extract a hierarchy from official local PlantCyc pathways.dat:
    python add_extended_pathway_relationships.py --plantcyc-dat data/plantcyc/pathways.dat

Optional reaction memberships: results/mapping_tables/pathway_reactions.csv
Requirements: pip install pandas
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


def save_hierarchy(path, edges):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HIERARCHY_COLUMNS)
        writer.writerows(sorted(edges))


def iter_dat_records(path):
    record = {}
    with path.open(encoding="utf-8-sig", errors="replace") as stream:
        for raw in stream:
            line = raw.rstrip("\r\n")
            if line.strip() == "//":
                if record:
                    yield record
                record = {}
                continue
            if not line or line.startswith(("#", "^", "/")) or " - " not in line:
                continue
            field, value = line.split(" - ", 1)
            record.setdefault(field.upper().strip(), []).append(value.strip())
    if record:
        yield record


def extract_plantcyc_hierarchy(path):
    records = list(iter_dat_records(path))
    known = {pid for rec in records for raw in rec.get("UNIQUE-ID", [])
             if (pid := normalize_id(raw))}
    edges, skipped = set(), set()
    for rec in records:
        own = next((pid for raw in rec.get("UNIQUE-ID", [])
                    if (pid := normalize_id(raw))), None)
        if not own:
            continue
        for slot, child_first in (("SUPER-PATHWAYS", True), ("SUB-PATHWAYS", False)):
            for raw in rec.get(slot, []):
                other = normalize_id(raw)
                if not other or other not in known or other == own:
                    skipped.add((own, slot, raw))
                else:
                    edges.add((own, other) if child_first else (other, own))
    return sorted(edges), sorted(skipped), len(known)


def save_plantcyc_hierarchy(dat_path, output_csv):
    if not dat_path.is_file():
        raise FileNotFoundError(f"PlantCyc pathways.dat not found: {dat_path}")
    edges, skipped, count = extract_plantcyc_hierarchy(dat_path)
    if not edges:
        raise ValueError(f"No explicit pathway hierarchy edges in {dat_path}; CSV not overwritten")
    save_hierarchy(output_csv, edges)
    if skipped:
        skipped_path = output_csv.with_name("pathway_hierarchy_skipped.csv")
        with skipped_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["pathway_id", "field", "unresolved_value"])
            writer.writerows(skipped)
        print(f"Unresolved .dat references: {len(skipped)} -> {skipped_path}", flush=True)
    print(f"PlantCyc pathway records: {count}; hierarchy links: {len(edges)} -> {output_csv}", flush=True)


def build_indexes(hierarchy, reactions):
    parents = defaultdict(set)
    for rec in hierarchy.itertuples(index=False):
        parents[rec.child_pathway_id].add(rec.parent_pathway_id)
    reaction_index = defaultdict(set)
    for rec in reactions.itertuples(index=False):
        reaction_index[rec.pathway_id].add(rec.reaction_id)
    return parents, reaction_index


def ancestors(pathway, parents):
    found = set()
    pending = list(parents.get(pathway, ()))
    while pending:
        current = pending.pop()
        if current in found or current == pathway:
            continue
        found.add(current)
        pending.extend(parents.get(current, ()))
    return found


def compare_extended(left, right, parents, reactions, has_hierarchy, has_reactions):
    """Return priority-ranked category, supporting pairs, and reaction IDs."""
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
        pairs, reaction_ids = set(), set()
        for a in left:
            for b in right:
                common_rxns = reactions.get(a, set()) & reactions.get(b, set())
                if common_rxns:
                    pairs.add((a, b))
                    reaction_ids.update(common_rxns)
        if pairs:
            return "shared_reaction", pairs, reaction_ids

    if not has_hierarchy and not has_reactions:
        return "not_evaluated", set(), set()
    # A negative result is limited to relationships explicitly provided in the input files.
    return "no_extended_match", set(), set()


def add_extended_columns(data, parents, reactions, has_hierarchy, has_reactions):
    required = {"Feature1_mapped_pathway", "Feature2_mapped_pathway"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Annotated CSV missing {sorted(missing)}")
    output = data.copy()
    labels, pair_labels, reaction_labels = [], [], []
    for a, b in zip(data["Feature1_mapped_pathway"], data["Feature2_mapped_pathway"]):
        label, pairs, shared_rxns = compare_extended(
            split_ids(a), split_ids(b), parents, reactions, has_hierarchy, has_reactions
        )
        labels.append(label)
        pair_labels.append("; ".join(f"{x}|{y}" for x, y in sorted(pairs)))
        reaction_labels.append("; ".join(sorted(shared_rxns)))
    output["pathway_relationship_extended"] = labels
    output["extended_related_pathway_pairs"] = pair_labels
    output["extended_shared_reaction_ids"] = reaction_labels
    return output


def resolve_path(path, project):
    return path if path.is_absolute() else project / path


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--plantcyc-dat", type=Path,
                        help="Official local PlantCyc pathways.dat; extracts hierarchy to CSV")
    parser.add_argument("--hierarchy", type=Path,
                        help="Existing hierarchy CSV or destination when extracting from pathways.dat")
    parser.add_argument("--reactions", type=Path, help="Optional pathway-to-reaction CSV")
    parser.add_argument("--output-dir", type=Path, help="Extended annotated CSV output directory")
    args = parser.parse_args()

    project = args.project_dir.resolve()
    mapping_dir = project / "results" / "mapping_tables"
    input_dir = project / "results" / "annotated_correlations"
    inputs = sorted(input_dir.rglob("*_annotated.csv")) if input_dir.is_dir() else []
    if not inputs:
        parser.error(f"No *_annotated.csv files under {input_dir}. Run the basic mapper first.")

    hierarchy_path = (resolve_path(args.hierarchy, project) if args.hierarchy
                      else mapping_dir / "pathway_hierarchy.csv")
    reactions_path = (resolve_path(args.reactions, project) if args.reactions
                      else mapping_dir / "pathway_reactions.csv")
    output_dir = (resolve_path(args.output_dir, project) if args.output_dir
                  else project / "results" / "annotated_correlations_extended")

    if args.plantcyc_dat:
        save_plantcyc_hierarchy(resolve_path(args.plantcyc_dat, project), hierarchy_path)

    hierarchy, has_hierarchy = read_relationships(hierarchy_path, HIERARCHY_COLUMNS)
    reactions, has_reactions = read_relationships(reactions_path, REACTION_COLUMNS)
    parents, reaction_index = build_indexes(hierarchy, reactions)
    print(f"Hierarchy: {len(hierarchy)} links ({hierarchy_path if has_hierarchy else 'unavailable'})", flush=True)
    print(f"Reactions: {len(reactions)} memberships ({reactions_path if has_reactions else 'unavailable'})", flush=True)

    for source in inputs:
        data = pd.read_csv(source, dtype=str, keep_default_na=False)
        extended = add_extended_columns(data, parents, reaction_index, has_hierarchy, has_reactions)
        destination = output_dir / source.relative_to(input_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        extended.to_csv(destination, index=False)
        counts = extended["pathway_relationship_extended"].value_counts().to_dict()
        print(f"{source.name}: {counts} -> {destination}", flush=True)
    print("Finished. Original annotated CSVs were not modified.", flush=True)


if __name__ == "__main__":
    main()
