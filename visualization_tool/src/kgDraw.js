// Draws the knowledge-graph map (kgMap.js) on a canvas UNDER the Cytoscape canvas, in Cytoscape's world coordinates
// (redrawn on every pan/zoom). Cytoscape only draws the claim dots (clickable, selectable); everything else is here.
// TEST, 2026-11-11 (see kgMap.js for how to remove it).
import { HUB } from './kgMap.js';

// one hue, light -> dark (coverage is a magnitude); a neutral gray means "nothing of yours here"
const RAMP = ['#ede9fe', '#ddd6fe', '#c4b5fd', '#a78bfa', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6', '#4c1d95'];
const NONE = '#eef0f3';
const INK = '#0f172a', MUTED = '#64748b';
const KG = '124, 58, 237'; // ribbon colour (rgb of RAMP[5])

const TAU = 2 * Math.PI;
const wrap = (a) => { a = (a + Math.PI) % TAU; return (a < 0 ? a + TAU : a) - Math.PI; };
const ramp = (f) => RAMP[Math.max(0, Math.min(RAMP.length - 1, Math.round(f * (RAMP.length - 1))))];

function band(ctx, r0, r1, a0, a1) {
  ctx.beginPath();
  ctx.arc(0, 0, r1, a0, a1);
  ctx.arc(0, 0, r0, a1, a0, true);
  ctx.closePath();
}

// text along a radius, readable on both halves of the circle; align 'end' = text ends at radius r
function radialText(ctx, text, r, ang, align, size, color, weight = 400) {
  ctx.save();
  const left = Math.cos(ang) < 0;
  ctx.rotate(left ? ang + Math.PI : ang);
  ctx.font = `${weight} ${size}px system-ui, sans-serif`;
  ctx.fillStyle = color;
  ctx.textBaseline = 'middle';
  ctx.textAlign = (align === 'end') !== left ? 'right' : 'left';
  ctx.fillText(text, left ? -r : r, 0);
  ctx.restore();
}

// text along an arc centred on angle mid; shrinks to 70 % and then truncates with … to fit `room` (radians)
function arcText(ctx, text, r, mid, ccw, size, color, weight, room, minScale = 0.7) {
  let s = size;
  ctx.font = `${weight} ${s}px system-ui, sans-serif`;
  let w = ctx.measureText(text).width;
  if (w / r > room) { s = Math.max(size * minScale, (size * room * r) / w); ctx.font = `${weight} ${s}px system-ui, sans-serif`; w = ctx.measureText(text).width; }
  let t = text;
  while (t.length > 1 && w / r > room) { t = t.slice(0, -2) + '…'; w = ctx.measureText(t).width; }
  if (t.length <= 2) return;
  ctx.save();
  ctx.fillStyle = color; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const dir = ccw ? -1 : 1;
  let a = mid - (dir * w) / r / 2;
  for (const ch of t) {
    const cw = ctx.measureText(ch).width;
    a += (dir * cw) / r / 2;
    ctx.save();
    ctx.rotate(a); ctx.translate(r, 0); ctx.rotate(dir * Math.PI / 2);
    ctx.fillText(ch, 0, 0);
    ctx.restore();
    a += (dir * cw) / r / 2;
  }
  ctx.restore();
}

export function drawKg(canvas, cy, lay, S, { centre, hover, selected, arcs = [], marks = [], dots = [] } = {}) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const z = cy.zoom(), pan = cy.pan();
  ctx.setTransform(dpr * z, 0, 0, dpr * z, dpr * pan.x, dpr * pan.y);
  const px = 1 / z; // one screen pixel in world units
  const { r, sectors, tick, hits, ribbons, blocks, R, stats } = lay;
  const maxHits = Math.max(1, ...hits);
  const focusGroup = selected?.kind === 'group' ? selected.g : selected?.kind === 'pathway' ? S.groupOf[selected.p] : null;

  // ribbons (claims block -> KG group), under everything
  for (const rib of ribbons) {
    const dim = focusGroup != null && rib.h !== focusGroup && rib.b !== focusGroup;
    const alpha = dim ? 0.03 : rib.primary ? 0.22 : 0.09;

    // edges are spirals in polar coordinates (angle eased, radius linear), so a ribbon between far-apart angles
    // curves around the ring instead of cutting through the disk; both edges turn the same way (that of the mids)
    const dm = wrap((rib.s0 + rib.s1) / 2 - (rib.a0 + rib.a1) / 2);
    const turn = (a, s) => s - a + TAU * Math.round((dm - (s - a)) / TAU);
    const edge = (a, s, fwd) => {
      const d = turn(a, s);
      for (let i = 0; i <= 32; i++) {
        const t = fwd ? i / 32 : 1 - i / 32, e = t * t * (3 - 2 * t);
        const rr = r.rib1 + (r.rib0 - r.rib1) * t, aa = a + d * e;
        ctx.lineTo(rr * Math.cos(aa), rr * Math.sin(aa));
      }
    };
    ctx.beginPath();
    ctx.arc(0, 0, r.rib1, rib.a0, rib.a1);
    edge(rib.a1, rib.s1, true);
    ctx.arc(0, 0, r.rib0, rib.s1, rib.s0, true);
    edge(rib.a0, rib.s0, false);
    ctx.closePath();
    ctx.fillStyle = `rgba(${KG}, ${alpha})`;
    ctx.fill();
  }

  // group band: fill = share of the group's pathways your data reaches
  for (const s of sectors) {
    band(ctx, r.band0, r.band1, s.from, s.to);
    ctx.fillStyle = s.hit ? ramp(s.hit / s.n) : NONE;
    ctx.fill();
    if (focusGroup === s.g) { ctx.lineWidth = 3 * px; ctx.strokeStyle = INK; ctx.stroke(); }
  }
  // pathway ticks: every pathway of the KG; dark = many of your claims
  for (let p = 0; p < tick.length; p++) {
    band(ctx, r.tick0, r.tick1, tick[p].from, tick[p].to);
    ctx.fillStyle = hits[p] ? ramp(0.25 + 0.75 * Math.log1p(hits[p]) / Math.log1p(maxHits)) : NONE;
    ctx.fill();
  }
  if (selected?.kind === 'pathway') {
    const t = tick[selected.p];
    band(ctx, r.tick0 - 4 * px, r.tick1 + 4 * px, t.from, t.to);
    ctx.lineWidth = 2 * px; ctx.strokeStyle = INK; ctx.stroke();
  }
  // thin surface gaps between pathway ticks only when they are wide enough to see
  const tickPx = ((sectors[0].to - sectors[0].from) / Math.max(1, sectors[0].n)) * r.tick1 * z;
  if (tickPx > 3) {
    ctx.strokeStyle = '#fff'; ctx.lineWidth = Math.min(1.5, tickPx / 4) * px;
    ctx.beginPath();
    for (const t of tick) { ctx.moveTo(r.tick0 * Math.cos(t.from), r.tick0 * Math.sin(t.from)); ctx.lineTo(r.tick1 * Math.cos(t.from), r.tick1 * Math.sin(t.from)); }
    ctx.stroke();
  }

  // group labels: curved along the band, two lines (name; reached / total)
  const fs = Math.max(R / 48, 11 * px);
  const fill = (s) => (s.hit ? Math.round((s.hit / s.n) * (RAMP.length - 1)) : -1);
  for (const s of sectors) {
    const bottom = Math.sin(s.mid) > 0.05; // text reads counter-clockwise there, "up" points to the centre
    const k = fill(s);
    const color = k >= 4 ? '#fff' : k >= 0 ? INK : MUTED;
    const th = r.band1 - r.band0;
    const rName = r.band0 + th * (bottom ? 0.36 : 0.64), rSub = r.band0 + th * (bottom ? 0.7 : 0.3);
    const room = (s.to - s.from) * 0.9;
    arcText(ctx, S.snap.groups[s.g], rName, s.mid, bottom, fs, color, 700, room);
    arcText(ctx, `${s.hit} of ${s.n}` + (s.scaled ? ' · drawn ¼' : ''), rSub, s.mid, bottom, fs * 0.8, color, 400, room);
  }
  // pathway titles when zoomed in far enough for them to fit
  const pathFs = 11 * px;
  for (let p = 0; p < tick.length; p++) {
    const t = tick[p];
    if ((t.to - t.from) * r.tick1 * z < 13) continue;
    const pw = S.snap.pathways[p];
    radialText(ctx, (hits[p] ? `● ${hits[p]}  ` : '') + pw[1], r.tick1 + 4 * px, (t.from + t.to) / 2, 'start', pathFs, hits[p] ? INK : MUTED);
  }

  // claim blocks: a bracket along each block just outside the claim dots, and a curved label outside it
  // ("<group> · n claims"), so it is clear why the claims sit where they do
  const rBr = R * 1.03, rLab = R * 1.03 + fs * 1.1;
  const ends = R * 0.012;
  for (const b of blocks) {
    const extra = typeof b.key !== 'number';
    const n = b.claims.length;
    const name = b.key === 'hub' ? `only very common anchors (in > ${HUB} pathways)`
      : b.key === 'none' ? `not found in ${centre}` : S.snap.groups[b.key];
    const focused = focusGroup != null && b.key === focusGroup;
    ctx.strokeStyle = extra ? MUTED : INK;
    ctx.globalAlpha = focusGroup != null && !focused ? 0.3 : 1;
    ctx.lineWidth = (focused ? 3 : 1.5) * px;
    ctx.beginPath();
    ctx.moveTo((rBr - ends) * Math.cos(b.from), (rBr - ends) * Math.sin(b.from));
    ctx.lineTo(rBr * Math.cos(b.from), rBr * Math.sin(b.from));
    ctx.arc(0, 0, rBr, b.from, b.to);
    ctx.lineTo((rBr - ends) * Math.cos(b.to), (rBr - ends) * Math.sin(b.to));
    ctx.stroke();
    const bottom = Math.sin(b.mid) > 0.05;
    const room = (b.to - b.from) * 1.0;
    const text = `${name} · ${n.toLocaleString()} claim${n === 1 ? '' : 's'}`;
    ctx.font = `${extra ? 400 : 600} ${fs}px system-ui, sans-serif`;
    if (ctx.measureText(text).width * 0.8 / rLab <= room) // fits along the arc (arcText may shrink it to 80 %)
      arcText(ctx, text, bottom ? rLab + fs * 0.2 : rLab, b.mid, bottom, fs, extra ? MUTED : INK, extra ? 400 : 600, room, 0.8);
    else // small block: label points outward from its middle
      radialText(ctx, text, rBr + fs * 0.6, b.mid, 'start', fs * 0.85, extra ? MUTED : INK, extra ? 400 : 600);
    ctx.globalAlpha = 1;
  }

  // centre: headline numbers
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = INK;
  const cf = r.band0 / 7.5;
  ctx.font = `700 ${cf}px system-ui, sans-serif`;
  ctx.fillText(centre, 0, -1.3 * cf);
  ctx.font = `400 ${cf * 0.42}px system-ui, sans-serif`;
  ctx.fillStyle = MUTED;
  ctx.fillText(`release ${S.snap.release}`, 0, -0.55 * cf);
  ctx.fillStyle = INK;
  ctx.font = `600 ${cf * 0.55}px system-ui, sans-serif`;
  ctx.fillText(`${stats.mapped.toLocaleString()} of ${stats.claims.toLocaleString()} claims placed`, 0, 0.35 * cf);
  ctx.fillText(`${stats.pathwaysHit.toLocaleString()} of ${stats.pathways.toLocaleString()} pathways reached`, 0, 1.05 * cf);

  // links between claims (siblings.js): arcs inside the claim ring; short ones hug the ring, long ones dip inward
  for (const a of arcs) {
    const p = lay.claims.get(a.from), q = lay.claims.get(a.to);
    if (!p || !q) continue;
    const d = Math.abs(wrap(q.angle - p.angle));
    const mid = p.angle + wrap(q.angle - p.angle) / 2;
    const rc = R * (0.97 - 0.55 * Math.min(1, d / Math.PI));
    ctx.strokeStyle = a.color; ctx.globalAlpha = a.alpha; ctx.lineWidth = (a.width || 1.5) * px;
    ctx.setLineDash(a.dash ? [6 * px, 4 * px] : []);
    ctx.beginPath();
    ctx.moveTo(p.x * 0.985, p.y * 0.985);
    ctx.quadraticCurveTo(rc * Math.cos(mid), rc * Math.sin(mid), q.x * 0.985, q.y * 0.985);
    ctx.stroke();
  }
  ctx.globalAlpha = 1; ctx.setLineDash([]);
  // score highlight (D36): coloured dots of fixed screen size, so the colours read at any zoom (the Cytoscape dots
  // vanish when the whole map is shown); when zoomed in they sit under the Cytoscape dot of the same colour
  for (const d of dots) {
    const p = lay.claims.get(d.id);
    if (!p) continue;
    ctx.fillStyle = d.color; ctx.globalAlpha = d.alpha ?? 1;
    ctx.beginPath(); ctx.arc(p.x, p.y, Math.max(3.5 * px, 5), 0, 2 * Math.PI); ctx.fill();
  }
  ctx.globalAlpha = 1;
  // halos around picked / opened claims: fixed screen size, so they stay visible at any zoom
  ctx.strokeStyle = INK; ctx.lineWidth = 2 * px;
  for (const id of marks) {
    const p = lay.claims.get(id);
    if (!p) continue;
    ctx.beginPath(); ctx.arc(p.x, p.y, Math.max(9 * px, 8), 0, 2 * Math.PI); ctx.stroke();
  }

  // hover: lines from the claim to each pathway it reaches
  if (hover) {
    const at = lay.claims.get(hover.id);
    if (at) {
      ctx.strokeStyle = `rgba(${KG}, 0.85)`; ctx.lineWidth = 1.5 * px;
      ctx.beginPath();
      for (const p of hover.w.keys()) {
        const m = (tick[p].from + tick[p].to) / 2;
        ctx.moveTo(at.x, at.y);
        ctx.quadraticCurveTo(r.rib1 * 0.8 * Math.cos(m), r.rib1 * 0.8 * Math.sin(m), r.tick1 * Math.cos(m), r.tick1 * Math.sin(m));
      }
      ctx.stroke();
    }
  }
}
