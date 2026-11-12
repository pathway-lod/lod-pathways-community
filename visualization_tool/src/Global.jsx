// Global view TEST (2026-11-10): all claims of a file on one Cytoscape.js canvas; click a claim to open the existing
// card view (Graph from App.jsx) beside it. Question it answers: is Cytoscape.js fast enough for thousands of claims,
// and does global -> detail work. Knows no vocabulary: roles, anchors and the centre label come from the profile.
import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import cytoscape from 'cytoscape';
import '@xyflow/react/dist/style.css';
import './styles.css';
import { Graph, ROLE_COLOR } from './App.jsx';
import { parseRdf, indexGraph, focusSet, key } from './rdf.js';
import { loadProfile, makeRoles, makeLabels, titleFor } from './profile.js';
import { buildView } from './model.js';
import { globalLayout } from './globalLayout.js';
import { indexSnapshot, mapClaims, kgLayout, kgHit, HUB } from './kgMap.js'; // TEST 2026-11-11: knowledge-graph map
import { drawKg } from './kgDraw.js';
import { sharedNodes, siblingArcs, DRAW_MAX } from './siblings.js';
import { putHandoff, getHandoff, handoffUrl } from './handoff.js';

const params = new URLSearchParams(window.location.search);
const PROFILE = 'profiles/lod-pathways-draft.json';
const LOOSE = '#94a3b8';
const ms = (t0) => Math.round(performance.now() - t0);

