// Score highlight in the global view (D36): which scores exist, how they are read and coloured.
// Knows no vocabulary: the scores are defined in a CSV named in the profile (`scores.definitions`), one row per score
// property: property, label, better (higher|lower), min, max (the score's theoretical range, which sets the colour
// scale), scale (linear|log), kind (numeric|ordinal; only numeric is drawn so far), order, attached_to (claim|evidence),
// status, note. A score on evidence is reached through the profile's hasEvidence predicates.
import { expand, key } from './rdf.js';

// small CSV reader: comma separated, double quotes around fields that contain commas, "" inside quotes
export function parseCsv(text) {
  const rows = [];
  let row = [], f = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"' && text[i + 1] === '"') { f += '"'; i++; }
      else if (c === '"') q = false;
      else f += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(f); f = '';
      if (row.some((x) => x !== '')) rows.push(row);
      row = [];
    } else f += c;
  }
  row.push(f);
  if (row.some((x) => x !== '')) rows.push(row);
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h.trim(), (r[i] ?? '').trim()])));
}

export function loadScoreDefs(text, prefixes) {
  return parseCsv(text).filter((r) => r.property).map((r) => ({
    iri: expand(r.property, prefixes), curie: r.property, label: r.label || r.property,
    better: r.better === 'lower' ? 'lower' : 'higher', min: Number(r.min), max: Number(r.max),
    scale: r.scale === 'log' ? 'log' : 'linear', kind: r.kind || 'numeric',
    order: r.order ? r.order.split('|') : [], attachedTo: r.attached_to || 'evidence',
    status: r.status || '', note: r.note || '',
  })).filter((d) => d.kind === 'numeric' && Number.isFinite(d.min) && Number.isFinite(d.max) && d.max > d.min
    && (d.scale === 'linear' || d.min > 0));
}

const isBetter = (def, a, b) => (def.better === 'lower' ? a < b : a > b);

// value of one score per claim; a claim with several values (several evidence nodes) takes its best one
export function claimScores(g, claimIds, def, hasEvidence) {
  const values = new Map();
  let multi = 0;
  const numbers = (k) => (g.out.get(k) || []).filter((t) => t.p.value === def.iri && t.o.termType === 'Literal')
    .map((t) => Number(t.o.value)).filter((v) => !Number.isNaN(v));
  for (const c of claimIds) {
    const nodes = def.attachedTo === 'claim' ? [c]
      : (g.out.get(c) || []).filter((t) => hasEvidence.has(t.p.value)).map((t) => key(t.o));
    const vs = nodes.flatMap(numbers);
    if (!vs.length) continue;
    if (vs.length > 1) multi++;
    values.set(c, vs.reduce((b, v) => (isBetter(def, v, b) ? v : b)));
  }
  return { values, multi };
}

// position on the colour scale: 0 = worst end, 1 = best end of the theoretical range; out = 'low' | 'high' | null
export function position(def, v) {
  const tr = (x) => (def.scale === 'log' ? Math.log10(x) : x);
  const lo = tr(def.min), hi = tr(def.max);
  const out = v < def.min ? 'low' : v > def.max ? 'high' : null;
  const x = v <= 0 && def.scale === 'log' ? lo : tr(Math.min(Math.max(v, def.min), def.max));
  const f = (x - lo) / (hi - lo);
  return { t: def.better === 'lower' ? 1 - f : f, out };
}

// sequential blue, light (worse) -> dark (better); dataviz reference ramp steps 250..700 (the light end still
// stands out on white, which small dots need)
const RAMP = ['#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b'];
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export function rampColor(t) {
  const x = Math.min(Math.max(t, 0), 1) * (RAMP.length - 1), i = Math.min(Math.floor(x), RAMP.length - 2), f = x - i;
  const a = rgb(RAMP[i]), b = rgb(RAMP[i + 1]);
  return '#' + a.map((v, j) => Math.round(v + (b[j] - v) * f).toString(16).padStart(2, '0')).join('');
}

// all scored claims, best first; equal values in claim-IRI order, so the top N is always the same set
export function ranking(def, values) {
  return [...values].sort((a, b) => (a[1] === b[1] ? (a[0] < b[0] ? -1 : 1) : isBetter(def, a[1], b[1]) ? -1 : 1));
}

export function summary(def, values) {
  const vs = [...values.values()].sort((a, b) => a - b);
  const n = vs.length;
  let low = 0, high = 0;
  for (const v of vs) { const { out } = position(def, v); if (out === 'low') low++; else if (out === 'high') high++; }
  return { n, min: vs[0], max: vs[n - 1], median: n ? (vs[(n - 1) >> 1] + vs[n >> 1]) / 2 : NaN, low, high };
}

// histogram over the theoretical range, worst end on the left; values outside go into the end bins
export function histogram(def, values, bins = 30) {
  const counts = new Array(bins).fill(0);
  for (const v of values.values()) counts[Math.min(bins - 1, Math.floor(position(def, v).t * bins))]++;
  return counts;
}

// value at position t of the scale (for axis labels)
export function valueAt(def, t) {
  const f = def.better === 'lower' ? 1 - t : t;
  if (def.scale === 'log') return 10 ** (Math.log10(def.min) + f * (Math.log10(def.max) - Math.log10(def.min)));
  return def.min + f * (def.max - def.min);
}

export const fmt = (v) => (v == null || Number.isNaN(v) ? '–' : v !== 0 && Math.abs(v) < 1e-3 ? v.toExponential(1)
  : Math.abs(v) >= 1000 ? String(Math.round(v)) : String(Number(v.toPrecision(3))));
