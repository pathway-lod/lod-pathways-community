// Layered layout: columns by role. Two arrangements:
//   compact (default)  runs | data + evidence | claims | knowledge graph
//                      every link goes to a neighbouring column (claim -> evidence/data left, claim -> anchor right)
//   slide              data | claims | evidence | knowledge graph | runs   (the look of slides 24/25; anchors then
//                      skip the evidence column on a lane above the cards, and KG groups sit side by side)
// If the profile finds no claims (unknown vocabulary, or no profile), columns are the link distance from the
// nodes that nothing points to. Deterministic: the same subset always gives the same picture.
export const LAYOUTS = {
  compact: { columns: { run: 0, data: 1, evidence: 1, claim: 2, kg: 3 }, kgSideBySide: false },
  slide: { columns: { data: 0, claim: 1, evidence: 2, kg: 3, run: 4 }, kgSideBySide: true },
};
const COL_W = 400, GAP_X = 170, GAP_Y = 40, BLOCK_GAP = 90, KG_GAP_X = 50;
const LABEL_PAD = 70; // room around the widest label in a gap: arrowhead, tracks, margins

// x of each column index. Every gap is as wide as the widest label of the edges crossing it (between neighbouring
// columns) plus LABEL_PAD, and at least GAP_X, so labels never run into the cards.
function columnX(colOf, edges, labelWidth) {
  const gap = new Map();
  for (const e of edges) {
    const a = colOf.get(e.source), b = colOf.get(e.target);
    if (a == null || b == null || Math.abs(a - b) !== 1) continue;
    const k = Math.min(a, b);
    gap.set(k, Math.max(gap.get(k) ?? 0, labelWidth(e.label || '')));
  }
  const width = (k) => Math.max(GAP_X, (gap.get(k) ?? 0) + LABEL_PAD);
  return (c) => { let x = 0; for (let k = 0; k < c; k++) x += COL_W + width(k); return x; };
}

// Claim order: claims linked to each other (e.g. a BGC-pathway link and the BGC it is about) are kept adjacent,
// each group ordered along its links (source above target); claims that share a side-column card (e.g. two
// annotations of the same feature) count as linked too, so the shared card can sit between them.
// Groups and roots keep the input order.
function orderClaims(cards, edges, claimRank, sideClaims) {
  const byRank = (a, b) => claimRank.get(a) - claimRank.get(b);
  const claims = [...cards.values()].filter((c) => c.role === 'claim').map((c) => c.id).sort(byRank);
  const isClaim = new Set(claims);
  const ce = edges.filter((e) => isClaim.has(e.source) && isClaim.has(e.target) && e.source !== e.target);
  const sharing = (k) => [...sideClaims.values()].filter((cs) => cs.length > 1 && cs.includes(k)).flat();
  const order = [], seen = new Set();
  const visit = (k) => { // depth-first: outgoing claim links, incoming ones, then claims sharing a card
    if (seen.has(k)) return;
    seen.add(k); order.push(k);
    ce.filter((e) => e.source === k).map((e) => e.target).sort(byRank).forEach(visit);
    ce.filter((e) => e.target === k).map((e) => e.source).sort(byRank).forEach(visit);
    sharing(k).sort(byRank).forEach(visit);
  };
  for (const k of claims) if (!ce.some((e) => e.target === k)) visit(k); // start where nothing points in
  claims.forEach(visit); // groups that are pure cycles
  return order;
}

