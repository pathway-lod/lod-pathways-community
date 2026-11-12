// SHACL validation in the browser (or Node): shacl-engine 1.1.3 with three corrections and one speed-up.
// Knows no evidence vocabulary: shapes and vocabulary come in as text (paths in the profile, see docs/validation.md).
//
// Corrections (tested against pyshacl on the repository's 83 shape test cases and the 4 pilot files, 2026-11-12):
//  1. Several sh:sparql constraints on one shape: shacl-engine 1.1.3 compiles them as ONE constraint whose query is
//     empty (only PREFIX lines), so every focus node gets a false violation and the real constraints never run.
//     Here each sh:sparql node is compiled on its own (compileSparql below).
//  2. shacl-engine follows rdfs:subClassOf (sh:targetClass, sh:class) in the shapes graph only; the vocabulary is
//     therefore added to the shapes as well as to the data (pyshacl's ont_graph puts it into the data).
//  3. Message of a SPARQL constraint: shacl-engine prefers the shape's sh:message; the constraint's own is used here
//     (as pyshacl does), taken from sh:sourceConstraint.
// Speed-up: shacl-engine runs every SPARQL constraint once per focus node, with a new query engine each time (17 min
// for the 54k-triple annotation pilot). A constraint whose query is "safe" (see isSafe) is run ONCE over the whole data
// instead, and its rows are looked up per focus node (8 s for the same file). Other queries keep the per-node way.
import rdf from 'rdf-ext';
import { Parser as N3Parser, Writer } from 'n3';
import TermMap from '@rdfjs/term-map';
import { Parser as SparqlParser } from 'sparqljs';
import { Validator } from 'shacl-engine';
import * as ns from 'shacl-engine/lib/namespaces.js';
import parsePath from 'shacl-engine/lib/parsePath.js';
import { bindingsToObject, stringifyPath } from 'shacl-engine/lib/sparql.js';
import { targetResolvers } from 'shacl-engine/sparql.js';
import { QueryEngine } from '@comunica/query-sparql-rdfjs-lite';
import { BindingsFactory } from '@comunica/utils-bindings-factory';

const SH = 'http://www.w3.org/ns/shacl#';

// SELECT over a dataset with one Comunica engine and source for the whole run (shacl-engine's select() creates a new
// engine for every call, i.e. for every focus node and constraint).
// The source returns plain arrays, not streams: shacl-engine wraps matches in readable-stream, whose browser stand-in for
// process.nextTick uses setTimeout (>= 4 ms per step in browsers); with one stream per FILTER NOT EXISTS row that made
// the cross-checks 6x slower in the browser than in Node (2026-11-12). countQuads saves Comunica a second match() per
// pattern for its cardinality estimate.
function makeSelect(dataset) {
  const engine = new QueryEngine();
  const source = {
    match: (s, p, o, g) => [...dataset.match(s, p, o, g)],
    countQuads: (s, p, o, g) => dataset.match(s, p, o, g).size,
  };
  const bf = new BindingsFactory(rdf);
  return async (query, bindings = []) => {
    const stream = await engine.queryBindings(query, { sources: [source], initialBindings: bf.bindings(bindings) });
    return stream.toArray();
  };
}
const REPORT_GRAPH = 'urn:lodviz:report';
const termKey = (t) => `${t.termType}|${t.value}`;

function parseInto(ds, text, format, blankNodePrefix) {
  // default graph only: shacl-engine and the queries see one graph
  for (const q of new N3Parser({ format, blankNodePrefix }).parse(text)) ds.add(rdf.quad(q.subject, q.predicate, q.object));
  return ds;
}

// PREFIX lines of a sh:prefixes node (with owl:imports), as shacl-engine does
function prefixLines(ptr, out = []) {
  for (const imp of ptr.out([ns.owl.imports])) prefixLines(imp, out);
  for (const d of ptr.out([ns.sh.declare])) out.push(`PREFIX ${d.out([ns.sh.prefix]).value}: <${d.out([ns.sh.namespace]).value}>`);
  return out;
}

function queryOf(sparqlPtr, shapePath) {
  const prefixes = [];
  for (const p of sparqlPtr.out([ns.sh.prefixes])) prefixLines(p, prefixes);
  return [...new Set(prefixes), sparqlPtr.out([ns.sh.select]).value].filter(Boolean).join('\n')
    .split('$PATH').join(shapePath ? stringifyPath(shapePath) : '$PATH');
}

