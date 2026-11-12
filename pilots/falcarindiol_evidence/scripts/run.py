#!/usr/bin/env python3
"""Run the additive falcarindiol evidence pilot from its own directory."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SHAPES = ROOT / 'shapes' / 'pilot_shapes.ttl'
QUERIES = ROOT / 'queries'


def load_graph(broken=False):
    g = Graph()
    for path in ('ontology.ttl', 'published.ttl', 'exploratory_scenario.ttl', 'synthetic_statistics.ttl'):
        g.parse(DATA / path, format='turtle')
    g.parse(ROOT / 'diagram' / 'diagram_mapping.ttl', format='turtle')
    if broken:
        g.parse(DATA / 'broken_additions.ttl', format='turtle')
    return g


def validate_graph(g):
    try:
        from pyshacl import validate
    except ImportError as exc:
        raise SystemExit('Install pyshacl with `python -m pip install -r requirements.txt`') from exc
    conforms, report, details = validate(
        data_graph=g, shacl_graph=str(SHAPES), inference='none',
        abort_on_first=False, allow_infos=False, allow_warnings=False
    )
    print('SHACL conforms:', conforms)
    print(details)
    return conforms


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='?', choices=['stats', 'query', 'validate', 'gpml-check'], default='stats')
    parser.add_argument('name', nargs='?', help='Query filename stem')
    parser.add_argument('--broken', action='store_true')
    args = parser.parse_args()
    g = load_graph(args.broken)
    if args.command == 'stats':
        print('RDF triples:', len(g))
        print('Queries:', ', '.join(p.stem for p in sorted(QUERIES.glob('*.rq'))))
    elif args.command == 'query':
        if not args.name or not (QUERIES / f'{args.name}.rq').is_file():
            parser.error('Pass a query name: ' + ', '.join(p.stem for p in QUERIES.glob('*.rq')))
        for row in g.query((QUERIES / f'{args.name}.rq').read_text()):
            print(' | '.join(str(v) if v is not None else '' for v in row))
    elif args.command == 'gpml-check':
        gpml_path = ROOT / 'diagram' / 'falcarindiol_teaching.gpml'
        tree = ET.parse(gpml_path)
        root = tree.getroot()
        ids = set()
        refs = []
        for el in root.iter():
            if 'elementId' in el.attrib:
                value = el.attrib['elementId']
                if value in ids:
                    raise SystemExit(f'Duplicate GPML elementId: {value}')
                ids.add(value)
            if 'elementRef' in el.attrib:
                refs.append(el.attrib['elementRef'])
        bad_refs = set(refs) - ids
        if bad_refs:
            raise SystemExit(f'Unresolved GPML elementRefs: {bad_refs}')
        from rdflib import Namespace, Literal
        demo = Namespace('https://example.org/falcarindiol-demo/')
        for s, o in g.subject_objects(demo.gpmlElementId):
            if str(o) not in ids:
                raise SystemExit(f'Unresolved diagram mapping: {s} -> {o}')
        print(f'GPML XML well-formed: {len(ids)} unique elementIds, {len(refs)} references; mappings resolved')
        print('NOTE: GPML2021 XSD / PathVisio validation NOT performed')
    elif args.command == 'validate':
        if not validate_graph(g):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