// One block per claim: the cards of its side column (evidence; in compact also its data cards, data first)
// stacked, the claim centred on that stack (or the stack on the claim when the claim is taller).
// A card linked to several claims is placed BETWEEN blocks: after the block of the first of its claims, so the
// claims around it reach it with short edges. Blocks follow each other with a larger gap.
function placeClaimBlocks(cards, edges, pos, h, claimRank, L, colX) {
  const side = L.columns.data === L.columns.evidence ? ['data', 'evidence'] : ['evidence'];
  const stack = (ids, y0, x) => { let y = y0; for (const k of ids) { pos.set(k, { x, y }); y += h(k) + GAP_Y; } };
  const height = (ids) => ids.reduce((s, k) => s + h(k), 0) + GAP_Y * Math.max(0, ids.length - 1);
  // side-column card -> the claims it is linked to
  const sideClaims = new Map();
  for (const e of edges) for (const [c, k] of [[e.source, e.target], [e.target, e.source]])
    if (cards.get(c)?.role === 'claim' && side.includes(cards.get(k)?.role)) {
      if (!sideClaims.has(k)) sideClaims.set(k, []);
      if (!sideClaims.get(k).includes(c)) sideClaims.get(k).push(c);
    }
  const order = orderClaims(cards, edges, claimRank, sideClaims);
  const idx = new Map(order.map((c, i) => [c, i]));
  const own = (c) => side.flatMap((role) => [...sideClaims.entries()]
    .filter(([k, cs]) => cards.get(k).role === role && cs.length === 1 && cs[0] === c).map(([k]) => k));
  const sharedAfter = (c) => [...sideClaims.entries()].filter(([, cs]) => cs.length > 1
    && Math.min(...cs.map((x) => idx.get(x))) === idx.get(c)).map(([k]) => k);
  let top = 0;
  for (const c of order) {
    const items = own(c);
    const stackH = height(items), blockH = Math.max(h(c), stackH);
    stack(items, top + (blockH - stackH) / 2, colX('evidence'));
    pos.set(c, { x: colX('claim'), y: top + (blockH - h(c)) / 2 });
    top += blockH + BLOCK_GAP;
    const shared = sharedAfter(c);
    if (shared.length) { stack(shared, top - BLOCK_GAP / 2, colX('evidence')); top += height(shared) + BLOCK_GAP / 2; }
  }
  // side-column cards without a shown claim (e.g. an orphan data node) go below
  stack([...cards.values()].filter((c) => side.includes(c.role) && !pos.has(c.id)).map((c) => c.id), top, colX('evidence'));
}

function depthColumns(cards, edges) {
  const out = new Map([...cards.keys()].map((k) => [k, []]));
  const indeg = new Map([...cards.keys()].map((k) => [k, 0]));
  for (const e of edges) { out.get(e.source).push(e.target); indeg.set(e.target, indeg.get(e.target) + 1); }
  const col = new Map();
  const roots = [...cards.keys()].filter((k) => indeg.get(k) === 0);
  const queue = (roots.length ? roots : [[...cards.keys()][0]]).map((k) => [k, 0]);
  while (queue.length) {
    const [k, d] = queue.shift();
    if (col.has(k)) continue;
    col.set(k, d);
    for (const n of out.get(k)) if (!col.has(n)) queue.push([n, d + 1]);
  }
  for (const k of cards.keys()) if (!col.has(k)) col.set(k, 0); // cycles without a root
  return col;
}

// Stack cards in one column, each as close as possible to the mean y of its placed neighbours, without overlap
function placeColumn(ids, x, nbrs, pos, h, sortByDesired = true) {
  const desired = (k) => {
    const ys = nbrs.get(k).filter((n) => pos.has(n)).map((n) => pos.get(n).y + h(n) / 2);
    return ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length - h(k) / 2 : null;
  };
  if (sortByDesired) ids.sort((a, b) => (desired(a) ?? 1e9) - (desired(b) ?? 1e9));
  let bottom = null;
  for (const k of ids) {
    const d = desired(k);
    const y = bottom === null ? (d ?? 0) : Math.max(d ?? bottom, bottom);
    pos.set(k, { x, y });
    bottom = y + h(k) + GAP_Y;
  }
}

const estimateWidth = (text) => text.length * 7.4; // 12 px monospace, used when no measuring function is given

export function layout(cards, edges, sizes, mode = 'compact', labelWidth = estimateWidth) {
  const nbrs = new Map([...cards.keys()].map((k) => [k, []]));
  for (const e of edges) { nbrs.get(e.source)?.push(e.target); nbrs.get(e.target)?.push(e.source); }
  const h = (k) => sizes.get(k)?.height ?? 200;
  const pos = new Map();
  const ids = (role) => [...cards.values()].filter((c) => c.role === role && !pos.has(c.id)).map((c) => c.id);

  if (![...cards.values()].some((c) => c.role === 'claim')) {
    const colOf = depthColumns(cards, edges);
    const X = columnX(colOf, edges, labelWidth);
    const cols = [...new Set(colOf.values())].sort((a, b) => a - b);
    for (const ci of cols) placeColumn([...cards.keys()].filter((k) => colOf.get(k) === ci), X(ci), nbrs, pos, h, ci > 0);
    pos.colXs = cols.map(X);
    return pos;
  }

  const L = LAYOUTS[mode] || LAYOUTS.compact;
  const X = columnX(new Map([...cards.values()].map((c) => [c.id, L.columns[c.role]])), edges, labelWidth);
  const colX = (role) => X(L.columns[role]);
  const claimRank = new Map([...cards.values()].filter((c) => c.role === 'claim')
    .sort((a, b) => (a.state === 'proposal') - (b.state === 'proposal')).map((c, i) => [c.id, i]));

  placeClaimBlocks(cards, edges, pos, h, claimRank, L, colX);
  placeColumn(ids('data'), colX('data'), nbrs, pos, h); // slide layout: data has its own column
  placeKg(cards, edges, nbrs, pos, h, colX('kg'), L.kgSideBySide);
  const runX = L.kgSideBySide ? kgRight(pos, cards, colX('kg')) : colX('run');
  placeColumn(ids('run'), runX, nbrs, pos, h);
  pos.colXs = [...new Set(Object.values(L.columns))].map(X).concat(runX);
  return pos;
}

