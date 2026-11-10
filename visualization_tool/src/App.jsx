import { useEffect, useMemo, useState, useCallback } from 'react';
import {
  ReactFlow, ReactFlowProvider, Background, Controls, MarkerType,
  useNodesState, useEdgesState, useNodesInitialized, useReactFlow, getNodesBounds, getViewportForBounds,
} from '@xyflow/react';
import { toPng, toSvg } from 'html-to-image';
import '@xyflow/react/dist/style.css';
import './styles.css';
import CardNode from './CardNode.jsx';
import LaneEdge from './LaneEdge.jsx';
import TrackEdge from './TrackEdge.jsx';
import { parseRdf, indexGraph, focusSet, turtleOf } from './rdf.js';
import { loadProfile, makeRoles, makeLabels, titleFor } from './profile.js';
import { buildView } from './model.js';
import { layout, handlesFor, assignTracks, assignPorts } from './layout.js';

export const ROLE_COLOR = { data: '#2563eb', claim: '#c2410c', evidence: '#15803d', kg: '#7e22ce', run: '#475569' };
const PROFILES = [
  { file: 'profiles/lod-pathways-draft.json', label: 'LOD-pathways draft (lodp:)' },
  { file: null, label: 'none (generic RDF)' },
];
const EMPTY_PROFILE = { name: 'none', prefixes: {} };
const nodeTypes = { card: CardNode };
const edgeTypes = { lane: LaneEdge, track: TrackEdge };
const MAX_ALL = 60;
const params = new URLSearchParams(window.location.search);
// width of an edge label in the font it is drawn with (for the dynamic column gaps)
const measureCtx = document.createElement('canvas').getContext('2d');
measureCtx.font = "600 12px ui-monospace, 'Cascadia Mono', Consolas, monospace";
const labelWidth = (text) => measureCtx.measureText(text).width + 10;

