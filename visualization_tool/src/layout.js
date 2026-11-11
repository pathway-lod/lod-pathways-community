// Layered layout: columns by role. Two arrangements:
//   compact (default)  runs | data + evidence | claims | knowledge graph
//                      every link goes to a neighbouring column (claim -> evidence/data left, claim -> anchor right)
//   slide              data | claims | evidence | knowledge graph | runs   (the look of slides 24/25; anchors then
//                      skip the evidence column on a lane above the cards)
// The knowledge graph is laid out as trees growing downward: anchors (linked from claims) in the knowledge-graph
// column at the height of their claims, the KG cards they link to in a row below, side by side, and so on (tidy
// tree: each card centred over its subtree, subtrees never overlap). The trees extend to the right of the KG column;
// columns after it (runs in the slide layout) start right of the widest tree.
// If the profile finds no claims (unknown vocabulary, or no profile), columns are the link distance from the
// nodes that nothing points to. Deterministic: the same subset always gives the same picture.
export const LAYOUTS = {
  compact: { columns: { run: 0, data: 1, evidence: 1, claim: 2, kg: 3 }, kgSideBySide: false },
  slide: { columns: { data: 0, claim: 1, evidence: 2, kg: 3, run: 4 }, kgSideBySide: true },
};
const COL_W = 400, GAP_X = 170, GAP_Y = 40, BLOCK_GAP = 90;
const SIB_GAP = 60, KG_GAP_X = 80, KG_MARGIN = 40; // sibling subtrees; trees side by side (slide); min. distance of a tree from the column left of the KG column
const V_MARGIN = 22, V_STEP = 14, V_LABEL = 34; // row gap of a KG tree: margin + one step per track + label room
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
  const kg = kgTrees(cards, edges, nbrs);
  const X = columnX(new Map([...cards.values()].map((c) => [c.id, L.columns[c.role]])), edges, labelWidth);
  const colX = (role) => X(L.columns[role]);
  const claimRank = new Map([...cards.values()].filter((c) => c.role === 'claim')
    .sort((a, b) => (a.state === 'proposal') - (b.state === 'proposal')).map((c, i) => [c.id, i]));

  placeClaimBlocks(cards, edges, pos, h, claimRank, L, colX);
  placeColumn(ids('data'), colX('data'), nbrs, pos, h); // slide layout: data has its own column
  const kgRight = placeKg(kg, nbrs, pos, h, colX('kg'), L.kgSideBySide,
    X(L.columns.kg - 1) + COL_W + KG_MARGIN);
  // columns right of the knowledge graph (runs in the slide layout) start after the widest tree
  const shift = Math.max(0, kgRight - (colX('kg') + COL_W));
  const xOf = (role) => colX(role) + (L.columns[role] > L.columns.kg ? shift : 0);
  placeColumn(ids('run'), xOf('run'), nbrs, pos, h);
  pos.colXs = [...new Set(Object.keys(L.columns).map(xOf))];
  pos.vertical = kg.vertical;
  // the column each card belongs to (KG tree cards can sit right of their column): used to find skipped columns
  pos.colOf = new Map([...cards.values()].map((c) => [c.id, xOf(c.role)]));
  return pos;
}