// Knowledge-graph cards: cards linked to each other (e.g. metabolite -> its pathways) form a group stacked
// vertically, the card linked from outside the group (the anchor of a claim) on top. Groups are placed at the
// height of the cards that point to them: one below the other (compact) or side by side (slide).
function placeKg(cards, edges, nbrs, pos, h, x0, sideBySide) {
  const kg = [...cards.values()].filter((c) => c.role === 'kg').map((c) => c.id);
  if (!kg.length) return;
  const isKg = new Set(kg);
  const kgEdges = edges.filter((e) => isKg.has(e.source) && isKg.has(e.target));
  const group = new Map(); // connected components over KG-to-KG links
  for (const k of kg) {
    if (group.has(k)) continue;
    const st = [k]; group.set(k, k);
    while (st.length) {
      const a = st.pop();
      for (const e of kgEdges) for (const [x, y] of [[e.source, e.target], [e.target, e.source]])
        if (x === a && !group.has(y)) { group.set(y, k); st.push(y); }
    }
  }
  const groups = [...new Set(group.values())].map((root) => kg.filter((k) => group.get(k) === root));
  const outside = (k) => nbrs.get(k).filter((x) => !isKg.has(x) && pos.has(x)).map((x) => pos.get(x).y + h(x) / 2);
  const groupY = (g) => { const ys = g.flatMap(outside); return ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : 0; };
  groups.sort((a, b) => groupY(a) - groupY(b));
  let bottom = null;
  groups.forEach((g, i) => {
    // inside a group: cards linked from outside on top, the others by link distance (either direction)
    const depth = new Map();
    const linked = g.filter((k) => outside(k).length);
    const queue = (linked.length ? linked : [g[0]]).map((k) => [k, 0]);
    while (queue.length) {
      const [k, d] = queue.shift();
      if (depth.has(k)) continue;
      depth.set(k, d);
      for (const e of kgEdges) for (const [a, b] of [[e.source, e.target], [e.target, e.source]])
        if (a === k && g.includes(b) && !depth.has(b)) queue.push([b, d + 1]);
    }
    g.sort((a, b) => (depth.get(a) ?? 0) - (depth.get(b) ?? 0) || outside(b).length - outside(a).length);
    const want = Math.max(0, groupY(g) - h(g[0]) / 2);
    let y = sideBySide || bottom === null ? want : Math.max(want, bottom);
    const x = sideBySide ? x0 + i * (COL_W + KG_GAP_X) : x0;
    for (const k of g) { pos.set(k, { x, y }); y += h(k) + GAP_Y; }
    bottom = y - GAP_Y + BLOCK_GAP / 2;
  });
}

const kgRight = (pos, cards, x0) => {
  const xs = [...cards.values()].filter((c) => c.role === 'kg' && pos.has(c.id)).map((c) => pos.get(c.id).x);
  return (xs.length ? Math.max(...xs) : x0) + COL_W + GAP_X;
};

