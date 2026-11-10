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
    fetch('data/' + source).then((r) => { if (!r.ok) throw new Error(r.statusText); return r.text(); })
      .then((t) => loadText(t, source)).catch((e) => setError(`${source}: ${e.message}`));
  }, [source]);

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

  // build the Cytoscape graph once per file
  useEffect(() => {
    if (!model || !cyBox.current) return;
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
  }, [model]);

  // resize Cytoscape when the detail panel opens or closes
  useEffect(() => { cyRef.current?.resize(); }, [focus, anchor]);

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
        <label className="file">Open RDF file…
          <input type="file" accept=".ttl,.nq,.trig,.nt" onChange={async (e) => {
            const f = e.target.files[0]; if (!f) return;
            setFocus(null); setAnchor(null); setSource('local:' + f.name); loadText(await f.text(), f.name);
          }} />
        </label>
        <span className="spacer" />
        {model && <span className="summary">
          {model.claims.length} claims · {model.lay.anchors.size} anchors · {nLoose} not anchored ·
          {' '}parse {times.parse ?? '…'} ms · layout {times.layout ?? '…'} ms · Cytoscape {times.cytoscape ?? '…'} ms
        </span>}
        <a href="./" className="note">card viewer</a>
      </header>
      {error && <div className="error">{error}</div>}
      <main>
        <div className="canvas"><div ref={cyBox} style={{ position: 'absolute', inset: 0 }} /></div>
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
            <ReactFlowProvider key={focus}>
              <Graph view={view} P={P} showMissing selected={null} onSelect={() => {}} exportRef={exportRef} mode="compact" />
            </ReactFlowProvider>
          </div>
        )}
      </main>
    </div>
  );
}