// Grid of graphs (2026-11-11, for selections opened from the global view): the view is split into connected graphs
// (over all edges), each is laid out on its own with layout(), and the graphs are packed in rows, largest first
// (most cards; ties: input order), left to right, a new row when the row would get wider than ROW_W. ROW_W =
// max(widest graph, GRID_ASPECT x sqrt(total area)), so the grid is roughly as wide as a screen is wide relative
// to its height. Deterministic. Edge routing uses each graph's own columns (pos.colXsOf), so a column of a graph in
// another row never turns an edge into a lane.
const GRID_GAP_X = 220, GRID_GAP_Y = 200, GRID_ASPECT = 1.7;
export function layoutGrid(cards, edges, sizes, mode = 'compact', labelWidth = estimateWidth) {
  const ids = [...cards.keys()];
  const parent = new Map(ids.map((k) => [k, k]));
  const find = (k) => { while (parent.get(k) !== k) { parent.set(k, parent.get(parent.get(k))); k = parent.get(k); } return k; };
  for (const e of edges) if (cards.has(e.source) && cards.has(e.target)) parent.set(find(e.source), find(e.target));
  const groups = new Map();
  ids.forEach((k, i) => { const r = find(k); if (!groups.has(r)) groups.set(r, { first: i, list: [] }); groups.get(r).list.push(k); });
  const wOf = (k) => sizes.get(k)?.width ?? COL_W, hOf = (k) => sizes.get(k)?.height ?? 200;
  const comps = [...groups.values()].map(({ first, list }) => {
    const set = new Set(list);
    const p = layout(new Map(list.map((k) => [k, cards.get(k)])), edges.filter((e) => set.has(e.source) && set.has(e.target)),
      sizes, mode, labelWidth);
    const xs = list.map((k) => p.get(k).x), ys = list.map((k) => p.get(k).y);
    const minX = Math.min(...xs), minY = Math.min(...ys);
    const w = Math.max(...list.map((k) => p.get(k).x + wOf(k))) - minX, h = Math.max(...list.map((k) => p.get(k).y + hOf(k))) - minY;
    return { first, list, p, minX, minY, w, h };
  }).sort((a, b) => b.list.length - a.list.length || a.first - b.first);
  const area = comps.reduce((s, c) => s + (c.w + GRID_GAP_X) * (c.h + GRID_GAP_Y), 0);
  const ROW_W = Math.max(...comps.map((c) => c.w), GRID_ASPECT * Math.sqrt(area));
  const pos = new Map();
  pos.colXsOf = new Map(); pos.colOf = new Map(); pos.vertical = new Set(); pos.colXs = [];
  let x = 0, y = 0, rowH = 0;
  for (const c of comps) {
    if (x > 0 && x + c.w > ROW_W) { y += rowH + GRID_GAP_Y; x = 0; rowH = 0; }
    const dx = x - c.minX, dy = y - c.minY;
    const colXs = (c.p.colXs || []).map((v) => v + dx);
    for (const k of c.list) {
      const q = c.p.get(k);
      pos.set(k, { ...q, x: q.x + dx, y: q.y + dy });
      pos.colXsOf.set(k, colXs);
      if (c.p.colOf?.has(k)) pos.colOf.set(k, c.p.colOf.get(k) + dx);
    }
    for (const v of c.p.vertical || []) pos.vertical.add(v);
    x += c.w + GRID_GAP_X; rowH = Math.max(rowH, c.h);
  }
  return pos;
}

// Knowledge-graph trees. KG cards linked to each other (e.g. metabolite -> its pathways) form a group (connected
// component over KG-to-KG links). Depth inside a group = link distance (either direction) from the cards linked from
// outside the group (the anchors of claims); a group that nothing outside links to starts at its first card.
function kgTrees(cards, edges, nbrs) {
  const kg = [...cards.values()].filter((c) => c.role === 'kg').map((c) => c.id);
  const isKg = new Set(kg);
  const adj = new Map(kg.map((k) => [k, []]));
  for (const e of edges) if (isKg.has(e.source) && isKg.has(e.target) && e.source !== e.target) {
    adj.get(e.source).push(e.target); adj.get(e.target).push(e.source);
  }
  const fromOutside = (k) => nbrs.get(k).some((x) => !isKg.has(x));
  const depth = new Map(), groups = [], seen = new Set();
  for (const k of kg) {
    if (seen.has(k)) continue;
    const g = [], st = [k]; seen.add(k);
    while (st.length) { const a = st.pop(); g.push(a); for (const b of adj.get(a)) if (!seen.has(b)) { seen.add(b); st.push(b); } }
    g.sort((a, b) => kg.indexOf(a) - kg.indexOf(b)); // input order: deterministic
    const roots = g.filter(fromOutside);
    const queue = (roots.length ? roots : [g[0]]).map((r) => [r, 0]);
    while (queue.length) {
      const [a, d] = queue.shift();
      if (depth.has(a)) continue;
      depth.set(a, d);
      for (const b of adj.get(a)) if (!depth.has(b)) queue.push([b, d + 1]);
    }
    groups.push(g);
  }
  return { groups, depth, maxDepth: Math.max(0, ...depth.values()) };
}