// A query can run once over the whole data (instead of once per focus node with $this pre-bound) when that gives the
// same rows: a SELECT that projects $this (or *), binds $this in a top-level triple pattern (so the pre-bound value
// only filters rows), and has no subquery, VALUES, aggregate, GROUP BY, HAVING, LIMIT or OFFSET (which pre-binding
// would change). Anything not parsable or unusual is treated as unsafe.
// Also unsafe: UNION inside FILTER (NOT) EXISTS or MINUS, and MINUS with UNION. Comunica 5.4.1 evaluates
// `$this p ?a . FILTER NOT EXISTS { { $this q ?a } UNION { $this r ?a } }` correctly with $this pre-bound but returns
// no rows with $this unbound (found 2026-11-12 on the association shapes; two separate NOT EXISTS work).
const sparqlParser = new SparqlParser();
function isSafe(query) {
  if (query.includes('$PATH')) return false;
  let q;
  try { q = sparqlParser.parse(query); } catch { return false; }
  if (q.queryType !== 'SELECT' || q.group || q.having || q.limit !== undefined || q.offset !== undefined || q.values) return false;
  const vars = q.variables || [];
  const projectsThis = vars.some((v) => v.termType === 'Wildcard' || (v.termType === 'Variable' && v.value === 'this'));
  if (!projectsThis || vars.some((v) => v.expression)) return false;
  const isThis = (t) => t && t.termType === 'Variable' && t.value === 'this';
  const topLevel = (q.where || []).some((p) => p.type === 'bgp' && p.triples.some((t) => isThis(t.subject) || isThis(t.object)));
  let nested = false;
  const walk = (x) => {
    if (!x || typeof x !== 'object' || nested) return;
    if (Array.isArray(x)) { x.forEach(walk); return; }
    if (x.type === 'query' || x.type === 'values' || x.type === 'aggregate') { nested = true; return; }
    if ((x.type === 'operation' && (x.operator === 'notexists' || x.operator === 'exists')) || x.type === 'minus') {
      if (JSON.stringify(x).includes('"type":"union"')) { nested = true; return; }
    }
    Object.values(x).forEach(walk);
  };
  walk(q.where);
  return topLevel && !nested;
}

// sh:sparql validations: one check per sh:sparql node (correction 1); rows of safe queries come from `cache`
function makeValidations(cache, select) {
  const compileOne = (shape, sparqlPtr) => {
    if (sparqlPtr.out([ns.sh.deactivated]).value === 'true') return null;
    const query = queryOf(sparqlPtr, shape.path);
    const message = sparqlPtr.out([ns.sh.message]).terms;
    const source = sparqlPtr.terms;
    const pre = cache.get(termKey(sparqlPtr.term));
    return async (context) => {
      const rows = pre ? (pre.get(termKey(context.focusNode.term)) || [])
        : await select(query, [[context.factory.variable('this'), context.focusNode.term]]);
      for (const row of rows) {
        const args = bindingsToObject(row);
        const path = row.has('path') && parsePath(context.focusNode.node([row.get('path')]));
        const value = context.focusNode.node([row.get('value') || context.focusNode.term]);
        context.violation(ns.sh.SPARQLConstraintComponent, { args, message, path, source, value });
      }
      if (rows.length === 0) context.debug(ns.sh.SPARQLConstraintComponent, { source });
    };
  };
  const compileSparql = (shape) => {
    const checks = [...shape.sparql].map((p) => compileOne(shape, p)).filter(Boolean);
    return { generic: async (context) => { for (const c of checks) await c(context); } };
  };
  return new TermMap([[ns.sh.sparql, compileSparql]]);
}

/**
 * Validate data against shapes.
 * @param {object} o
 * @param {string} o.dataNq       the data as N-Quads (graphs are ignored); blank-node labels are kept as written
 * @param {string[]} o.shapes     Turtle texts of the shape files
 * @param {string} [o.vocab]      Turtle text of the vocabulary (class hierarchy), added to data and shapes
 * @param {(p: {phase: string, done: number, total: number}) => void} [o.onProgress]
 * @returns {Promise<{reportNq: string, conforms: boolean, counts: object, seconds: object, sparql: object}>}
 *   reportNq: the report in graph urn:lodviz:report; data blank nodes keep their labels, the report's own blank
 *   nodes get the prefix "lodvizr_" so they cannot clash with data labels.
 */
