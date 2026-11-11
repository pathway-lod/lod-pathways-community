// Knowledge-graph stubs (2026-11-11): cards for knowledge-graph nodes the file points to but does not describe, taken
// from the snapshot (tools/build_pmw_snapshot.py), so that claims anchored to the same node meet on one card and
// claims anchored to different nodes are linked where the knowledge graph links those nodes.
//   - a pathway anchor:   title, key, group and classes, link to the current IRI
//   - another anchor:     "in n pathways" (e.g. a metabolite) and a part-of edge to every pathway anchored in the view
//   - shared pathways:    pathways that at least two non-hub anchors of the view are part of (most shared first, at
//                         most MAX_SHARED) are added as cards too, with their part-of edges: they connect graphs
// The triples go into a COPY of the graph index (out/inc), with origin 'plantmetwiki' (so they look like knowledge
// graph content) and the flag `stub` (so exports leave them out). Knows no vocabulary (rule 1): rdfs: only, and the
// part-of predicate comes from the snapshot.
import { DataFactory } from 'n3';
import { HUB } from './kgMap.js';

const { namedNode, literal } = DataFactory;
const RDFS = 'http://www.w3.org/2000/01/rdf-schema#';
const MAX_SHARED = 30;

export function withKgStubs(g, claimIds, anchoredTo, S, name = 'knowledge graph') {
  const anchors = [];
  const seen = new Set();
  for (const c of claimIds) for (const t of g.out.get(c) || []) {
    const a = t.o.value;
    if (anchoredTo.has(t.p.value) && t.o.termType === 'NamedNode' && !g.out.has(a) && !seen.has(a)) { seen.add(a); anchors.push(a); }
  }
  if (!anchors.length) return g;
  const out = new Map(g.out), inc = new Map(g.inc);
  const add = (s, p, o) => {
    const t = { s: namedNode(s), p: namedNode(p), o, origins: new Set(['plantmetwiki']), stub: true };
    out.set(s, [...(out.get(s) || []), t]);
    if (o.termType !== 'Literal') inc.set(o.value, [...(inc.get(o.value) || []), t]);
  };
  const partOf = S.snap.partOf || RDFS + 'seeAlso';
  const pw = S.snap.pathways;
  const describe = (iri, i) => {
    const [k, title, gi, cls, cur] = pw[i];
    add(iri, RDFS + 'label', literal(title));
    add(iri, RDFS + 'comment', literal(`${k} · ${S.snap.groups[gi]}${cls.length ? ' · ' + cls.join(', ') : ''}`));
    if (cur !== iri) add(iri, RDFS + 'seeAlso', namedNode(cur));
  };
  // pathway anchors: anchor IRI = a pathway IRI of the snapshot or an alias of one
  const pathOf = new Map(); // pathway index -> IRI used for it in this view
  for (const a of anchors) {
    const ps = S.byIri.get(a);
    if (ps?.length === 1 && (pw[ps[0]][4] === a || S.snap.alias?.[a] === ps[0]) && !pathOf.has(ps[0])) pathOf.set(ps[0], a);
  }
  for (const [i, a] of pathOf) describe(a, i);
  // other anchors (e.g. metabolites)
  const shared = new Map(); // pathway index -> anchors in it
  for (const a of anchors) {
    const ps = S.byIri.get(a);
    if (!ps) { add(a, RDFS + 'comment', literal(`not found in the ${name} snapshot`)); continue; }
    if (pathOf.get(ps[0]) === a) continue;
    add(a, RDFS + 'comment', literal(`in ${ps.length} ${name} pathway${ps.length === 1 ? '' : 's'}${ps.length > HUB ? ' (very common)' : ''}`));
    for (const p of ps) {
      if (pathOf.has(p)) add(a, partOf, namedNode(pathOf.get(p)));
      else if (ps.length <= HUB) { if (!shared.has(p)) shared.set(p, []); shared.get(p).push(a); }
    }
  }
  const top = [...shared.entries()].filter(([, as]) => as.length >= 2)
    .sort((x, y) => y[1].length - x[1].length || x[0] - y[0]).slice(0, MAX_SHARED);
  for (const [i, as] of top) {
    const iri = pw[i][4];
    describe(iri, i);
    for (const a of as) add(a, partOf, namedNode(iri));
  }
  return { ...g, out, inc };
}
