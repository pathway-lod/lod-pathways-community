// "Knowledge-graph map" layout of the global view (TEST, 2026-11-11). Alternative to globalLayout.js (the anchor
// ring); switch with ?layout=ring|kg. To drop this test: delete this file, kgDraw.js, tools/build_pmw_snapshot.py,
// tools/pmw_class_groups.csv, public/data/pmw_snapshot.json and the "kg" branches in Global.jsx.
//
// Picture: the knowledge graph (KG) as a fixed inner ring (groups -> pathways, same for every file), the claims of
// the file on an outer ring, sorted by the KG group they map to, and ribbons from each block of claims to the groups
// it reaches. Deterministic (rule 2): sorted, no forces. Knows no vocabulary (rule 1): it only reads the snapshot
// (groups, pathways, node IRI -> pathway indices) built by tools/build_pmw_snapshot.py.

export const HUB = 50; // an anchor in more pathways than this (water, H+, ...) is a "hub": it does not place a claim
const TAU = 2 * Math.PI;
const START = -Math.PI / 2; // 12 o'clock
const SECTOR_GAP = 0.004 * TAU;
const BLOCK_GAP = 0.008 * TAU;

// snapshot -> lookup structures
export function indexSnapshot(snap) {
  const byIri = new Map(Object.entries(snap.nodes));
  snap.pathways.forEach((p, i) => byIri.set(p[4], [i]));
  for (const [iri, i] of Object.entries(snap.alias || {})) if (!byIri.has(iri)) byIri.set(iri, [i]);
  const groupOf = snap.pathways.map((p) => p[2]);
  const nPerGroup = snap.groups.map(() => 0);
  groupOf.forEach((g) => nPerGroup[g]++);
  return { snap, byIri, groupOf, nPerGroup, G: snap.groups.length };
}

// claims [{id, anchors}] -> each claim with its pathway weights (sum 1 for a placed claim; an anchor with n pathways
// gives 1/n to each), group weights, kind ('mapped' | 'hub' = only hub anchors | 'none' = no anchor found in the KG),
// primary group (largest weight, ties to the earlier group) and primary pathway (for ordering inside a block)
export function mapClaims(claims, S, hub = HUB) {
  return claims.map((c) => {
    const found = c.anchors.map((a) => S.byIri.get(a)).filter(Boolean);
    const usable = found.filter((ps) => ps.length <= hub);
    const w = new Map(), gw = new Array(S.G).fill(0);
    for (const ps of usable) for (const p of ps) {
      const x = 1 / ps.length / usable.length;
      w.set(p, (w.get(p) || 0) + x);
      gw[S.groupOf[p]] += x;
    }
    const kind = usable.length ? 'mapped' : found.length ? 'hub' : 'none';
    let group = -1, first = -1;
    if (kind === 'mapped') {
      group = 0;
      for (let g = 1; g < S.G; g++) if (gw[g] > gw[group] + 1e-9) group = g;
      let best = -1;
      for (const [p, x] of w) if (S.groupOf[p] === group && (x > best + 1e-9 || (Math.abs(x - best) <= 1e-9 && p < first))) { best = x; first = p; }
    }
    return { ...c, w, gw, kind, group, first };
  });
}

const wrap = (a) => { a = (a + Math.PI) % TAU; return (a < 0 ? a + TAU : a) - Math.PI; }; // to (-pi, pi]