// Place the trees (tidy tree, growing downward). Parent of a card = its first neighbour one level up. Width of a
// subtree = max(card width, its children's subtrees side by side); a card is centred over its subtree. The tree is then shifted so that its first anchor is at the KG column (the gap
// to the claims stays as wide as the label), but no card goes left of leftLimit (the column left of the KG column +
// KG_MARGIN): the children use the free space below the claim -> anchor edge. The roots of
// a group (its anchors) form the top row at the mean height of the cards that point into the group; groups are
// stacked below each other (BLOCK_GAP/2 apart; compact) or side by side (slide). Rows are as far apart as the edge
// tracks between them need.
// Returns the right edge of the widest tree; sets kg.vertical (parent|child pairs drawn top-to-bottom).
function placeKg(kg, nbrs, pos, h, x0, sideBySide, leftLimit) {
  kg.vertical = new Set();
  if (!kg.groups.length) return x0 + COL_W;
  const outsideY = (g) => {
    const ys = g.flatMap((k) => nbrs.get(k).filter((x) => pos.has(x) && !kg.depth.has(x)).map((x) => pos.get(x).y + h(x) / 2));
    return ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : 0;
  };
  const groups = [...kg.groups].sort((a, b) => outsideY(a) - outsideY(b));
  let floor = -Infinity, right = x0 + COL_W;
  for (const g of groups) {
    const d = (k) => kg.depth.get(k);
    const children = new Map(g.map((k) => [k, []]));
    for (const k of g) {
      const parent = nbrs.get(k).find((n) => children.has(n) && d(n) === d(k) - 1);
      if (parent !== undefined) { children.get(parent).push(k); kg.vertical.add(`${parent}|${k}`); }
    }
    for (const cs of children.values()) cs.splice(0, cs.length, ...new Set(cs));
    const width = new Map();
    const w = (k) => {
      if (width.has(k)) return width.get(k);
      const cs = children.get(k);
      const sum = cs.reduce((s, c) => s + w(c), 0) + SIB_GAP * Math.max(0, cs.length - 1);
      width.set(k, Math.max(COL_W, sum));
      return width.get(k);
    };
    const roots = g.filter((k) => d(k) === 0);
    const xs = new Map();
    const placeX = (k, left) => {
      xs.set(k, left + (w(k) - COL_W) / 2);
      const cs = children.get(k);
      const span = cs.reduce((s, c) => s + w(c), 0) + SIB_GAP * Math.max(0, cs.length - 1);
      let cx = left + (w(k) - span) / 2;
      for (const c of cs) { placeX(c, cx); cx += w(c) + SIB_GAP; }
    };
    // compact: every tree starts at the KG column; slide: each tree right of the previous one (claim -> anchor
    // edges drop from a lane above all cards, so trees must not stand below each other)
    const base = sideBySide && g !== groups[0] ? right + KG_GAP_X : x0;
    const limit = base === x0 ? Math.min(leftLimit, x0) : base; // later trees side by side: not into the previous one
    let left = base;
    for (const r of roots) { placeX(r, left); left += w(r) + SIB_GAP; }
    // first anchor at the column, as far as the free space on the left allows
    const minX = Math.min(...g.map((k) => xs.get(k)));
    const shift = Math.max(base - xs.get(roots[0]), limit - minX);
    for (const k of g) xs.set(k, xs.get(k) + shift);
    // rows: top row at the height of the claims, each further row below the tallest card of the row above
    const maxD = Math.max(...g.map(d));
    const rowH = (r) => Math.max(...g.filter((k) => d(k) === r).map(h));
    const tracks = (r) => Math.max(1, ...g.filter((k) => d(k) === r).map((k) => Math.ceil(children.get(k).length / 2)));
    const want = outsideY(g) - h(roots[0]) / 2;
    let y = sideBySide ? want : Math.max(want, Number.isFinite(floor) ? floor : want);
    let bottom = y;
    for (let r = 0; r <= maxD; r++) {
      for (const k of g.filter((k) => d(k) === r)) pos.set(k, { x: xs.get(k), y });
      bottom = y + rowH(r);
      y = bottom + V_MARGIN + tracks(r) * V_STEP + V_LABEL;
    }
    for (const k of g) right = Math.max(right, xs.get(k) + COL_W);
    floor = bottom + BLOCK_GAP / 2;
  }
  return right;
}

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
  const centreX = (k) => pos.get(k).x + COL_W / 2;
  const sides = new Map();
  const add = (card, side, id, end, other) => {
    const k = `${card}|${side}`;
    const vert = side === 'top' || side === 'bottom';
    if (!sides.has(k)) sides.set(k, { card, vert, items: [] });
    sides.get(k).items.push({ id, end, other: vert ? centreX(other) : centre(other) });
  };
  for (const e of edges) {
    if (e.type === 'lane') continue;
    if (e.sourceHandle) add(e.source, e.sourceHandle.slice(2), e.id, 's', e.target);
    if (e.targetHandle) add(e.target, e.targetHandle.slice(2), e.id, 't', e.source);
  }
  const off = new Map();
  for (const { card, vert, items } of sides.values()) {
    items.sort((a, b) => a.other - b.other || (a.id < b.id ? -1 : 1));
    const span = Math.max(0, (vert ? COL_W : h(card)) - 2 * PORT_MARGIN);
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
  // an edge that has another column between its ends goes over the top (grid: only the columns of its own graph)
  const ca = pos.colOf?.get(e.source) ?? a.x, cb = pos.colOf?.get(e.target) ?? b.x;
  const lo = Math.min(ca, cb), hi = Math.max(ca, cb);
  if ((pos.colXsOf?.get(e.source) || pos.colXs || []).some((x) => x > lo + 1 && x < hi - 1)) {
    if (!lanes.has(e.id)) lanes.set(e.id, Math.min(...[...pos.values()].map((p) => p.y)) - 50 - lanes.size * 26);
    return { sourceHandle: 's-top', targetHandle: 't-top', type: 'lane', data: { laneY: lanes.get(e.id) } };
  }
  if (pos.vertical?.has(`${e.source}|${e.target}`) || pos.vertical?.has(`${e.target}|${e.source}`))
    return b.y > a.y ? { sourceHandle: 's-bottom', targetHandle: 't-top' } : { sourceHandle: 's-top', targetHandle: 't-bottom' };
  if (b.x > a.x) return { sourceHandle: 's-right', targetHandle: 't-left' };
  if (b.x < a.x) return { sourceHandle: 's-left', targetHandle: 't-right' };
  return b.y > a.y ? { sourceHandle: 's-bottom', targetHandle: 't-top' } : { sourceHandle: 's-top', targetHandle: 't-bottom' };
}

