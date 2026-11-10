// Global view layout (test, 2026-11-10): knowledge graph as a disk in the middle, anchors on its rim, claims on an
// outer ring, unanchored claims in a separate wedge. Deterministic: same input, same positions (sorted, no forces).
// Knows no vocabulary: gets claim keys and, for each claim, the keys of the nodes it is anchored to.

const GAP = 0.06; // angle (fraction of the full circle) left empty on both sides of the unanchored wedge

// claims: [{ id, anchors: [key, ...] }]  ->  { claims: Map id -> {x, y, angle}, anchors: Map key -> {x, y, n},
//                                            rClaims, rAnchors, wedge: {from, to, n} | null }
export function globalLayout(claims, { spacing = 9 } = {}) {
  const anchored = claims.filter((c) => c.anchors.length);
  const loose = claims.filter((c) => !c.anchors.length).sort((a, b) => (a.id < b.id ? -1 : 1));
  // claims sorted by first anchor, then IRI: claims on the same anchor sit next to each other
  anchored.sort((a, b) => (a.anchors[0] < b.anchors[0] ? -1 : a.anchors[0] > b.anchors[0] ? 1 : a.id < b.id ? -1 : 1));

  const n = claims.length;
  const rClaims = Math.max(260, (n * spacing) / (2 * Math.PI));
  const rAnchors = rClaims * 0.62;
  const full = 2 * Math.PI;
  // the wedge gets its share of the circle (at least a bit, so a few unanchored claims stay visible)
  const wedgeShare = loose.length ? Math.max(0.04, loose.length / n) : 0;
  const mainSpan = full * (1 - wedgeShare - (loose.length ? 2 * GAP : 0));
  const start = -Math.PI / 2; // 12 o'clock

  const pos = new Map();
  const place = (list, from, span) => list.forEach((c, i) => {
    const a = from + (span * (i + 0.5)) / list.length;
    pos.set(c.id, { x: rClaims * Math.cos(a), y: rClaims * Math.sin(a), angle: a });
  });
  place(anchored, start, mainSpan);
  let wedge = null;
  if (loose.length) {
    const from = start + mainSpan + full * GAP, span = full * wedgeShare;
    place(loose, from, span);
    wedge = { from, to: from + span, n: loose.length };
  }

  // anchor angle = mean angle of the claims placed by it (they are contiguous); anchors only reached as a second
  // anchor of a claim get the mean of those claims
  const angles = new Map();
  for (const c of anchored) for (const k of c.anchors) {
    if (!angles.has(k)) angles.set(k, []);
    angles.get(k).push(pos.get(c.id).angle);
  }
  const anchors = new Map();
  for (const [k, as] of angles) {
    // circular mean (robust if a group crosses 12 o'clock)
    const a = Math.atan2(as.reduce((s, x) => s + Math.sin(x), 0), as.reduce((s, x) => s + Math.cos(x), 0));
    anchors.set(k, { x: rAnchors * Math.cos(a), y: rAnchors * Math.sin(a), n: as.length });
  }
  return { claims: pos, anchors, rClaims, rAnchors, wedge };
}