export function kgLayout(mapped, S, { spacing = 9 } = {}) {
  const { snap, G, nPerGroup } = S;
  const n = mapped.length;
  const R = Math.max(520, (n * spacing) / TAU);
  const r = { band0: 0.34 * R, band1: 0.46 * R, tick0: 0.475 * R, tick1: 0.56 * R, rib0: 0.57 * R, rib1: 0.94 * R, claims: R };

  // KG sectors: size = pathways x drawing weight
  const units = nPerGroup.map((k, g) => k * (snap.groupWeight?.[g] ?? 1));
  const U = units.reduce((s, x) => s + x, 0);
  const span = TAU - G * SECTOR_GAP;
  const sectors = [];
  const tick = new Array(snap.pathways.length);
  let a = START + SECTOR_GAP / 2, p = 0;
  for (let g = 0; g < G; g++) {
    const from = a, to = a + (span * units[g]) / U;
    for (let i = 0; i < nPerGroup[g]; i++, p++) // pathways are sorted by group in the snapshot
      tick[p] = { from: from + ((to - from) * i) / nPerGroup[g], to: from + ((to - from) * (i + 1)) / nPerGroup[g] };
    sectors.push({ g, from, to, mid: (from + to) / 2, n: nPerGroup[g], scaled: (snap.groupWeight?.[g] ?? 1) !== 1 });
    a = to + SECTOR_GAP;
  }

  // coverage: claims per pathway, pathways hit per group
  const hits = new Array(snap.pathways.length).fill(0), weight = new Array(snap.pathways.length).fill(0);
  for (const c of mapped) for (const [pi, x] of c.w) { hits[pi]++; weight[pi] += x; }
  for (const s of sectors) {
    s.hit = 0;
    for (let i = 0; i < snap.pathways.length; i++) if (S.groupOf[i] === s.g && hits[i]) s.hit++;
  }

  // claim blocks: one per KG group (primary group), then hub-only, then not found
  const blocks = [];
  for (let g = 0; g < G; g++) blocks.push({ key: g, claims: mapped.filter((c) => c.kind === 'mapped' && c.group === g) });
  blocks.push({ key: 'hub', claims: mapped.filter((c) => c.kind === 'hub') });
  blocks.push({ key: 'none', claims: mapped.filter((c) => c.kind === 'none') });
  for (const b of blocks) b.claims.sort((x, y) => (x.first - y.first) || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
  const used = blocks.filter((b) => b.claims.length);
  const step = n ? (TAU - used.length * BLOCK_GAP) / n : 0;
  // place blocks in order, then rotate the whole claim ring so that blocks sit as close as possible to their sector
  // (circular mean of the angle differences, weighted by block size); deterministic
  let at = 0;
  for (const b of used) { b.from = at + BLOCK_GAP / 2; b.to = b.from + step * b.claims.length; at = b.to + BLOCK_GAP / 2; }
  let sx = 0, sy = 0;
  for (const b of used) if (typeof b.key === 'number') {
    const d = sectors[b.key].mid - (b.from + b.to) / 2;
    sx += b.claims.length * Math.cos(d); sy += b.claims.length * Math.sin(d);
  }
  const rot = sx || sy ? Math.atan2(sy, sx) : START;
  const claims = new Map();
  for (const b of used) {
    b.from += rot; b.to += rot; b.mid = (b.from + b.to) / 2;
    b.claims.forEach((c, i) => {
      const ang = b.from + step * (i + 0.5);
      claims.set(c.id, { x: R * Math.cos(ang), y: R * Math.sin(ang), angle: ang, block: b.key });
    });
  }

  // ribbons: block (claims of primary group b) -> every group h it reaches, width = summed claim weight
  const ribbons = [];
  const into = sectors.map(() => []);
  for (const b of used) {
    if (typeof b.key !== 'number') continue;
    const W = new Array(G).fill(0);
    for (const c of b.claims) c.gw.forEach((x, h) => { W[h] += x; });
    const tot = W.reduce((s, x) => s + x, 0);
    const targets = W.map((x, h) => ({ h, x })).filter((t) => t.x > 0)
      .sort((t, u) => wrap(sectors[t.h].mid - b.mid) - wrap(sectors[u.h].mid - b.mid) || t.h - u.h);
    let s0 = b.from;
    for (const t of targets) {
      const rib = { b: b.key, h: t.h, w: t.x, a0: s0, a1: s0 + ((b.to - b.from) * t.x) / tot, primary: t.h === b.key };
      s0 = rib.a1;
      ribbons.push(rib); into[t.h].push(rib);
    }
  }
  sectors.forEach((s, h) => {
    const list = into[h].sort((x, y) => wrap(blocks[x.b].mid - s.mid) - wrap(blocks[y.b].mid - s.mid) || x.b - y.b);
    const tot = list.reduce((t, x) => t + x.w, 0);
    let s0 = s.from;
    for (const rib of list) { rib.s0 = s0; rib.s1 = s0 + ((s.to - s.from) * rib.w) / tot; s0 = rib.s1; }
  });

  const stats = {
    claims: n, mapped: mapped.filter((c) => c.kind === 'mapped').length,
    hub: blocks[G].claims.length, none: blocks[G + 1].claims.length,
    pathwaysHit: hits.filter(Boolean).length, pathways: snap.pathways.length,
  };
  return { R, r, sectors, tick, hits, weight, blocks: used, ribbons, claims, stats };
}

// world point -> what is under it: {kind: 'group', g} | {kind: 'pathway', p} | null
export function kgHit(lay, S, x, y) {
  const d = Math.hypot(x, y), ang = Math.atan2(y, x);
  const inArc = (from, to) => { const t = ((ang - from) % TAU + TAU) % TAU; return t <= to - from; };
  if (d >= lay.r.band0 && d <= lay.r.tick1) {
    const s = lay.sectors.find((s) => inArc(s.from, s.to));
    if (!s) return null;
    if (d < lay.r.tick0) return { kind: 'group', g: s.g };
    const t = ((ang - s.from) % TAU + TAU) % TAU;
    const first = S.groupOf.indexOf(s.g);
    return { kind: 'pathway', p: first + Math.min(s.n - 1, Math.floor((t / (s.to - s.from)) * s.n)) };
  }
  return null;
}