// Horizontal tracks for top/bottom edges (KG trees, same-column links), in the gap below the upper card of each edge.
// The edges of one upper card ("hub") fan out left and right; on each side the edge to the farthest card turns
// first (highest track), so the fan never crosses itself. Fans of different hubs in one row do not overlap (tidy
// tree), so they reuse the same track heights.
export function assignVTracks(edges, pos, sizes, ports = new Map()) {
  const h = (k) => sizes.get(k)?.height ?? 200;
  const hubs = new Map();
  for (const e of edges) {
    if (!['s-bottom', 's-top'].includes(e.sourceHandle)) continue;
    const down = e.sourceHandle === 's-bottom';
    const hub = down ? e.source : e.target, other = down ? e.target : e.source;
    const p = ports.get(e.id) || {};
    const hubX = pos.get(hub).x + COL_W / 2 + ((down ? p.sOff : p.tOff) || 0);
    const otherX = pos.get(other).x + COL_W / 2 + ((down ? p.tOff : p.sOff) || 0);
    if (!hubs.has(hub)) hubs.set(hub, []);
    hubs.get(hub).push({ id: e.id, d: otherX - hubX });
  }
  const trackY = new Map();
  for (const [hub, items] of hubs) {
    const y0 = pos.get(hub).y + h(hub) + V_MARGIN;
    const left = items.filter((it) => it.d < -1).sort((a, b) => a.d - b.d);
    const right = items.filter((it) => it.d > 1).sort((a, b) => b.d - a.d);
    left.forEach((it, i) => trackY.set(it.id, y0 + i * V_STEP));
    right.forEach((it, i) => trackY.set(it.id, y0 + i * V_STEP));
    items.filter((it) => Math.abs(it.d) <= 1).forEach((it) => trackY.set(it.id, y0));
  }
  return trackY;
}
