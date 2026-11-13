// Everything that depends on the evidence vocabulary, driven by a profile (public/profiles/*.json).
// Roles: claim | evidence | run | kg (existing knowledge graph node) | data (anything else).
import { RDF_TYPE, expand, makeCompact, typesOf, valueOf, key } from './rdf.js';

const set = (list, P) => new Set((list || []).map((c) => expand(c, P.prefixes)));

export function loadProfile(json) {
  const P = { ...json, prefixes: json.prefixes || {} };
  const r = json.roles || {};
  P.claimClasses = set(r.claim?.classes, P); P.claimHas = set(r.claim?.hasPredicates, P);
  P.evidenceObjectOf = set(r.evidence?.objectOf, P);
  P.runClasses = set(r.run?.classes, P); P.runObjectOf = set(r.run?.objectOf, P); P.runSummary = (r.run?.summary || []).map((c) => expand(c, P.prefixes));
  P.kgObjectOf = set(r.kg?.objectOf, P); P.kgGraphs = new Set(r.kg?.graphs || []);
  P.kgNamespaces = (r.kg?.namespaces || []).map((c) => expand(c, P.prefixes));
  P.kgClassNamespaces = (r.kg?.classNamespaces || []).map((c) => expand(c, P.prefixes));
  P.hasEvidence = set(json.pattern?.hasEvidence, P); P.generatedBy = set(json.pattern?.generatedBy, P);
  P.anchoredTo = set(json.pattern?.anchoredTo, P);
  P.sameEntity = set(json.pattern?.sameEntity, P); // links that name the same entity as the anchor (global view links)
  const ns = (l) => (l || []).map((c) => expand(c, P.prefixes));
  P.localNs = ns(json.terms?.localNamespaces); P.kgVocabNs = ns(json.terms?.kgVocabularyNamespaces); P.genericNs = ns(json.terms?.generic);
  P.labelProps = ns(json.titles?.labelProperties);
  P.titleByClass = Object.fromEntries(Object.entries(json.titles?.byClass || {}).map(([c, ps]) => [expand(c, P.prefixes), ns(ps)]));
  P.predLabels = Object.fromEntries(Object.entries(json.predicateLabels || {}).map(([c, l]) => [expand(c, P.prefixes), l]));
  P.roleLabels = Object.fromEntries(['claim', 'evidence', 'run', 'kg'].map((k) => [k, r[k]?.label || k]).concat([['data', 'data']]));
  P.compact = makeCompact(P.prefixes);
  return P;
}

const startsAny = (iri, list) => list.some((ns) => iri.startsWith(ns));

export function makeRoles(g, P) {
  const cache = new Map();
  const isA = (k, classes) => classes.size && typesOf(g, k).some((t) => [...g.supers(t)].some((c) => classes.has(c)));
  const roleOf = (k) => {
    if (cache.has(k)) return cache.get(k);
    const outs = g.out.get(k) || [], ins = g.inc.get(k) || [];
    let role = 'data';
    if (outs.some((t) => [...t.origins].some((o) => P.kgGraphs.has(o))) || (!k.startsWith('_:') && startsAny(k, P.kgNamespaces))
      || typesOf(g, k).some((t) => startsAny(t, P.kgClassNamespaces)) || ins.some((t) => P.kgObjectOf.has(t.p.value))) role = 'kg';
    else if (isA(k, P.claimClasses) || outs.some((t) => P.claimHas.has(t.p.value))) role = 'claim';
    else if (ins.some((t) => P.evidenceObjectOf.has(t.p.value))) role = 'evidence';
    else if (isA(k, P.runClasses) || ins.some((t) => P.runObjectOf.has(t.p.value))) role = 'run';
    // run part (2026-11-13, D40): a node with triples that only runs (or other run parts) point to, e.g. the run's
    // software agent, its parameter set, the organisation behind the agent, belongs to the run. A node that a claim,
    // evidence or data node also points to (e.g. a dataset the run used and a feature names) stays data.
    // Provisional 'data' in the cache stops cycles.
    else if (outs.length && ins.length) {
      cache.set(k, 'data');
      if (ins.every((t) => { const s = key(t.s); return s !== k && roleOf(s) === 'run'; })) role = 'run';
    }
    cache.set(k, role);
    return role;
  };
  return roleOf;
}

