"""Report multi-target connectivity annotations from committed pilot CSVs (offline).

Run: python shape_constraints/audit_annotation_ambiguity.py
These are ambiguity risks, not evidence of contradictory measurements.
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'pilots/metabolomics_overlap'


def build_report():
    with (PILOT / 'data/plantmetwiki_metabolites.csv').open() as f:
        names = {r['inchikey']: r['name'] for r in csv.DictReader(f)}
    groups = defaultdict(list)
    with (PILOT / 'results/feature_hits.csv').open() as f:
        for row in csv.DictReader(f):
            if row['tier'] != 'ms2query_analog':
                groups[(row['mode'], row['feature_id'], row['key14'])].append(row)
    report = []
    for (mode, feature, key), rows in sorted(groups.items()):
        candidates = sorted(set(rows[0]['pmw_inchikeys'].split(' | ')))
        if len(candidates) < 2:
            continue
        # Same first two blocks: only final block differs (e.g. protonation).
        kind = ('final_block_only' if len({k.rsplit('-', 1)[0] for k in candidates}) == 1
                else 'second_block_difference')
        report.append(dict(
            annotation=f'https://example.org/lod-pathways/pilot/annotation_MTBLS14270_{mode}_{feature}_{key}',
            mode=mode, feature_id=feature, connectivity_key=key,
            candidate_count=len(candidates), ambiguity_kind=kind,
            tiers=' | '.join(sorted({r['tier'] for r in rows})),
            candidates=' | '.join(f'{k}: {names.get(k, "")}' for k in candidates)))
    return report


def main():
    rows = build_report()
    output = ROOT / 'shape_constraints/annotation_ambiguity.csv'
    with output.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    groups = {r['connectivity_key'] for r in rows}
    print(f'{len(rows)} multi-target annotations across {len(groups)} connectivity groups. Report: {output}')
    for kind in ('second_block_difference', 'final_block_only'):
        subset = [r for r in rows if r['ambiguity_kind'] == kind]
        print(f'{kind}: {len(subset)} annotations, {len({r["connectivity_key"] for r in subset})} groups')


if __name__ == '__main__':
    main()
