// Cards, rows and edges for the current subset. Vocabulary comes from the profile (P), roles from roleOf,
// term status from the optional term table, problems from the optional SHACL report and the pattern checks.
import { RDF_TYPE, key } from './rdf.js';
import { termInfo, titleFor, patternChecks } from './profile.js';

const fmtNumber = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? String(Number(n.toPrecision(10))) : v;
};
const literalText = (o) => (/#(double|decimal|float|integer|int|long)$/.test(o.datatype?.value || '') ? fmtNumber(o.value) : `"${o.value}"`);
const originState = (origins) => (origins.has('proposal') && origins.size === 1 ? 'proposal' : 'data');
const ORDER = { violation: 0, warning: 1, pattern: 2, info: 3 };

export function buildView(g, keep, { P, roleOf, L, terms, runsAsCards = false }) {
  const isCard = (k) => keep.has(k) && g.out.has(k) && (runsAsCards || roleOf(k) !== 'run');
  const cards = new Map();
  const edges = new Map();

  for (const k of keep) {
    if (!isCard(k)) continue;
    const role = roleOf(k);
    const rowsByPred = new Map();
    const outs = g.out.get(k) || [];
    for (const t of outs) {
      const o = key(t.o);
      if (t.o.termType !== 'Literal' && isCard(o)) {
        const ek = `${k}->${o}`;
        if (!edges.has(ek)) edges.set(ek, { id: ek, source: k, target: o, preds: [], states: new Set() });
        edges.get(ek).preds.push(t.p.value);
        edges.get(ek).states.add(originState(t.origins));
        continue;
      }
      const p = t.p.value;
      if (!rowsByPred.has(p)) rowsByPred.set(p, { pred: p, isType: p === RDF_TYPE, values: [], issues: [], reqs: new Set() });
      const row = rowsByPred.get(p);
      const v = { state: originState(t.origins) };
      if (t.o.termType === 'Literal') v.text = literalText(t.o);
      else if (p === RDF_TYPE) {
        const ti = termInfo(t.o.value, terms, P);
        v.text = P.compact(t.o.value); v.note = L.termLabel(t.o.value); v.status = ti.status; v.unlisted = ti.unlisted;
        ti.reqs.forEach((r) => row.reqs.add(r));
      } else if (roleOf(o) === 'run' && g.out.has(o)) {
        v.text = '→ ' + L.runSummary(o); v.ref = o;
      } else if (t.o.termType === 'BlankNode') {
        v.text = '[blank node, not shown]';
      } else {
        v.text = '→ ' + P.compact(t.o.value); v.note = L.termLabel(t.o.value) || L.labelOf(o); v.href = t.o.value;
      }
      row.values.push(v);
    }
    const rows = [...rowsByPred.values()].map((row) => {
      if (row.isType) {
        const st = row.values.map((v) => v.status);
        row.status = st.includes('local') ? 'local' : st.includes('reuse') ? 'reuse' : st[0] || 'none';
        row.unlisted = row.values.every((v) => v.unlisted);
      } else {
        const ti = termInfo(row.pred, terms, P);
        row.status = ti.status; row.unlisted = ti.unlisted; row.predNote = ti.label || L.termLabel(row.pred);
        ti.reqs.forEach((r) => row.reqs.add(r));
      }
      if (role === 'kg') { row.status = 'kg'; row.unlisted = false; }
      row.state = row.values.every((v) => v.state === 'proposal') ? 'proposal' : 'data';
      row.reqs = [...row.reqs];
      return row;
    });
    rows.sort((a, b) => b.isType - a.isType);
    const states = new Set(outs.map((t) => originState(t.origins)));
    cards.set(k, {
      id: k, role, rows, issues: [],
      iri: k.startsWith('_:') ? null : k,
      state: states.size === 1 && states.has('proposal') ? 'proposal' : 'data',
      title: titleFor(g, k, role, P, L),
    });
  }

  // problems -> rows (missing or wrong value) or the card footer
  const problems = [...g.results, ...patternChecks(g, P, roleOf, [...cards.keys()])];
  for (const r of problems) {
    const card = cards.get(r.focus);
    if (!card) {
      for (const c of cards.values()) for (const row of c.rows)
        if (row.values.some((v) => v.ref === r.focus)) row.issues.push({ ...r, via: P.compact(r.focus) });
      continue;
    }
    if (r.path) {
      let row = card.rows.find((x) => x.pred === r.path);
      if (!row) {
        const ti = termInfo(r.path, terms, P);
        row = { pred: r.path, values: [], issues: [], reqs: ti.reqs, status: ti.status, missing: true, state: 'data' };
        card.rows.push(row);
      }
      row.issues.push(r);
    } else card.issues.push(r);
  }
  for (const c of cards.values()) c.issues.sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);

  const edgeList = [...edges.values()].map((e) => ({
    ...e,
    label: [...new Set(e.preds.map((p) => {
      if (P.predLabels[p]) return P.predLabels[p];
      const c = P.compact(p);
      const l = L.termLabel(p);
      return /^[A-Z]+:\d/.test(c) && l ? l : c;
    }))].join('  ·  '),
    state: e.states.has('data') ? 'data' : 'proposal',
  }));
  return { cards, edges: edgeList };
}
