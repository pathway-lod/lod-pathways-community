// Links between claims (2026-11-11): two claims are "siblings" when they point at the same node, directly
// (claim -> node) or through one of their evidence nodes (claim -> evidence -> node). Examples in the pilots: two
// annotations of the same feature, claims anchored to the same metabolite or pathway, evidence citing the same paper.
// Knows no vocabulary (rule 1): it uses the roles from the profile and only the RDF core predicates below.

const RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#';
// rdf:type: classes are not shared data; rdf:predicate: every reified statement of one kind shares its predicate
const SKIP = new Set([RDF + 'type', RDF + 'predicate']);
export const DRAW_MAX = 30; // a node shared by more claims than this is listed, not drawn as arcs

const keyOf = (t) => (t.termType === 'BlankNode' ? '_:' + t.value : t.value);

// Kind of a link, from HOW the claims reach the shared node (Martin, 2026-11-11):
//   'kg'     same knowledge-graph annotation: the node has role kg, or is reached by a predicate the profile lists in
//            pattern.sameEntity (e.g. another identifier of the anchored compound)
//   'data'   same data point: the claim points at the node directly (e.g. the measured feature)
//   'source' same source: the node is reached only through evidence (e.g. the cited paper)
const KIND_RANK = { kg: 0, data: 1, source: 2 };

// -> { byNode: Map node -> {claims: [id], via: Set(predicate IRI), role, kind}, ofClaim: Map id -> [node] }
//    only nodes shared by at least two claims are kept
export function sharedNodes(g, claimIds, roleOf, { sameEntity = new Set() } = {}) {
  const isClaim = new Set(claimIds);
  const byNode = new Map();
  const add = (c, node, p, kind) => {
    if (!byNode.has(node)) byNode.set(node, { claims: [], via: new Set(), role: roleOf(node), kind });
    const e = byNode.get(node);
    if (e.claims[e.claims.length - 1] !== c) e.claims.push(c);
    e.via.add(p);
    if (KIND_RANK[kind] < KIND_RANK[e.kind]) e.kind = kind;
  };
  for (const c of claimIds) {
    for (const t of g.out.get(c) || []) {
      if (t.o.termType === 'Literal' || SKIP.has(t.p.value)) continue;
      const o = keyOf(t.o);
      if (isClaim.has(o)) continue; // claim-to-claim links are edges of their own, not shared nodes
      const r = roleOf(o);
      if (r === 'run') continue;
      if (r === 'evidence') {
        for (const t2 of g.out.get(o) || []) {
          if (t2.o.termType === 'Literal' || SKIP.has(t2.p.value)) continue;
          const o2 = keyOf(t2.o);
          const r2 = roleOf(o2);
          if (r2 === 'run' || r2 === 'evidence' || isClaim.has(o2)) continue;
          add(c, o2, t2.p.value, r2 === 'kg' ? 'kg' : 'source');
        }
        continue;
      }
      add(c, o, t.p.value, r === 'kg' || sameEntity.has(t.p.value) ? 'kg' : 'data');
    }
  }
  for (const [n, e] of byNode) if (e.claims.length < 2) byNode.delete(n);
  const ofClaim = new Map();
  for (const [n, e] of byNode) for (const c of e.claims) {
    if (!ofClaim.has(c)) ofClaim.set(c, []);
    ofClaim.get(c).push(n);
  }
  // most specific link first (fewest claims); on ties kg, then data, then source; then by key
  const r = (n) => KIND_RANK[byNode.get(n).kind];
  for (const ns of ofClaim.values())
    ns.sort((a, b) => byNode.get(a).claims.length - byNode.get(b).claims.length || r(a) - r(b) || (a < b ? -1 : 1));
  return { byNode, ofClaim };
}

// claim -> [{other, node, kind}] for arcs: each sibling once, via its most specific shared node; big nodes skipped
export function siblingArcs(S, id) {
  const seen = new Set([id]), out = [];
  for (const n of S.ofClaim.get(id) || []) {
    const e = S.byNode.get(n);
    if (e.claims.length > DRAW_MAX) continue;
    for (const o of e.claims) if (!seen.has(o)) { seen.add(o); out.push({ other: o, node: n, kind: e.kind }); }
  }
  return out;
}