export default function Global() {
  const [datasets, setDatasets] = useState([]);
  const [terms, setTerms] = useState(null);
  const [profileJson, setProfileJson] = useState(null);
  const [source, setSource] = useState(params.get('data') || 'sample_evidence_graph.nq');
  const [g, setG] = useState(null);
  const [error, setError] = useState(null);
  const [times, setTimes] = useState({});
  const [focus, setFocus] = useState(params.get('focus'));   // claim shown in the detail panel
  const [anchor, setAnchor] = useState(null); // anchor whose claims are listed
  const cyBox = useRef(null), cyRef = useRef(null), exportRef = useRef(null);
  // knowledge-graph map (TEST 2026-11-11): ?layout=kg (default, needs a snapshot named in the profile) or ring
  const [mode, setMode] = useState(params.get('layout') || 'kg');
  const [snap, setSnap] = useState(null);
  // picked set of claims: {kind: 'group', g} | {kind: 'pathway', p} | {kind: 'node', key} (claims sharing a node)
  // | {kind: 'set', ids} (shift-click)
  const [picked, setPicked] = useState(params.get('pick')?.startsWith('node:') ? { kind: 'node', key: params.get('pick').slice(5) } : null);
  const ringRef = useRef(null), kgHover = useRef(null), kgPick = useRef(null), kgRedraw = useRef(null), focusRef = useRef(null);

  useEffect(() => {
    fetch('data/datasets.json').then((r) => r.json()).then(setDatasets).catch(() => setDatasets([]));
    fetch('data/terms.json').then((r) => (r.ok ? r.json() : null)).then(setTerms).catch(() => setTerms(null));
    fetch(PROFILE).then((r) => r.json()).then(setProfileJson).catch((e) => setError(`profile: ${e.message}`));
  }, []);

  const loadText = useCallback((text, name) => {
    try {
      const t0 = performance.now();
      const graph = indexGraph(parseRdf(text, name));
      setTimes({ parse: ms(t0) }); setG(graph); setAnchor(null); setError(null);
    } catch (e) { setError(`${name}: ${e.message}`); }
  }, []);
  useEffect(() => {
    if (source.startsWith('local:')) return;
    let live = true; // ignore a response for a source that is no longer current (e.g. replaced by a hand-off)
    fetch('data/' + source).then((r) => { if (!r.ok) throw new Error(r.statusText); return r.text(); })
      .then((t) => { if (live) loadText(t, source); }).catch((e) => { if (live) setError(`${source}: ${e.message}`); });
    return () => { live = false; };
  }, [source]);
  // text of a file opened from disk, kept so that a selection can take it along to the card viewer
  const rawRef = useRef(null);
  // ?handoff=1 (back from the card viewer): same data again, the handed-over claims picked
  useEffect(() => {
    if (!params.has('handoff')) return;
    getHandoff().then((h) => {
      if (!h) return;
      if (h.text != null) { rawRef.current = { name: h.name, text: h.text }; setSource(h.source); loadText(h.text, h.name); }
      else if (h.source) setSource(h.source);
      if (h.claims?.length) setPicked({ kind: 'set', ids: h.claims, title: h.title });
    });
  }, []);
  // hand a set of claims to the card viewer (handoff.js) and go there
  const openCards = async (ids, title) => {
    const local = source.startsWith('local:');
    const ok = await putHandoff({ source, name: local ? rawRef.current?.name : null, text: local ? rawRef.current?.text ?? null : null,
      claims: [...ids], title });
    if (!ok) { setError('could not hand the selection to the card viewer (browser storage blocked?)'); return; }
    window.location.href = handoffUrl('./', source);
  };

  useEffect(() => {
    const f = profileJson?.roles?.kg?.snapshot;
    if (!f) { setSnap(null); return; }
    fetch(f).then((r) => (r.ok ? r.json() : null)).then(setSnap).catch(() => setSnap(null));
  }, [profileJson]);
  const S = useMemo(() => (snap ? indexSnapshot(snap) : null), [snap]);

  const P = useMemo(() => (profileJson && g
    ? loadProfile({ ...profileJson, prefixes: { ...g.filePrefixes, ...profileJson.prefixes } }) : null), [profileJson, g]);
  const roleOf = useMemo(() => (g && P ? makeRoles(g, P) : null), [g, P]);
  const L = useMemo(() => (g && P ? makeLabels(g, P, terms) : null), [g, P, terms]);

  // claims and their anchors (anchor predicates from the profile)
  const model = useMemo(() => {
    if (!roleOf) return null;
    const t0 = performance.now();
    const claims = [...g.out.keys()].filter((k) => roleOf(k) === 'claim').map((k) => ({
      id: k, anchors: [...new Set((g.out.get(k) || []).filter((t) => P.anchoredTo.has(t.p.value)).map((t) => key(t.o)))],
    }));
    const lay = globalLayout(claims);
    return { claims, lay, time: ms(t0) };
  }, [roleOf]);

  const kg = useMemo(() => {
    if (!model || !S) return null;
    const t0 = performance.now();
    const mapped = mapClaims(model.claims, S);
    return { mapped, lay: kgLayout(mapped, S), time: ms(t0) };
  }, [model, S]);
  // links between claims: nodes shared by two or more claims (siblings.js)
  const links = useMemo(() => (model ? sharedNodes(g, model.claims.map((c) => c.id), roleOf, { sameEntity: P.sameEntity }) : null), [model]);
  const linkColor = (kind) => (kind === 'data' ? ROLE_COLOR.data : kind === 'kg' ? ROLE_COLOR.kg : '#64748b');
  const arcsFor = (id, alpha, width) => (id && links ? siblingArcs(links, id).map((s) => ({
    from: id, to: s.other, color: linkColor(s.kind), alpha, width })) : []);
  // claims of the current pick (null = nothing picked)
  const pickedIds = useMemo(() => {
    if (!picked) return null;
    if (picked.kind === 'node') return new Set(links?.byNode.get(picked.key)?.claims || []);
    if (picked.kind === 'set') return new Set(picked.ids);
    if (!kg) return null;
    return new Set(kg.mapped.filter((c) => (picked.kind === 'group' ? c.gw[picked.g] > 0 : c.w.has(picked.p))).map((c) => c.id));
  }, [picked, links, kg]);

  const centre = profileJson?.roles?.kg?.name || 'knowledge graph';
  const useKg = mode === 'kg' && !!kg;

  // knowledge-graph map: claims are Cytoscape nodes, the map itself is drawn on a canvas underneath (kgDraw.js)
  useEffect(() => {
    if (!useKg || !cyBox.current) return;
    const t0 = performance.now();
    const { mapped, lay } = kg;
    // claims whose data point (role 'data') has other claims too get a dark ring
    const sharedData = new Set();
    for (const e of links.byNode.values()) if (e.kind === 'data') e.claims.forEach((c) => sharedData.add(c));
    const els = mapped.map((c) => {
      const p = lay.claims.get(c.id);
      const cls = (c.kind === 'mapped' ? 'claim' : 'claim loose') + (sharedData.has(c.id) ? ' shared' : '');
      return { data: { id: c.id }, classes: cls, position: { x: p.x, y: p.y }, grabbable: false };
    });
    const cy = cytoscape({
      container: cyBox.current, elements: els, layout: { name: 'preset', padding: 70 },
      minZoom: 0.02, maxZoom: 8, wheelSensitivity: 0.3, pixelRatio: 1, boxSelectionEnabled: false,
      style: [
        { selector: 'node', style: { width: 10, height: 10, 'border-width': 0 } },
        { selector: '.claim', style: { 'background-color': ROLE_COLOR.claim } },
        { selector: '.loose', style: { 'background-color': '#fff', 'border-width': 2, 'border-color': LOOSE } },
        { selector: '.shared', style: { 'border-width': 2, 'border-color': '#1e293b' } },
        { selector: '.dim', style: { opacity: 0.12 } },
        { selector: '.picked', style: { width: 14, height: 14 } },
        { selector: 'node:selected', style: { width: 16, height: 16, 'border-width': 3, 'border-color': '#0f172a' } },
      ],
    });
    const byId = new Map(mapped.map((c) => [c.id, c]));
    let queued = false;
    const redraw = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        if (cy.destroyed() || !ringRef.current) return;
        const arcs = [...arcsFor(focusRef.current, 0.9, 2), ...arcsFor(kgHover.current?.id, 0.45, 1.5)];
        const pk = kgPick.current, marks = [];
        if (pk?.kind === 'node' || pk?.kind === 'set') {
          const ids = pk.kind === 'node' ? links.byNode.get(pk.key)?.claims || [] : pk.ids;
          marks.push(...ids);
          // a picked shared node: connect its claims (first to each other one), if there are not too many
          if (pk.kind === 'node' && ids.length <= DRAW_MAX) {
            const color = linkColor(links.byNode.get(pk.key).kind);
            for (const o of ids.slice(1)) arcs.push({ from: ids[0], to: o, color, alpha: 0.9, width: 2 });
          }
        }
        if (focusRef.current) marks.push(focusRef.current);
        drawKg(ringRef.current, cy, lay, S, { centre, hover: kgHover.current, selected: kgPick.current, arcs, marks });
      });
    };
    kgRedraw.current = redraw;
    cy.on('render viewport resize', redraw);
    cy.on('mouseover', 'node', (e) => { kgHover.current = byId.get(e.target.id()); redraw(); });
    cy.on('mouseout', 'node', () => { kgHover.current = null; redraw(); });
    cy.on('tap', 'node', (e) => {
      const id = e.target.id();
      if (e.originalEvent?.shiftKey) { // shift-click: add to / remove from a hand-picked set
        setPicked((pk) => {
          const ids = new Set(pk?.kind === 'set' ? pk.ids : []);
          if (ids.has(id)) ids.delete(id); else ids.add(id);
          return ids.size ? { kind: 'set', ids: [...ids], title: pk?.kind === 'set' ? pk.title : undefined } : null;
        });
        return;
      }
      setFocus(id); setAnchor(null);
    });
    cy.on('tap', (e) => { if (e.target === cy) setPicked(kgHit(lay, S, e.position.x, e.position.y)); });
    cy.one('render', () => {
      setTimes((t) => ({ ...t, layout: kg.time, cytoscape: ms(t0) }));
      document.body.dataset.ready = '1';
    });
    redraw();
    cyRef.current = cy;
    return () => { cy.destroy(); kgRedraw.current = null; };
  }, [kg, useKg, links]);
  // picked set: dim the other claims, enlarge the picked ones, redraw the outline
  useEffect(() => {
    kgPick.current = picked;
    const cy = cyRef.current;
    if (useKg && cy && !cy.destroyed()) cy.batch(() => {
      cy.nodes().removeClass('dim picked');
      if (pickedIds) {
        cy.nodes().filter((n) => !pickedIds.has(n.id())).addClass('dim');
        if (picked.kind === 'node' || picked.kind === 'set') cy.nodes().filter((n) => pickedIds.has(n.id())).addClass('picked');
      }
    });
    kgRedraw.current?.();
  }, [pickedIds, useKg]);
  // opened claim: select its dot and draw its sibling arcs
  useEffect(() => {
    focusRef.current = focus;
    const cy = cyRef.current;
    if (useKg && cy && !cy.destroyed()) { cy.nodes().unselect(); if (focus) cy.getElementById(focus).select(); }
    kgRedraw.current?.();
  }, [focus, useKg, kg]);

  // build the Cytoscape graph once per file (anchor ring)
  useEffect(() => {
    if (!model || !cyBox.current || useKg) return;
    const t0 = performance.now();
    const { claims, lay } = model;
    const els = [];
    const centre = profileJson.roles?.kg?.name || 'knowledge graph';
    els.push({ data: { id: '__centre', label: `${centre}\n${lay.anchors.size} anchors` }, classes: 'centre',
      position: { x: 0, y: 0 }, selectable: false, grabbable: false });
    if (lay.wedge) {
      const a = (lay.wedge.from + lay.wedge.to) / 2, r = lay.rClaims * 1.12;
      els.push({ data: { id: '__wedge', label: `not anchored (${lay.wedge.n})` }, classes: 'wedge-label',
        position: { x: r * Math.cos(a), y: r * Math.sin(a) }, selectable: false, grabbable: false });
    }
    for (const [k, p] of lay.anchors) els.push({ data: { id: k, label: L.labelOf(k) || P.compact(k), n: p.n },
      classes: 'anchor', position: { x: p.x, y: p.y }, grabbable: false });
    for (const c of claims) {
      const p = lay.claims.get(c.id);
      els.push({ data: { id: c.id }, classes: c.anchors.length ? 'claim' : 'claim loose', position: { x: p.x, y: p.y }, grabbable: false });
      for (const a of c.anchors) els.push({ data: { id: `${c.id}->${a}`, source: c.id, target: a } });
    }
    const cy = cytoscape({
      container: cyBox.current, elements: els, layout: { name: 'preset' },
      minZoom: 0.02, maxZoom: 4, wheelSensitivity: 0.3,
      hideEdgesOnViewport: true, textureOnViewport: false, pixelRatio: 1, boxSelectionEnabled: false,
      style: [
        { selector: 'node', style: { width: 10, height: 10, 'border-width': 0 } },
        { selector: '.centre', style: { width: 2 * lay.rAnchors * 0.92, height: 2 * lay.rAnchors * 0.92,
          'background-color': ROLE_COLOR.kg, 'background-opacity': 0.08, 'border-width': 3, 'border-color': ROLE_COLOR.kg,
          'border-opacity': 0.35, label: 'data(label)', 'text-wrap': 'wrap', 'text-valign': 'center', color: ROLE_COLOR.kg,
          'font-size': Math.max(24, lay.rAnchors / 6), 'font-weight': 700, events: 'no' } },
        { selector: '.anchor', style: { 'background-color': ROLE_COLOR.kg, width: 'mapData(n, 1, 20, 8, 30)',
          height: 'mapData(n, 1, 20, 8, 30)', label: 'data(label)', 'font-size': 9, color: ROLE_COLOR.kg,
          'min-zoomed-font-size': 9 } },
        { selector: '.claim', style: { 'background-color': ROLE_COLOR.claim } },
        { selector: '.loose', style: { 'background-color': '#fff', 'border-width': 2, 'border-color': LOOSE } },
        { selector: '.wedge-label', style: { label: 'data(label)', width: 1, height: 1, color: LOOSE,
          'font-size': Math.max(18, lay.rClaims / 30), 'font-weight': 700, events: 'no' } },
        { selector: 'edge', style: { width: 1, 'line-color': ROLE_COLOR.kg, opacity: 0.25, 'curve-style': 'haystack' } },
        { selector: '.faded', style: { opacity: 0.08 } },
        { selector: 'edge.hl', style: { opacity: 0.9, width: 2 } },
        { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#0f172a' } },
      ],
    });
    // hover: highlight the node and its neighbours
    cy.on('mouseover', 'node.claim, node.anchor', (e) => cy.batch(() => {
      const near = e.target.closedNeighborhood();
      cy.elements().not(near).not('.centre, .wedge-label').addClass('faded');
      near.edges().addClass('hl');
    }));
    cy.on('mouseout', 'node', () => cy.batch(() => cy.elements().removeClass('faded hl')));
    cy.on('tap', 'node.claim', (e) => { setFocus(e.target.id()); setAnchor(null); });
    cy.on('tap', 'node.anchor', (e) => { setAnchor(e.target.id()); setFocus(null); });
    cy.one('render', () => {
      setTimes((t) => ({ ...t, layout: model.time, cytoscape: ms(t0) }));
      document.body.dataset.ready = '1';
    });
    cyRef.current = cy;
    return () => cy.destroy();
  }, [model, useKg]);

  // resize Cytoscape when the detail panel opens or closes
  useEffect(() => { cyRef.current?.resize(); }, [focus, anchor, picked]);

  const view = useMemo(() => (focus && roleOf
    ? buildView(g, focusSet(g, focus, roleOf), { P, roleOf, L, terms, runsAsCards: false }) : null), [focus, roleOf, L]);
  const nLoose = model?.claims.filter((c) => !c.anchors.length).length ?? 0;
  const anchorClaims = anchor && model ? model.claims.filter((c) => c.anchors.includes(anchor)) : [];

  return (
    <div className="app">
      <header>
        <h1>Global view <small>test (Cytoscape.js)</small></h1>
        <label>Data
          <select value={source} onChange={(e) => { setSource(e.target.value); setFocus(null); setAnchor(null); }}>
            {datasets.map((d) => <option key={d.file} value={d.file}>{d.label}</option>)}
            {!datasets.some((d) => d.file === source) && <option value={source}>{source.replace('local:', '')}</option>}
          </select>
        </label>
        <label className="file" title="Turtle (.ttl); N-Quads, TriG and N-Triples work too">Open Turtle file…
          <input type="file" accept=".ttl,.nq,.trig,.nt" onChange={async (e) => {
            const f = e.target.files[0]; if (!f) return;
            const text = await f.text(); rawRef.current = { name: f.name, text };
            setFocus(null); setAnchor(null); setPicked(null); setSource('local:' + f.name); loadText(text, f.name);
          }} />
        </label>
        <label>Layout
          <select value={mode} onChange={(e) => { setMode(e.target.value); setPicked(null); setAnchor(null); }}>
            <option value="kg" disabled={!S}>{centre} map</option>
            <option value="ring">anchor ring</option>
          </select>
        </label>
        <span className="spacer" />
        {useKg && <span className="summary">
          {kg.lay.stats.claims} claims · {kg.lay.stats.mapped} placed · {kg.lay.stats.hub} only very common anchors ·
          {' '}{kg.lay.stats.none} not in {centre} · parse {times.parse ?? '…'} ms · map {times.layout ?? '…'} ms
        </span>}
        {model && !useKg && <span className="summary">
          {model.claims.length} claims · {model.lay.anchors.size} anchors · {nLoose} not anchored ·
          {' '}parse {times.parse ?? '…'} ms · layout {times.layout ?? '…'} ms · Cytoscape {times.cytoscape ?? '…'} ms
        </span>}
        <button className="detail-btn" disabled={!g} onClick={() => openCards([], null)}
          title="open this file in the detail view (cards), without a selection">Open file in detail view →</button>
      </header>
      {error && <div className="error">{error}</div>}
      <main>
        <div className="canvas">
          {useKg && <canvas ref={ringRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />}
          <div ref={cyBox} key={useKg ? 'kg' : 'ring'} style={{ position: 'absolute', inset: 0 }} />
          {useKg && <KgLegend centre={centre} />}
        </div>
        {useKg && picked && <KgPanel picked={picked} ids={pickedIds} kg={kg} S={S} links={links} centre={centre}
          label={(id) => titleFor(g, id, 'claim', P, L)} nodeLabel={(k) => L.labelOf(k) || P.compact(k)} compact={P.compact}
          onClaim={(id) => setFocus(id)} onPathway={(p) => setPicked({ kind: 'pathway', p })} onClose={() => setPicked(null)}
          onOpenCards={openCards} />}
        {anchor && (
          <aside>
            <div className="aside-head"><b>{L.labelOf(anchor) || P.compact(anchor)}: {anchorClaims.length} claims</b>
              <button onClick={() => setAnchor(null)}>×</button></div>
            <pre>{anchorClaims.map((c) => (
              <div key={c.id}><a href="#" onClick={(e) => { e.preventDefault(); setFocus(c.id); setAnchor(null); }}>
                {titleFor(g, c.id, 'claim', P, L)}</a> <span style={{ color: '#64748b' }}>{P.compact(c.id)}</span></div>))}
            </pre>
          </aside>
        )}
        {view && (
          <div className="canvas" style={{ flex: 1.3, borderLeft: '1px solid #cbd5e1', background: '#f8fafc' }}>
            <button style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }} onClick={() => setFocus(null)}>× close</button>
            {links && <LinksBar id={focus} links={links} label={(id) => titleFor(g, id, 'claim', P, L)}
              nodeLabel={(k) => L.labelOf(k) || P.compact(k)} compact={P.compact} color={linkColor}
              onClaim={(id) => setFocus(id)} onNode={(k) => setPicked({ kind: 'node', key: k })} />}
            <ReactFlowProvider key={focus}>
              <Graph view={view} P={P} showMissing selected={null} onSelect={() => {}} exportRef={exportRef} mode="compact" />
            </ReactFlowProvider>
          </div>
        )}
      </main>
    </div>
  );
}

