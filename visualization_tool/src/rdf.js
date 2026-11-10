// RDF core: parsing, indexing, CURIEs, subsets. Knows NO evidence vocabulary (that is in the profile).
// Named graphs urn:lodviz:<origin> tell where a triple comes from; two origins are special:
//   report  a SHACL validation report (sh:ValidationResult ...), read as results, not drawn
//   vocab   the vocabulary/ontology (class hierarchy, labels), used for reasoning and labels, not drawn
import { Parser, Writer } from 'n3';

export const RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
const SUBCLASS = 'http://www.w3.org/2000/01/rdf-schema#subClassOf';
const RDFS_LABEL = 'http://www.w3.org/2000/01/rdf-schema#label';
const SH = 'http://www.w3.org/ns/shacl#';
const OBO = 'http://purl.obolibrary.org/obo/';
const ORIGIN_NS = 'urn:lodviz:';

export const key = (t) => (t.termType === 'BlankNode' ? '_:' + t.value : t.value);

export function makeCompact(prefixes) {
  const list = Object.entries(prefixes).filter(([p]) => p !== 'obo').sort((a, b) => b[1].length - a[1].length);
  return (iri) => {
    if (iri.startsWith(OBO)) return iri.slice(OBO.length).replace('_', ':'); // OBO convention: ECO_0001580 -> ECO:0001580
    for (const [p, ns] of list) if (iri.startsWith(ns)) return `${p}:${iri.slice(ns.length)}`;
    return iri.length > 60 ? iri.slice(0, 57) + '…' : iri;
  };
}

export function expand(curie, prefixes) {
  const i = curie.indexOf(':');
  const p = curie.slice(0, i);
  return prefixes[p] && !curie.startsWith('http') ? prefixes[p] + curie.slice(i + 1) : curie;
}

export function parseRdf(text, filename = '') {
  const lower = filename.toLowerCase();
  const format = lower.endsWith('.nq') ? 'N-Quads' : lower.endsWith('.trig') ? 'TriG'
    : lower.endsWith('.nt') ? 'N-Triples' : lower.endsWith('.ttl') ? 'Turtle' : 'TriG';
  const prefixes = {};
  const quads = new Parser({ format }).parse(text, null, (p, iri) => { if (p) prefixes[p] = iri.value; });
  quads.prefixes = prefixes; // the file's own @prefix lines: used for CURIEs when no profile gives them
  return quads;
}

const originOf = (q) => (q.graph.termType === 'DefaultGraph' ? 'loaded'
  : q.graph.value.startsWith(ORIGIN_NS) ? q.graph.value.slice(ORIGIN_NS.length) : q.graph.value);

export function indexGraph(quads) {
  const triples = new Map();
  const report = [];
  const superOf = new Map(); // class -> direct superclasses (from vocab and data)
  const vocabLabels = new Map();
  for (const q of quads) {
    const origin = originOf(q);
    if (q.predicate.value === SUBCLASS && q.object.termType === 'NamedNode') {
      if (!superOf.has(q.subject.value)) superOf.set(q.subject.value, new Set());
      superOf.get(q.subject.value).add(q.object.value);
    }
    if (origin === 'report') { report.push(q); continue; }
    if (origin === 'vocab') {
      if (q.predicate.value === RDFS_LABEL && !vocabLabels.has(q.subject.value)) vocabLabels.set(q.subject.value, q.object.value);
      continue;
    }
    const k = `${key(q.subject)}|${q.predicate.value}|${key(q.object)}|${q.object.datatype?.value ?? ''}`;
    if (!triples.has(k)) triples.set(k, { s: q.subject, p: q.predicate, o: q.object, origins: new Set() });
    triples.get(k).origins.add(origin);
  }
  const out = new Map(); const inc = new Map();
  for (const t of triples.values()) {
    const s = key(t.s), o = key(t.o);
    if (!out.has(s)) out.set(s, []);
    out.get(s).push(t);
    if (t.o.termType !== 'Literal') { if (!inc.has(o)) inc.set(o, []); inc.get(o).push(t); }
  }
  const supers = (cls, seen = new Set()) => {
    if (seen.has(cls)) return seen;
    seen.add(cls);
    for (const s of superOf.get(cls) || []) supers(s, seen);
    return seen;
  };
  return { out, inc, results: readReport(report), hasReport: report.length > 0, quads, supers, vocabLabels, filePrefixes: quads.prefixes || {} };
}

function readReport(quads) {
  const by = new Map();
  for (const q of quads) {
    const s = key(q.subject);
    if (!by.has(s)) by.set(s, {});
    by.get(s)[q.predicate.value.replace(SH, '')] = q.object;
  }
  const res = [];
  for (const r of by.values()) {
    if (!r.focusNode || !r.resultSeverity) continue;
    res.push({
      focus: key(r.focusNode),
      path: r.resultPath?.termType === 'NamedNode' ? r.resultPath.value : null,
      value: r.value ? key(r.value) : null,
      severity: r.resultSeverity.value.replace(SH, '').toLowerCase(), // violation | warning | info
      message: r.resultMessage?.value ?? '',
      source: 'SHACL',
    });
  }
  return res;
}

export const typesOf = (g, k) => (g.out.get(k) || []).filter((t) => t.p.value === RDF_TYPE).map((t) => t.o.value);
export const valueOf = (g, k, p) => (g.out.get(k) || []).find((t) => t.p.value === p)?.o.value;
export const objectsOf = (g, k) => (g.out.get(k) || []).filter((t) => t.o.termType !== 'Literal').map((t) => key(t.o));

// Subset ("focus"): one claim and its neighbourhood. null = every subject.
export function focusSet(g, claimKey, roleOf) {
  if (!claimKey) return new Set(g.out.keys());
  const keep = new Set([claimKey]);
  const add = (k) => { if (g.out.has(k)) keep.add(k); };
  for (const o of objectsOf(g, claimKey)) { add(o); for (const o2 of objectsOf(g, o)) add(o2); } // evidence -> run
  // knowledge-graph context: follow KG-to-KG links (e.g. metabolite -> pathways)
  for (const k of [...keep]) if (roleOf(k) === 'kg')
    for (const o of objectsOf(g, k)) if (g.out.has(o) && roleOf(o) === 'kg') keep.add(o);
  // data nodes that point at kept data nodes (but not other claims)
  for (const k of [...keep]) if (roleOf(k) === 'data')
    for (const t of g.inc.get(k) || []) { const s = key(t.s); if (roleOf(s) !== 'claim') keep.add(s); }
  return keep;
}

export function turtleOf(g, k, prefixes) {
  const w = new Writer({ prefixes });
  const seen = new Set();
  const walk = (s) => {
    if (seen.has(s)) return; seen.add(s);
    for (const t of g.out.get(s) || []) {
      w.addQuad(t.s, t.p, t.o);
      if (t.o.termType === 'BlankNode') walk(key(t.o));
    }
  };
  walk(k);
  let text = '';
  w.end((_, r) => { text = r; });
  return text;
}