// --- labels and titles ---------------------------------------------------------------------------
export function makeLabels(g, P, terms) {
  const labelOf = (k) => {
    const ts = typesOf(g, k);
    for (const t of ts) for (const p of P.titleByClass[t] || []) { const v = valueOf(g, k, p); if (v) return v; }
    for (const p of P.labelProps) { const v = valueOf(g, k, p); if (v) return v; }
    return null;
  };
  const termLabel = (iri) => terms?.[iri]?.label || g.vocabLabels.get(iri) || null;
  const typeName = (k) => {
    const t = typesOf(g, k)[0];
    if (!t) return null;
    const c = P.compact(t);
    return /^[A-Z]+:\d/.test(c) ? termLabel(t) || c : c.split(':').pop();
  };
  const runSummary = (k) => {
    const parts = P.runSummary.map((p) => valueOf(g, k, p)).filter(Boolean);
    return parts.length ? parts.join(' ') : labelOf(k) || P.compact(k);
  };
  return { labelOf, termLabel, typeName, runSummary };
}

export function titleFor(g, k, role, P, L) {
  const tn = L.typeName(k);
  const lab = L.labelOf(k);
  if (role === 'claim') {
    const anchors = (g.out.get(k) || []).filter((t) => P.anchoredTo.has(t.p.value)).map((t) => L.labelOf(key(t.o)) || P.compact(t.o.value));
    return `${tn || 'Claim'} · ${anchors.length ? '→ ' + anchors.join(', ') : 'not anchored'}`;
  }
  if (role === 'evidence') {
    const run = (g.out.get(k) || []).find((t) => P.generatedBy.has(t.p.value));
    return `Evidence · ${run ? L.runSummary(key(run.o)) : lab || tn || ''}`;
  }
  // a run with software/version: its summary; a run part (agent, parameter set; D40): type and label as other cards
  if (role === 'run' && P.runSummary.some((p) => valueOf(g, k, p))) return L.runSummary(k);
  if (tn && lab) return `${tn} · ${lab}`;
  return lab || tn || (k.startsWith('_:') ? 'blank node' : P.compact(k));
}

// --- term status (overlay: only when a term table is loaded) --------------------------------------
export function termInfo(iri, terms, P) {
  if (startsAny(iri, P.kgVocabNs)) return { status: 'kg', reqs: [] };
  if (!terms) return { status: startsAny(iri, P.localNs) ? 'local' : 'none', reqs: [] };
  const t = terms[iri];
  if (t) {
    const actions = new Set(t.rows.map((r) => r.action));
    const status = actions.has('reuse') ? 'reuse' : actions.has('local_term') ? 'local'
      : actions.has('request_term') ? 'request' : actions.has('review') ? 'review' : 'listed';
    return { status, reqs: [...new Set(t.rows.map((r) => r.req_id))], label: t.label };
  }
  if (startsAny(iri, P.genericNs)) return { status: 'none', reqs: [] };
  if (startsAny(iri, P.localNs)) return { status: 'local', reqs: [], unlisted: true };
  return { status: 'unlisted', reqs: [], unlisted: true };
}

// --- pattern checks: need no ontology, only the profile -------------------------------------------
// Claim without evidence / anchor and evidence without provenance are only checked when the file has no SHACL
// report (the shapes say it better then). Orphans (not connected to any claim) are always checked.
export function patternChecks(g, P, roleOf, shown) {
  const res = [];
  const outs = (k) => g.out.get(k) || [];
  const claims = [...g.out.keys()].filter((k) => roleOf(k) === 'claim');
  if (!g.hasReport) {
    for (const k of shown) {
      const r = roleOf(k);
      if (r === 'claim' && !outs(k).some((t) => P.hasEvidence.has(t.p.value)))
        res.push({ focus: k, severity: 'pattern', message: 'Claim without evidence.' });
      if (r === 'claim' && P.anchoredTo.size && !outs(k).some((t) => P.anchoredTo.has(t.p.value)))
        res.push({ focus: k, severity: 'pattern', message: 'Claim not anchored to the knowledge graph.' });
      if (r === 'evidence' && !outs(k).some((t) => P.generatedBy.has(t.p.value)))
        res.push({ focus: k, severity: 'pattern', message: 'Evidence without provenance (no run that generated it).' });
    }
  }
  if (claims.length) {
    // undirected reachability from all claims
    const seen = new Set(claims), stack = [...claims];
    while (stack.length) {
      const k = stack.pop();
      for (const t of [...(g.out.get(k) || []), ...(g.inc.get(k) || [])]) {
        if (t.o.termType === 'Literal') continue;
        for (const n of [key(t.s), key(t.o)]) if (!seen.has(n)) { seen.add(n); stack.push(n); }
      }
    }
    for (const k of shown) if (!seen.has(k))
      res.push({ focus: k, severity: 'pattern', message: 'Not connected to any claim: nothing in the RDF links this node to a prediction or its evidence.' });
  }
  return res.map((r) => ({ ...r, source: 'pattern' }));
}