// "how to read this" box over the knowledge-graph map (TEST 2026-11-11); can be folded away
function KgLegend({ centre }) {
  const [open, setOpen] = useState(false); // starts folded (Martin: takes a lot of space on small screens)
  const box = { position: 'absolute', top: 12, left: 12, zIndex: 5, background: 'rgba(255,255,255,0.94)',
    border: '1px solid #cbd5e1', borderRadius: 8, font: '13px/1.45 system-ui, sans-serif', color: '#0f172a' };
  if (!open) return <button style={{ ...box, padding: '4px 10px', cursor: 'pointer' }} onClick={() => setOpen(true)}>How to read this</button>;
  const dot = (bg, border) => ({ display: 'inline-block', width: 10, height: 10, borderRadius: 5, background: bg,
    border: border ? `2px solid ${border}` : 'none', marginRight: 6, verticalAlign: 'middle', boxSizing: 'border-box' });
  const sw = (bg) => ({ display: 'inline-block', width: 14, height: 10, background: bg, marginRight: 6, verticalAlign: 'middle' });
  return (
    <div style={{ ...box, padding: '10px 14px', maxWidth: 360 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <b>How to read this</b>
        <button onClick={() => setOpen(false)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>×</button>
      </div>
      <div><span style={dot(ROLE_COLOR.claim)} /><b>Outer ring: your claims</b>, every one. They are grouped in blocks
        (bracket + label) by the {centre} group most of their anchors fall into. An anchor that sits in n pathways
        counts 1/n for each. Click a claim for its cards.</div>
      <div style={{ marginTop: 6 }}><span style={sw('rgba(124,58,237,0.25)')} /><b>Ribbons</b> lead from each block to
        every group its claims reach; the strong one is its own group.</div>
      <div style={{ marginTop: 6 }}><span style={sw('#6d28d9')} /><b>Inner ring: {centre}</b>, the same for every file.
        Group band: darker = more of the group's pathways reached by you (“reached of total”). Thin ticks: one per
        pathway, darker = more of your claims. Grey = nothing of yours yet. Click a group or pathway for its list.</div>
      <div style={{ marginTop: 6 }}><span style={dot('#fff', LOOSE)} /><b>Grey blocks</b>: claims whose anchors are
        all very common (e.g. water, in more than {HUB} pathways), or not found in {centre}.</div>
      <div style={{ marginTop: 6 }}><span style={dot(ROLE_COLOR.claim, '#1e293b')} /><b>Dark ring</b>: the claim's data
        point has other claims too. Hover or open a claim: arcs link it to claims with the same {centre} annotation
        (purple), the same data point (blue) or the same source, e.g. a paper (grey). Shift-click claims to collect a
        selection.</div>
    </div>
  );
}

const KIND_TEXT = { kg: 'same annotation', data: 'same data point', source: 'same source (cited by the evidence)' };

// bar on top of the card panel: what the opened claim shares with other claims (siblings.js)
function LinksBar({ id, links, label, nodeLabel, compact, color, onClaim, onNode }) {
  const nodes = links.ofClaim.get(id) || [];
  if (!nodes.length) return null;
  const link = (fn) => (e) => { e.preventDefault(); fn(); };
  return (
    <div style={{ position: 'absolute', top: 8, left: 8, right: 90, zIndex: 10, maxHeight: '32%', overflow: 'auto',
      background: 'rgba(255,255,255,0.96)', border: '1px solid #cbd5e1', borderRadius: 8, padding: '8px 12px',
      font: '12.5px/1.5 system-ui, sans-serif' }}>
      <b>Shares with other claims</b>
      {nodes.map((n) => {
        const e = links.byNode.get(n);
        const others = e.claims.filter((c) => c !== id);
        return (
          <div key={n} style={{ marginTop: 4 }}>
            <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: color(e.kind), marginRight: 6 }} />
            <b>{nodeLabel(n)}</b> <span style={{ color: '#64748b' }}>({[...e.via].map(compact).join(', ')}; {KIND_TEXT[e.kind]})</span>
            {' · '}{others.length} other claim{others.length === 1 ? '' : 's'}
            {others.length > DRAW_MAX && <span style={{ color: '#64748b' }}> (not drawn)</span>}
            {': '}{others.slice(0, 4).map((c, i) => <span key={c}>{i ? ', ' : ''}<a href="#" onClick={link(() => onClaim(c))}>{label(c)}</a></span>)}
            {others.length > 4 && ' …'} <a href="#" onClick={link(() => onNode(n))}>[select all {e.claims.length}]</a>
          </div>
        );
      })}
    </div>
  );
}

// side panel for a picked set of claims: group or pathway of the knowledge-graph map, a shared node, or a hand-picked
// set (TEST 2026-11-11)
function KgPanel({ picked, ids, kg, S, links, centre, label, nodeLabel, compact, onClaim, onPathway, onClose, onOpenCards }) {
  const { lay, mapped } = kg;
  const pw = S.snap.pathways;
  const muted = { color: '#64748b' };
  const link = (fn) => (e) => { e.preventDefault(); fn(); };
  const title = picked.kind === 'group' ? S.snap.groups[picked.g] : picked.kind === 'pathway' ? pw[picked.p][1]
    : picked.kind === 'node' ? nodeLabel(picked.key) : picked.title || 'Hand-picked claims';
  const n = ids?.size ?? 0;
  const openBtn = n > 0 && (
    <div style={{ padding: '8px 12px', borderBottom: '1px solid #e2e8f0' }}>
      <button onClick={() => onOpenCards([...ids], title)} title="open these claims in the detail view (cards), 100 per page">
        Open {n === 1 ? 'this claim' : `these ${n} claims`} in detail view →</button>
    </div>);
  if (picked.kind === 'node' || picked.kind === 'set') {
    const list = [...(ids || [])];
    const e = picked.kind === 'node' ? links.byNode.get(picked.key) : null;
    return (
      <aside>
        <div className="aside-head">
          <b>{e ? nodeLabel(picked.key) : `${picked.title || 'Selection'}: ${list.length} claims`}</b>
          <button onClick={onClose}>×</button>
        </div>
        {openBtn}
        <pre>
          {e ? <div>{list.length} claims point at {compact(picked.key)}{'\n'}via {[...e.via].map(compact).join(', ')} · {KIND_TEXT[e.kind]}{'\n\n'}</div>
            : <div>{picked.title ? 'Back from the card viewer. ' : ''}Shift-click claims to add or remove them.{'\n\n'}</div>}
          <div><b>Claims</b>{'\n'}{list.slice(0, 200).map((c) => (
            <div key={c}><a href="#" onClick={link(() => onClaim(c))}>{label(c)}</a> <span style={muted}>{compact(c)}</span></div>))}
            {list.length > 200 && <div style={muted}>… {list.length - 200} more</div>}</div>
        </pre>
      </aside>
    );
  }
  const isGroup = picked.kind === 'group';
  const g = isGroup ? picked.g : S.groupOf[picked.p];
  const claims = mapped.filter((c) => (isGroup ? c.gw[picked.g] > 0 : c.w.has(picked.p)));
  const sec = lay.sectors[g];
  const paths = isGroup ? pw.map((_, i) => i).filter((i) => S.groupOf[i] === g && lay.hits[i])
    .sort((a, b) => lay.hits[b] - lay.hits[a] || a - b) : [];
  return (
    <aside>
      <div className="aside-head">
        <b>{isGroup ? S.snap.groups[g] : pw[picked.p][1]}</b>
        <button onClick={onClose}>×</button>
      </div>
      {openBtn}
      <pre>
        {isGroup
          ? <div>{sec.hit} of {sec.n} {centre} pathways in this group are reached by {claims.length} claims{'\n\n'}</div>
          : <div>{pw[picked.p][0]} · {S.snap.groups[g]}{'\n'}classes: {pw[picked.p][3].join(', ') || '–'}{'\n'}
              <a href={pw[picked.p][4]} target="_blank" rel="noreferrer">{pw[picked.p][4]}</a>{'\n'}
              {claims.length} claims reach it{'\n\n'}</div>}
        {isGroup && <div><b>Pathways reached</b> (claims){'\n'}{paths.slice(0, 60).map((i) => (
          <div key={i}><a href="#" onClick={link(() => onPathway(i))}>{pw[i][1]}</a> <span style={muted}>({lay.hits[i]})</span></div>))}
          {paths.length > 60 && <div style={muted}>… {paths.length - 60} more</div>}{'\n'}</div>}
        <div><b>Claims</b>{'\n'}{claims.slice(0, 200).map((c) => (
          <div key={c.id}><a href="#" onClick={link(() => onClaim(c.id))}>{label(c.id)}</a> <span style={muted}>{compact(c.id)}</span></div>))}
          {claims.length > 200 && <div style={muted}>… {claims.length - 200} more</div>}</div>
      </pre>
    </aside>
  );
}