export async function validate({ dataNq, shapes, vocab = '', onProgress = () => {} }) {
  const t0 = performance.now();
  const data = parseInto(rdf.dataset(), dataNq, 'N-Quads', '');
  const shapesDs = rdf.dataset();
  for (const s of shapes) parseInto(shapesDs, s, 'Turtle');
  if (vocab) { parseInto(data, vocab, 'Turtle'); parseInto(shapesDs, vocab, 'Turtle'); } // correction 2
  const t1 = performance.now();

  // SPARQL constraints: the safe ones run once over the whole data (speed-up)
  const shapePtr = rdf.grapoi({ dataset: shapesDs });
  const constraints = [...shapesDs.match(null, rdf.namedNode(SH + 'sparql'))].map((q) => q.object);
  const safe = [], unsafe = [];
  for (const c of constraints) {
    const ptr = shapePtr.node([c]);
    if (ptr.out([ns.sh.deactivated]).value === 'true') continue;
    const query = queryOf(ptr, null);
    (isSafe(query) ? safe : unsafe).push({ c, query });
  }
  const cache = new Map();
  const select = makeSelect(data);
  const queryTimes = []; // [seconds, rows, first line of the query] per safe query, for diagnostics
  const total = safe.length + 1;
  for (const [i, { c, query }] of safe.entries()) {
    onProgress({ phase: `cross-check ${i + 1} of ${safe.length}`, done: i, total });
    const tq = performance.now();
    const rows = await select(query);
    queryTimes.push([(performance.now() - tq) / 1000, rows.length, query.split(/\n/).find((l) => /SELECT/i.test(l))?.trim().slice(0, 60)]);
    const byFocus = new Map();
    for (const row of rows) {
      const t = row.get('this');
      if (!t) continue;
      const k = termKey(t);
      if (!byFocus.has(k)) byFocus.set(k, []);
      byFocus.get(k).push(row);
    }
    cache.set(termKey(c), byFocus);
  }
  const t2 = performance.now();
  onProgress({ phase: unsafe.length ? `basic rules and ${unsafe.length} slow cross-checks` : 'basic rules', done: safe.length, total });

  const validator = new Validator(shapesDs, { factory: rdf, targetResolvers, validations: makeValidations(cache, select) });
  const report = await validator.validate({ dataset: data });
  const t3 = performance.now();
  onProgress({ phase: 'report', done: total, total });

  // report quads: the constraint's own message for SPARQL results (correction 3); report blank nodes renamed
  const rds = report.dataset;
  const msgOf = (c) => [...shapesDs.match(c, rdf.namedNode(SH + 'message'))].map((q) => q.object);
  const dataBlanks = new Set();
  for (const q of data) for (const t of [q.subject, q.object]) if (t.termType === 'BlankNode') dataBlanks.add(t.value);
  const ren = (t) => (t.termType === 'BlankNode' && !dataBlanks.has(t.value) ? rdf.blankNode('lodvizr_' + t.value) : t);
  const g = rdf.namedNode(REPORT_GRAPH);
  const out = [];
  const replaced = new Set();
  for (const q of rds.match(null, rdf.namedNode(SH + 'sourceConstraint'))) {
    const isSparql = rds.match(q.subject, rdf.namedNode(SH + 'sourceConstraintComponent'), rdf.namedNode(SH + 'SPARQLConstraintComponent')).size > 0;
    const msgs = isSparql ? msgOf(q.object) : [];
    if (msgs.length) {
      replaced.add(termKey(q.subject));
      for (const m of msgs) out.push(rdf.quad(ren(q.subject), rdf.namedNode(SH + 'resultMessage'), m, g));
    }
  }
  for (const q of rds) {
    if (q.predicate.value === SH + 'resultMessage' && replaced.has(termKey(q.subject))) continue;
    out.push(rdf.quad(ren(q.subject), q.predicate, ren(q.object), g));
  }
  const reportNq = new Writer({ format: 'N-Quads' }).quadsToString(out);

  const counts = { violation: 0, warning: 0, info: 0 };
  for (const r of report.results) {
    const sev = r.severity.value.replace(SH, '').toLowerCase();
    if (sev in counts) counts[sev]++;
  }
  return {
    reportNq, conforms: report.conforms, counts,
    triples: data.size,
    seconds: { parse: (t1 - t0) / 1000, sparql: (t2 - t1) / 1000, core: (t3 - t2) / 1000, total: (performance.now() - t0) / 1000 },
    sparql: { safe: safe.length, perNode: unsafe.length, queryTimes },
  };
}