// Vertical tracks in the gaps between columns: every edge gets its own bend position, so no two edges share a
// vertical segment. Each source card gets a band of tracks in the gap; bands are ordered by the card's height (the
// top card's band nearest to it). Inside a band, the card's upward edges (target above the connection point) bend
// nearest-first from the top, its downward edges nearest-first from the bottom, so a card's own fan never crosses
// itself; upward and downward edges never meet and can reuse the same tracks.
export function assignTracks(edges, pos, sizes, ports = new Map()) {
  const h = (k) => sizes.get(k)?.height ?? 200;
  const y = (k, off) => pos.get(k).y + h(k) / 2 + (off || 0);
  const gaps = new Map();
  for (const e of edges) {
    if (e.sourceHandle !== 's-left' && e.sourceHandle !== 's-right') continue;
    const a = pos.get(e.source), b = pos.get(e.target);
    const left = Math.min(a.x, b.x) + COL_W, right = Math.max(a.x, b.x);
    const k = `${left}|${right}`;
    if (!gaps.has(k)) gaps.set(k, { left, right, owners: new Map() });
    const g = gaps.get(k);
    if (!g.owners.has(e.source)) g.owners.set(e.source, { y: a.y, fromRight: a.x > b.x, up: [], down: [] });
    const p = ports.get(e.id) || {};
    const sy = y(e.source, p.sOff), ty = y(e.target, p.tOff);
    g.owners.get(e.source)[ty < sy ? 'up' : 'down'].push({ id: e.id, sy });
  }
  const centerX = new Map();
  for (const g of gaps.values()) {
    const owners = [...g.owners.values()].sort((p, q) => p.y - q.y);
    owners.forEach((o) => { o.up.sort((p, q) => p.sy - q.sy); o.down.sort((p, q) => q.sy - p.sy); });
    const total = owners.reduce((n, o) => n + Math.max(1, o.up.length, o.down.length), 0);
    const step = (g.right - g.left) / (total + 1);
    let slot = 0;
    for (const o of owners) {
      const x = (i) => (o.fromRight ? g.right - (slot + i + 1) * step : g.left + (slot + i + 1) * step);
      o.up.forEach((it, i) => centerX.set(it.id, x(i)));
      o.down.forEach((it, i) => centerX.set(it.id, x(i)));
      slot += Math.max(1, o.up.length, o.down.length);
    }
  }
  return centerX;
}

// Connection points spread along a card's side: the k edges on one (left or right) side of a card get k evenly
// spaced points instead of all using the middle. Order = height of the card at the other end, so edges do not
// cross at the border. Returned as offsets from the card's vertical centre (they stay right when a card is dragged).
const PORT_MARGIN = 18;
export function assignPorts(edges, pos, sizes) {
  const h = (k) => sizes.get(k)?.height ?? 200;
  const centre = (k) => pos.get(k).y + h(k) / 2;
  const sides = new Map();
  const add = (card, side, id, end, other) => {
    const k = `${card}|${side}`;
    if (!sides.has(k)) sides.set(k, { card, items: [] });
    sides.get(k).items.push({ id, end, otherY: centre(other) });
  };
  for (const e of edges) {
    if (e.sourceHandle === 's-left' || e.sourceHandle === 's-right') add(e.source, e.sourceHandle.slice(2), e.id, 's', e.target);
    if (e.targetHandle === 't-left' || e.targetHandle === 't-right') add(e.target, e.targetHandle.slice(2), e.id, 't', e.source);
  }
  const off = new Map();
  for (const { card, items } of sides.values()) {
    items.sort((a, b) => a.otherY - b.otherY || (a.id < b.id ? -1 : 1));
    const span = Math.max(0, h(card) - 2 * PORT_MARGIN);
    items.forEach((it, i) => {
      const y = -span / 2 + (span * (i + 1)) / (items.length + 1);
      if (!off.has(it.id)) off.set(it.id, {});
      off.get(it.id)[it.end === 's' ? 'sOff' : 'tOff'] = items.length > 1 ? y : 0;
    });
  }
  return off;
}

// Which side of each card an edge leaves and enters. Edges that skip a column run on a lane above all cards.
export function handlesFor(e, pos, lanes) {
  const a = pos.get(e.source), b = pos.get(e.target);
  if (!a || !b) return {};
  // an edge that has another column between its ends goes over the top
  const lo = Math.min(a.x, b.x), hi = Math.max(a.x, b.x);
  if ((pos.colXs || []).some((x) => x > lo + 1 && x < hi - 1)) {
    if (!lanes.has(e.id)) lanes.set(e.id, Math.min(...[...pos.values()].map((p) => p.y)) - 50 - lanes.size * 26);
    return { sourceHandle: 's-top', targetHandle: 't-top', type: 'lane', data: { laneY: lanes.get(e.id) } };
  }
  if (b.x > a.x) return { sourceHandle: 's-right', targetHandle: 't-left' };
  if (b.x < a.x) return { sourceHandle: 's-left', targetHandle: 't-right' };
  return b.y > a.y ? { sourceHandle: 's-bottom', targetHandle: 't-top' } : { sourceHandle: 's-top', targetHandle: 't-bottom' };
}