export function Graph({ view, P, showMissing, selected, onSelect, exportRef, mode }) {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    [...view.cards.values()].map((c) => ({
      id: c.id, type: 'card', position: { x: 0, y: 0 }, data: { card: c, showMissing, compact: P.compact }, style: { opacity: 0 },
    })));
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const initialized = useNodesInitialized();
  const { getNodes, fitBounds } = useReactFlow();
  const [done, setDone] = useState(false);

  // pass 2: the cards have been measured -> lay out, then draw the edges
  useEffect(() => {
    if (!initialized || done) return;
    const sizes = new Map(getNodes().map((n) => [n.id, n.measured]));
    const pos = layout(view.cards, view.edges, sizes, mode, labelWidth);
    setNodes((ns) => ns.map((n) => ({ ...n, position: pos.get(n.id) ?? n.position, style: { opacity: 1 } })));
    const lanes = new Map();
    const routed = view.edges.map((e) => ({ ...e, ...handlesFor(e, pos, lanes) }));
    const ports = assignPorts(routed, pos, sizes);
    const tracks = assignTracks(routed, pos, sizes, ports);
    // edges entering the same card at the same point with the same label: show the label once
    const seenLabel = new Set();
    for (const e of routed) {
      const k = `${e.target}|${e.targetHandle}|${ports.get(e.id)?.tOff ?? 0}|${e.label}`;
      if (seenLabel.has(k)) e.label = ''; else seenLabel.add(k);
    }
    setEdges(routed.map((e) => {
      const color = ROLE_COLOR[view.cards.get(e.target)?.role] || '#64748b';
      const onTrack = tracks.has(e.id);
      return {
        id: e.id, source: e.source, target: e.target, sourceHandle: e.sourceHandle, targetHandle: e.targetHandle,
        type: e.type === 'lane' ? 'lane' : onTrack ? 'track' : 'smoothstep',
        data: e.type === 'lane' ? e.data : onTrack ? { centerX: tracks.get(e.id), ...ports.get(e.id) } : undefined,
        label: e.label, labelStyle: { fill: color, fontWeight: 600, fontSize: 12, fontFamily: 'var(--mono)' },
        labelBgStyle: { fill: '#fff' }, labelBgPadding: [4, 2],
        style: { stroke: color, strokeWidth: 1.8, strokeDasharray: e.state === 'proposal' ? '7 5' : undefined },
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 18, height: 18 },
      };
    }));
    setDone(true);
    // fit cards AND the edge lanes above them (lanes lie outside the card bounds)
    const xs = [...pos.entries()].map(([k, p]) => [p.x, p.x + (sizes.get(k)?.width ?? 400)]).flat();
    const ys = [...pos.entries()].map(([k, p]) => [p.y, p.y + (sizes.get(k)?.height ?? 200)]).flat();
    const top = Math.min(...ys, ...[...lanes.values()].map((y) => y - 20));
    const bounds = { x: Math.min(...xs), y: top, width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - top };
    requestAnimationFrame(() => { fitBounds(bounds, { padding: 0.04 }); document.body.dataset.ready = '1'; });
  }, [initialized, done]);

  useEffect(() => {
    setNodes((ns) => ns.map((n) => ({ ...n, data: { ...n.data, selected: n.id === selected } })));
  }, [selected]);

  exportRef.current = async (kind) => {
    const b = getNodesBounds(getNodes());
    const w = Math.ceil(b.width + 80), h = Math.ceil(b.height + 80);
    const vp = getViewportForBounds(b, w, h, 0.1, 2, 0.02);
    const url = await (kind === 'svg' ? toSvg : toPng)(document.querySelector('.react-flow__viewport'), {
      backgroundColor: '#ffffff', width: w, height: h, pixelRatio: 2,
      style: { width: `${w}px`, height: `${h}px`, transform: `translate(${vp.x}px, ${vp.y}px) scale(${vp.zoom})` },
    });
    const a = document.createElement('a');
    a.download = `evidence-graph.${kind}`; a.href = url; a.click();
  };

  return (
    <ReactFlow
      nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
      onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
      onNodeClick={(_, n) => onSelect(n.id)} onPaneClick={() => onSelect(null)}
      minZoom={0.05} maxZoom={2} nodesConnectable={false} proOptions={{ hideAttribution: true }}
    >
      <Background gap={24} color="#e2e8f0" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

function Legend({ P, hasTerms }) {
  const status = hasTerms
    ? [['reuse', 'existing ontology term, reused'], ['review', 'ontology term, decision open'],
      ['local', 'local placeholder term (to be agreed)'], ['unlisted', 'not in the term table'], ['kg', 'knowledge graph\'s own terms']]
    : [['local', 'local placeholder namespace'], ['kg', 'knowledge graph\'s own terms'], ['none', 'other terms']];
  return (
    <div className="legend">
      <div><b>Card header (role)</b>{Object.entries(P.roleLabels).map(([r, l]) => <div key={r}><i style={{ background: ROLE_COLOR[r] }} />{l}</div>)}</div>
      <div><b>Row (term status)</b>{status.map(([s, l]) => <div key={s}><i className={`sw st-${s}`} />{l}</div>)}</div>
      <div><b>Marks</b>
        <div><i className="sw dashed" />proposal, not in the RDF export</div>
        <div><span className="cnt violation">✕</span> SHACL violation <span className="cnt warning">!</span> warning</div>
        <div><span className="cnt pattern">◇</span> pattern check (from the profile)</div>
        {hasTerms && <div><span className="badge">MET-12</span> requirement in the term table</div>}
      </div>
    </div>
  );
}

export default function App() {
  const [datasets, setDatasets] = useState([]);
  const [termTable, setTermTable] = useState(null);
  const [profileFile, setProfileFile] = useState(params.has('profile') ? (params.get('profile') || null) : PROFILES[0].file);
  const [profileJson, setProfileJson] = useState(null);
  const [g, setG] = useState(null);
  const [source, setSource] = useState(params.get('data') || 'slide25.nq');
  const [focus, setFocus] = useState(params.get('focus') || '');
  const [runsAsCards, setRunsAsCards] = useState(params.get('runs') === '1');
  const [showMissing, setShowMissing] = useState(true);
  const [slideLayout, setSlideLayout] = useState(params.get('layout') === 'slide');
  const [useTerms, setUseTerms] = useState(params.get('terms') !== '0');
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const exportRef = { current: null };

  useEffect(() => {
    fetch('data/datasets.json').then((r) => r.json()).then(setDatasets).catch(() => setDatasets([]));
    fetch('data/terms.json').then((r) => (r.ok ? r.json() : null)).then(setTermTable).catch(() => setTermTable(null));
  }, []);
  useEffect(() => {
    if (!profileFile) { setProfileJson(EMPTY_PROFILE); return; }
    fetch(profileFile).then((r) => r.json()).then(setProfileJson).catch((e) => setError(`profile: ${e.message}`));
  }, [profileFile]);

  const loadText = useCallback((text, name, keepFocus) => {
    try {
      const graph = indexGraph(parseRdf(text, name));
      setG(graph); setSelected(null); setError(null);
      if (!keepFocus) setFocus('');
    } catch (e) { setError(`${name}: ${e.message}`); }
  }, []);
  useEffect(() => {
    if (source.startsWith('local:')) return;
    fetch('data/' + source).then((r) => { if (!r.ok) throw new Error(r.statusText); return r.text(); })
      .then((t) => loadText(t, source, true)).catch((e) => setError(`${source}: ${e.message}`));
  }, [source]);

  // the profile's prefixes win; the file's own prefixes fill the gaps (all of them when there is no profile)
  const P = useMemo(() => (profileJson && g
    ? loadProfile({ ...profileJson, prefixes: { ...g.filePrefixes, ...profileJson.prefixes } }) : null), [profileJson, g]);
  const roleOf = useMemo(() => (g && P ? makeRoles(g, P) : null), [g, P]);
  const terms = useTerms ? termTable : null;
  const L = useMemo(() => (g && P ? makeLabels(g, P, terms) : null), [g, P, terms]);
  const claims = useMemo(() => (roleOf ? [...g.out.keys()].filter((k) => roleOf(k) === 'claim') : []), [roleOf]);
  // big files open on their first claim
  const effFocus = focus || (g && g.out.size > MAX_ALL && claims.length ? claims[0] : '');
  const view = useMemo(() => (roleOf && L
    ? buildView(g, focusSet(g, effFocus || null, roleOf), { P, roleOf, L, terms, runsAsCards }) : null),
  [roleOf, L, effFocus, runsAsCards, terms]);
  const viewKey = `${source}|${effFocus}|${runsAsCards}|${showMissing}|${slideLayout}|${profileFile}|${useTerms}|${g?.quads.length}`;
  const nViol = g?.results.filter((r) => r.severity === 'violation').length ?? 0;
  const nWarn = g?.results.filter((r) => r.severity === 'warning').length ?? 0;

  return (
    <div className="app">
      <header>
        <h1>Evidence graph viewer <small>prototype</small></h1>
        <label>Data
          <select value={source} onChange={(e) => { setSource(e.target.value); setFocus(''); }}>
            {datasets.map((d) => <option key={d.file} value={d.file}>{d.label}</option>)}
            {!datasets.some((d) => d.file === source) && <option value={source}>{source.replace('local:', '')}</option>}
          </select>
        </label>
        <label className="file">Open RDF file…
          <input type="file" accept=".ttl,.nq,.trig,.nt" onChange={async (e) => {
            const f = e.target.files[0]; if (!f) return;
            setSource('local:' + f.name); loadText(await f.text(), f.name, false);
          }} />
        </label>
        <label>Profile
          <select value={profileFile ?? ''} onChange={(e) => setProfileFile(e.target.value || null)}>
            {PROFILES.map((p) => <option key={p.label} value={p.file ?? ''}>{p.label}</option>)}
          </select>
        </label>
        <label>Show
          <select value={effFocus} onChange={(e) => { setFocus(e.target.value); setSelected(null); }}>
            <option value="" disabled={g && g.out.size > MAX_ALL && claims.length > 0}>everything ({g?.out.size ?? 0} subjects)</option>
            {L && claims.slice(0, 2000).map((k) => <option key={k} value={k}>{titleFor(g, k, 'claim', P, L)} — {P.compact(k)}</option>)}
          </select>
        </label>
        <label className="chk"><input type="checkbox" checked={runsAsCards} onChange={(e) => setRunsAsCards(e.target.checked)} />runs as cards</label>
        <label className="chk" title="data | claims | evidence | PlantMetWiki, as on slides 24/25">
          <input type="checkbox" checked={slideLayout} onChange={(e) => setSlideLayout(e.target.checked)} />slide layout</label>
        <label className="chk"><input type="checkbox" checked={showMissing} onChange={(e) => setShowMissing(e.target.checked)} />missing properties</label>
        <label className="chk" title="colours and requirement badges from specification/ontology_terms.csv">
          <input type="checkbox" checked={useTerms} disabled={!termTable} onChange={(e) => setUseTerms(e.target.checked)} />term table</label>
        <span className="spacer" />
        <span className="summary">{g?.hasReport ? `SHACL: ${nViol} violations, ${nWarn} warnings` : 'no SHACL report'} · {claims.length} claims</span>
        <button onClick={() => exportRef.current?.('png')}>PNG</button>
        <button onClick={() => exportRef.current?.('svg')}>SVG</button>
      </header>
      {error && <div className="error">{error}</div>}
      <main>
        <div className="canvas">
          {view && P && (
            <ReactFlowProvider key={viewKey}>
              <Graph view={view} P={P} showMissing={showMissing} selected={selected} onSelect={setSelected} exportRef={exportRef}
                mode={slideLayout ? 'slide' : 'compact'} />
            </ReactFlowProvider>
          )}
          {P && <Legend P={P} hasTerms={!!terms} />}
        </div>
        {selected && g && P && (
          <aside>
            <div className="aside-head"><b>RDF of this card</b><button onClick={() => setSelected(null)}>×</button></div>
            <pre>{turtleOf(g, selected, P.prefixes)}</pre>
          </aside>
        )}
      </main>
    </div>
  );
}
