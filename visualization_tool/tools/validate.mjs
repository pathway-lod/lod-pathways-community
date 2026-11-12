#!/usr/bin/env node
// Validate RDF files with the viewer's in-browser validator (src/validation/engine.js) in Node, and print the results
// grouped by message, in the same spirit as shape_constraints/validate.py. Use it to check that the button gives the
// same answers as pyshacl after a change to src/validation/ or to the shapes:
//
//   node tools/validate.mjs ../shape_constraints/rdf/bgc.ttl            # needs Node >= 22 (Comunica)
//   python ../shape_constraints/validate.py rdf/bgc.ttl --no-references  # from shape_constraints/: same numbers
//
// Shapes and vocabulary: public/data/validation/ (copied from shape_constraints/ by tools/rebuild_bundles.sh), as in
// the browser. Several files are validated together. Exit code 1 if there are violations.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Parser, Writer } from 'n3';
import { validate } from '../src/validation/engine.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const files = process.argv.slice(2);
if (!files.length) { console.error('usage: node tools/validate.mjs <file.ttl|.nq> [...]'); process.exit(2); }
const VAL = path.join(ROOT, 'public/data/validation');
const idx = JSON.parse(fs.readFileSync(path.join(VAL, 'index.json'), 'utf8'));
const shapes = idx.shapes.map((f) => fs.readFileSync(path.join(VAL, f), 'utf8'));
const vocab = idx.vocab ? fs.readFileSync(path.join(VAL, idx.vocab), 'utf8') : '';

const quads = files.flatMap((f) => new Parser({ format: f.endsWith('.nq') ? 'N-Quads' : 'Turtle' }).parse(fs.readFileSync(f, 'utf8'))
  .filter((q) => !q.graph.value.startsWith('urn:lodviz:report') && q.graph.value !== 'urn:lodviz:vocab'));
const r = await validate({ dataNq: new Writer({ format: 'N-Quads' }).quadsToString(quads), shapes, vocab });

const SH = 'http://www.w3.org/ns/shacl#';
const by = new Map();
for (const q of new Parser({ format: 'N-Quads', blankNodePrefix: '' }).parse(r.reportNq)) {
  if (!by.has(q.subject.value)) by.set(q.subject.value, {});
  by.get(q.subject.value)[q.predicate.value.replace(SH, '')] = q.object;
}
const groups = new Map();
for (const x of by.values()) {
  if (!x.resultSeverity || !x.focusNode) continue;
  const k = `${x.resultSeverity.value.replace(SH, '')}|${x.resultMessage?.value ?? ''}`;
  if (!groups.has(k)) groups.set(k, []);
  groups.get(k).push(x.focusNode.termType === 'BlankNode' ? '(blank node)' : x.focusNode.value);
}
console.log(`${r.triples} triples; ${r.counts.violation} violations, ${r.counts.warning} warnings`);
console.log(`time: ${r.seconds.total.toFixed(1)} s (SPARQL ${r.seconds.sparql.toFixed(1)} s, ${r.sparql.safe} queries once over the data, ${r.sparql.perNode} per node; basic rules ${r.seconds.core.toFixed(1)} s)\n`);
for (const [k, foci] of [...groups].sort((a, b) => a[0].localeCompare(b[0]) || b[1].length - a[1].length)) {
  const [sev, msg] = k.split('|');
  console.log(`[${foci.length}x] ${sev}: ${msg}`);
  for (const f of foci.slice(0, 3)) console.log(`      at ${f}`);
  if (foci.length > 3) console.log(`      ... and ${foci.length - 3} more`);
}
process.exit(r.counts.violation ? 1 : 0);
