#!/usr/bin/env python3
"""Export ONE Turtle file per annotated correlation CSV (offline).

Install: pip install pandas rdflib
Run: python export_omics_turtle_separate.py
     python export_omics_turtle_separate.py --only-shared --max-padj 0.05
     python export_omics_turtle_separate.py --project-dir PATH --base-uri https://your.org/study/
Outputs: results/turtle/<annotated CSV stem>.ttl
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, PROV, SKOS

PLANTCYC = "https://identifiers.org/plantcyc/"
TAIR = "https://identifiers.org/tair.locus/"
UNIPROT = "https://identifiers.org/uniprot/"
INCHIKEY = "https://identifiers.org/inchikey/"
AGI_RE = re.compile(r"(?<![A-Z0-9])AT(?:[1-5]|M|C)G\d{5}(?!\d)", re.I)
UP_RE = re.compile(r"(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9](?:[A-Z0-9]{3}[0-9])?)", re.I)
IK_RE = re.compile(r"[A-Z]{14}-[A-Z]{10}-[A-Z]", re.I)
REQUIRED = {"Feature_1", "Feature_2", "Omics_Comparison", "Feature1_mapped_pathway", "Feature2_mapped_pathway"}


def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def pathway_ids(value):
    return {part.strip() for part in re.split(r"[;,]", clean(value)) if part.strip()}


def finite_number(value):
    try:
        number = float(clean(value))
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def feature_kinds(comparison):
    comparison = clean(comparison).lower()
    if "transcript" in comparison and "proteom" in comparison:
        return "Transcript", "Protein"
    if "transcript" in comparison and "metabolom" in comparison:
        return "Transcript", "Metabolite"
    if "proteom" in comparison and "metabolom" in comparison:
        return "Protein", "Metabolite"
    return "Feature", "Feature"


def digest(*parts):
    return hashlib.sha256("\0".join(map(str, parts)).encode("utf-8")).hexdigest()[:24]


def provenance_index(path):
    """Match provenance by source filename, CSV row number, side and pathway."""
    idx = {}
    if not path.exists():
        return idx
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    necessary = {"file", "row_number", "feature_side", "plantcyc_id", "tier", "via"}
    if not necessary <= set(data):
        raise ValueError(f"{path}: missing {sorted(necessary - set(data))}")
    for row in data.itertuples(index=False):
        try:
            key = (clean(row.file).replace("\\", "/"), int(row.row_number), int(row.feature_side), clean(row.plantcyc_id))
        except (ValueError, TypeError):
            continue
        idx.setdefault(key, set()).add((clean(row.tier), clean(row.via)))
    return idx


def add_feature(graph, base, label, kind):
    node = base[f"feature/{kind.lower()}/{digest(kind, label)}"]
    graph.add((node, RDF.type, base.OmicsFeature))
    graph.add((node, RDFS.label, Literal(label)))
    graph.add((node, base.omicsType, Literal(kind)))
    if kind == "Transcript":
        match = AGI_RE.search(label)
        if match:
            graph.add((node, SKOS.closeMatch, URIRef(TAIR + match.group().upper())))
    elif kind == "Protein":
        match = UP_RE.fullmatch(label.upper().split("-")[0])
        if match:
            graph.add((node, SKOS.closeMatch, URIRef(UNIPROT + match.group())))
        else:
            match = AGI_RE.search(label)
            if match:
                graph.add((node, SKOS.closeMatch, URIRef(TAIR + match.group().upper())))
    elif kind == "Metabolite":
        match = IK_RE.fullmatch(label.upper())
        if match:
            graph.add((node, SKOS.closeMatch, URIRef(INCHIKEY + match.group())))
    return node


def add_numeric(graph, subject, predicate, raw, integer=False):
    value = finite_number(raw)
    if value is not None:
        if integer and value.is_integer():
            graph.add((subject, predicate, Literal(int(value), datatype=XSD.integer)))
        else:
            graph.add((subject, predicate, Literal(value, datatype=XSD.double)))


def create_graph(base_uri, source_name):
    if not base_uri.startswith(("https://", "http://")):
        raise ValueError("--base-uri must start with http:// or https://")
    base = Namespace(base_uri.rstrip("/#") + "/")
    graph = Graph()
    for prefix, namespace in {"study": base, "prov": PROV, "dcterms": DCTERMS, "skos": SKOS, "rdfs": RDFS, "rdf": RDF, "xsd": XSD}.items():
        graph.bind(prefix, namespace)
    dataset = base[f"dataset/{digest(source_name)}"]
    graph.add((dataset, RDF.type, PROV.Entity))
    graph.add((dataset, DCTERMS.identifier, Literal(source_name)))
    graph.add((dataset, DCTERMS.description, Literal("Annotated omics correlations; shared pathways are annotations, not proof of direct molecular interaction.")))
    for name in ("OmicsAssociation", "OmicsFeature", "CorrelationEvidence", "PathwayAssignment"):
        graph.add((base[name], RDF.type, RDFS.Class))
    return graph, base, dataset


def select_source_id(annotated_file, provenance):
    """Use original input file name only when it is unambiguous."""
    original_name = annotated_file.name.removesuffix("_annotated.csv") + ".csv"
    candidates = {key[0] for key in provenance if Path(key[0]).name == original_name}
    return next(iter(candidates)) if len(candidates) == 1 else None


def export_one(source, output, project_dir, base_uri, provenance, only_shared=False, max_padj=None):
    data = pd.read_csv(source, dtype=str, keep_default_na=False)
    missing = REQUIRED - set(data)
    if missing:
        raise ValueError(f"{source.name}: missing {sorted(missing)}")
    source_name = source.relative_to(project_dir).as_posix()
    original_id = select_source_id(source, provenance)
    graph, base, dataset = create_graph(base_uri, source_name)
    stats = {"input_rows": len(data), "exported_associations": 0, "shared_associations": 0, "pathway_assignments": 0, "missing_provenance": 0}

    for index, row in data.iterrows():
        left = pathway_ids(row.get("Feature1_mapped_pathway", ""))
        right = pathway_ids(row.get("Feature2_mapped_pathway", ""))
        shared = left & right
        if only_shared and not shared:
            continue
        if max_padj is not None:
            adjusted = finite_number(row.get("padj", ""))
            if adjusted is None or adjusted > max_padj:
                continue

        association_id = digest(source_name, index)
        assoc = base[f"association/{association_id}"]
        ev = base[f"evidence/{association_id}"]
        kind1, kind2 = feature_kinds(row["Omics_Comparison"])
        feat1 = add_feature(graph, base, clean(row["Feature_1"]), kind1)
        feat2 = add_feature(graph, base, clean(row["Feature_2"]), kind2)
        graph.add((assoc, RDF.type, base.OmicsAssociation))
        graph.add((assoc, base.feature1, feat1))
        graph.add((assoc, base.feature2, feat2))
        graph.add((assoc, base.omicsComparison, Literal(clean(row["Omics_Comparison"]))))
        graph.add((assoc, base.pathwayRelationship, Literal("same" if shared else "different" if left and right else "not_comparable")))
        graph.add((assoc, PROV.wasDerivedFrom, dataset))
        graph.add((assoc, base.sourceRowNumber, Literal(index + 2, datatype=XSD.integer)))
        graph.add((assoc, base.hasEvidence, ev))
        graph.add((ev, RDF.type, base.CorrelationEvidence))
        for col, predicate in (("Pearson_r", base.pearsonR), ("Spearman_rho", base.spearmanRho), ("p_value", base.pValue), ("padj", base.adjustedPValue)):
            add_numeric(graph, ev, predicate, row.get(col, ""))
        add_numeric(graph, ev, base.nSamples, row.get("n_samples", ""), integer=True)
        for pw in sorted(shared):
            graph.add((assoc, base.supportedBySharedPathway, URIRef(PLANTCYC + quote(pw, safe=""))))
        if shared:
            stats["shared_associations"] += 1

        for side, feature, assigned, tier_column in ((1, feat1, left, "Feature1_mapping_tier"), (2, feat2, right, "Feature2_mapping_tier")):
            for pw in sorted(assigned):
                assignment = base[f"assignment/{digest(source_name, index, side, pw)}"]
                graph.add((assignment, RDF.type, base.PathwayAssignment))
                graph.add((assoc, base.hasPathwayAssignment, assignment))
                graph.add((assignment, base.mappedFeature, feature))
                graph.add((assignment, base.mappedPathway, URIRef(PLANTCYC + quote(pw, safe=""))))
                graph.add((assignment, base.featureSide, Literal(side, datatype=XSD.integer)))
                evs = provenance.get((original_id, index + 2, side, pw), set()) if original_id else set()
                if evs:
                    for tier, via in sorted(evs):
                        if tier:
                            graph.add((assignment, base.mappingTier, Literal(tier)))
                        if via:
                            graph.add((assignment, base.mappingVia, Literal(via)))
                else:
                    stats["missing_provenance"] += 1
                    for tier in pathway_ids(row.get(tier_column, "")):
                        graph.add((assignment, base.mappingTier, Literal(tier)))
                stats["pathway_assignments"] += 1
        stats["exported_associations"] += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output), format="turtle", encoding="utf-8")
    verified = Graph()
    verified.parse(str(output), format="turtle")
    stats["triples"] = len(verified)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, help="Default: PROJECT/results/turtle")
    parser.add_argument("--base-uri", default="https://example.org/arabidopsis-heat-stress/")
    parser.add_argument("--only-shared", action="store_true")
    parser.add_argument("--max-padj", type=float)
    args = parser.parse_args()
    if args.max_padj is not None and not 0 <= args.max_padj <= 1:
        parser.error("--max-padj must be between 0 and 1")
    project_dir = args.project_dir.resolve()
    annotated_dir = project_dir / "results" / "annotated_correlations"
    sources = sorted(annotated_dir.rglob("*_annotated.csv"))
    if not sources:
        parser.error(f"No *_annotated.csv files under {annotated_dir}")
    output_dir = (args.output_dir or project_dir / "results" / "turtle").resolve()
    prov = provenance_index(project_dir / "results" / "mapping_tables" / "mapping_provenance.csv")
    for source in sources:
        # Preserve subdirectories; avoid overwriting same-named CSVs.
        relative = source.relative_to(annotated_dir).with_suffix(".ttl")
        output = output_dir / relative
        stats = export_one(source, output, project_dir, args.base_uri, prov, args.only_shared, args.max_padj)
        print(f"{source.name} -> {output} | " + ", ".join(f"{key}={value}" for key, value in stats.items()))
    print(f"Created {len(sources)} separate Turtle files in {output_dir}")
    if args.base_uri.startswith("https://example.org/"):
        print("NOTE: Set --base-uri to your persistent project namespace before publication.")


if __name__ == "__main__":
    main()
