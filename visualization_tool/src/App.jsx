import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import {
  ReactFlow, ReactFlowProvider, Background, Controls, MarkerType, SelectionMode,
  useNodesState, useEdgesState, useNodesInitialized, useReactFlow, getNodesBounds, getViewportForBounds,
} from '@xyflow/react';
import { toPng, toSvg } from 'html-to-image';
import '@xyflow/react/dist/style.css';
import './styles.css';
import CardNode from './CardNode.jsx';
import ValidationControl from './ValidationControl.jsx';
import LaneEdge from './LaneEdge.jsx';
import TrackEdge from './TrackEdge.jsx';
import VTrackEdge from './VTrackEdge.jsx';
import { parseRdf, indexGraph, focusSet, focusSetMany, turtleOf, key } from './rdf.js';
import { getHandoff, handoffUrl } from './handoff.js';
import { loadProfile, makeRoles, makeLabels, titleFor } from './profile.js';
import { buildView } from './model.js';
import { layout, layoutGrid, handlesFor, assignTracks, assignVTracks, assignPorts } from './layout.js';
import { indexSnapshot } from './kgMap.js';
import { withKgStubs } from './kgStubs.js';

export const ROLE_COLOR = { data: '#2563eb', claim: '#c2410c', evidence: '#15803d', kg: '#7e22ce', run: '#475569' };
const PROFILES = [
  { file: 'profiles/lod-pathways-draft.json', label: 'LOD-pathways draft (lodp:)' },
  { file: null, label: 'none (generic RDF)' },
];
const EMPTY_PROFILE = { name: 'none', prefixes: {} };
const nodeTypes = { card: CardNode };
const edgeTypes = { lane: LaneEdge, track: TrackEdge, vtrack: VTrackEdge };
const MAX_ALL = 60;
const isProposal = (t) => t.origins.size === 1 && t.origins.has('proposal'); // as in model.js
const MULTI_KEYS =['Shift', 'Control', 'Meta']; // held while clicking a card: add it to / remove it from the selection
const params = new URLSearchParams(window.location.search);
const SUBSET_PAGE = 100; // claims per page when a selection from the global view is shown
// width of an edge label in the font it is drawn with (for the dynamic column gaps)
const measureCtx = document.createElement('canvas').getContext('2d');
measureCtx.font = "600 12px ui-monospace, 'Cascadia Mono', Consolas, monospace";
const labelWidth = (text) => measureCtx.measureText(text).width + 10;

export function Graph({ view, P, showMissing, selected, onSelect, exportRef, mode, grid = false }) {
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
    // grid: each connected graph laid out on its own, graphs packed in rows (selections from the global view)
    const pos = (grid ? layoutGrid : layout)(view.cards, view.edges, sizes, mode, labelWidth);
    setNodes((ns) => ns.map((n) => ({ ...n, position: pos.get(n.id) ?? n.position, style: { opacity: 1 } })));
    const lanes = new Map();
    const routed = view.edges.map((e) => ({ ...e, ...handlesFor(e, pos, lanes) }));
    const ports = assignPorts(routed, pos, sizes);
    const tracks = assignTracks(routed, pos, sizes, ports);
    const vtracks = assignVTracks(routed, pos, sizes, ports);
    // edges entering the same card at the same point with the same label: show the label once
    const seenLabel = new Set();
    for (const e of routed) {
      const k = `${e.target}|${e.targetHandle}|${ports.get(e.id)?.tOff ?? 0}|${e.label}`;
      if (seenLabel.has(k)) e.label = ''; else seenLabel.add(k);
    }
    setEdges(routed.map((e) => {
      const color = ROLE_COLOR[view.cards.get(e.target)?.role] || '#64748b';
      const onTrack = tracks.has(e.id), onVTrack = vtracks.has(e.id);
      return {
        id: e.id, source: e.source, target: e.target, sourceHandle: e.sourceHandle, targetHandle: e.targetHandle,
        type: e.type === 'lane' ? 'lane' : onTrack ? 'track' : onVTrack ? 'vtrack' : 'smoothstep',
        data: e.type === 'lane' ? e.data : onTrack ? { centerX: tracks.get(e.id), ...ports.get(e.id) }
          : onVTrack ? { trackY: vtracks.get(e.id), ...ports.get(e.id) } : undefined,
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

  // selection: `selected` (list of card ids, or null) is the source of truth; it is pushed into React Flow's own
  // node selection, and React Flow's changes (Shift/Ctrl/Cmd-click toggles, Shift-drag box) come back via onSelect
  // (React Flow reports an empty selection on mount, before our push; ignore it so a remount keeps the selection)
  const pushed = useRef(false);
  useEffect(() => {
    const sel = new Set(selected || []);
    setNodes((ns) => ns.map((n) => {
      const s = sel.has(n.id);
      return n.selected === s && n.data.selected === s ? n : { ...n, selected: s, data: { ...n.data, selected: s } };
    }));
    pushed.current = true;
  }, [selected]);
  const onSelectionChange = useCallback(({ nodes: sel }) => {
    if (pushed.current) onSelect(sel.map((n) => n.id));
  }, [onSelect]);

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
      onNodeClick={(ev, n) => { if (!(ev.shiftKey || ev.ctrlKey || ev.metaKey)) onSelect([n.id]); }}
      onPaneClick={() => onSelect([])} onSelectionChange={onSelectionChange}
      multiSelectionKeyCode={MULTI_KEYS} selectionMode={SelectionMode.Partial} deleteKeyCode={null}
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
  const [profileFile] = useState(params.has('profile') ? (params.get('profile') || null) : PROFILES[0].file);
  const [profileJson, setProfileJson] = useState(null);
  const [g0, setG] = useState(null); // the parsed file; `g` below adds knowledge-graph stubs in selection mode
  const [source, setSource] = useState(params.get('data') || 'slide25.nq');
  const [focus, setFocus] = useState(params.get('focus') || '');
  const [runsAsCards, setRunsAsCards] = useState(params.get('runs') === '1');
  const [showMissing, setShowMissing] = useState(true);
  const [slideLayout] = useState(params.get('layout') === 'slide');
  const [useTerms, setUseTerms] = useState(params.get('terms') !== '0');
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [validated, setValidated] = useState(null); // result of a validation run in this page for the current file
  // selection handed over by the global view (handoff.js): {title, claims}; shown page by page
  // subset shown page by page: a selection handed over by the global view, or "all claims" of the file
  const [subset, setSubset] = useState(null);
  const [handoffSel, setHandoffSel] = useState(null); // the hand-over selection, to switch back to it
  const [page, setPage] = useState(0);
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
      setG(graph); setSelected(null); setError(null); setValidated(null);
      if (!keepFocus) setFocus('');
    } catch (e) { setError(`${name}: ${e.message}`); }
  }, []);
  // ?handoff=1: take data (and the file text, for files opened from disk) and the claim list from the global view
  useEffect(() => {
    if (!params.has('handoff')) return;
    getHandoff().then((h) => {
      if (!h) { setError('no selection from the global view found (browser storage empty or blocked)'); return; }
      if (h.text != null) { setSource(h.source); loadText(h.text, h.name, true); }
      else if (h.source && h.source !== source) setSource(h.source);
      // no claims = the whole file ("Open file in detail view" in the global view), not an empty selection
      if (h.claims?.length) { const sel = { title: h.title, claims: h.claims }; setSubset(sel); setHandoffSel(sel); setPage(0); setFocus(''); }
    });
  }, []);
  useEffect(() => {
    if (source.startsWith('local:')) return;
    let live = true; // a response for a source that is no longer current (e.g. replaced by a hand-off) is ignored
    fetch('data/' + source).then((r) => { if (!r.ok) throw new Error(r.statusText); return r.text(); })
      .then((t) => { if (live) loadText(t, source, true); }).catch((e) => { if (live) setError(`${source}: ${e.message}`); });
    return () => { live = false; };
  }, [source]);

  // the profile's prefixes win; the file's own prefixes fill the gaps (all of them when there is no profile)
  const P = useMemo(() => (profileJson && g0
    ? loadProfile({ ...profileJson, prefixes: { ...g0.filePrefixes, ...profileJson.prefixes } }) : null), [profileJson, g0]);
  // knowledge-graph snapshot named in the profile (as in the global view): stub cards for anchors the file does not
  // describe, so claims of a selection meet on their shared knowledge-graph nodes (kgStubs.js)
  const [snap, setSnap] = useState(null);
  useEffect(() => {
    const f = profileJson?.roles?.kg?.snapshot;
    if (!f) { setSnap(null); return; }
    fetch(f).then((r) => (r.ok ? r.json() : null)).then(setSnap).catch(() => setSnap(null));
  }, [profileJson]);
  const S = useMemo(() => (snap ? indexSnapshot(snap) : null), [snap]);
  // a hand-over selection: the claims of the current page (only those present in the file)
  const subsetAll = useMemo(() => (subset && g0 ? subset.claims.filter((c) => g0.out.has(c)) : null), [subset, g0]);
  const nPages = subsetAll ? Math.max(1, Math.ceil(subsetAll.length / SUBSET_PAGE)) : 0;
  const pageClaims = subsetAll && !focus ? subsetAll.slice(page * SUBSET_PAGE, (page + 1) * SUBSET_PAGE) : null;
  const g = useMemo(() => (g0 && P && S && pageClaims
    ? withKgStubs(g0, pageClaims, P.anchoredTo, S, profileJson?.roles?.kg?.name) : g0), [g0, P, S, pageClaims?.join('|')]);
  const roleOf = useMemo(() => (g && P ? makeRoles(g, P) : null), [g, P]);
  const terms = useTerms ? termTable : null;
  const L = useMemo(() => (g && P ? makeLabels(g, P, terms) : null), [g, P, terms]);
  const claims = useMemo(() => (roleOf ? [...g.out.keys()].filter((k) => roleOf(k) === 'claim') : []), [roleOf]);
  // big files open on their first claim
  const effFocus = focus || (pageClaims ? '' : (g && g.out.size > MAX_ALL && claims.length ? claims[0] : ''));
  const shown = useMemo(() => (roleOf
    ? (pageClaims ? focusSetMany(g, pageClaims, roleOf) : focusSet(g, effFocus || null, roleOf)) : null),
  [roleOf, effFocus, pageClaims?.join('|')]);
  const view = useMemo(() => (shown && L
    ? buildView(g, shown, { P, roleOf, L, terms, runsAsCards }) : null),
  [shown, L, runsAsCards, terms]);
  const viewKey = `${source}|${effFocus}|${pageClaims ? `sel${page}/${subsetAll.length}` : ''}|${runsAsCards}|${showMissing}|${slideLayout}|${profileFile}|${useTerms}|${g?.quads.length}|${pageClaims && S ? 'stubs' : ''}`;
  const nViol = g?.results.filter((r) => r.severity === 'violation').length ?? 0;
  const nWarn = g?.results.filter((r) => r.severity === 'warning').length ?? 0;
  // RDF of the selected cards: the exportable part, and the proposal-only triples shown apart (not exported)
  // (plus the shown subjects that are not drawn as cards and that a selected card points to, e.g. runs folded into
  // evidence cards, so the export holds what the selected cards show)
  const nSel = selected?.length ?? 0;
  const selTtl = useMemo(() => {
    if (!nSel || !g || !P || !view) return null;
    const folded = selected.flatMap((k) => (g.out.get(k) || []).map((t) => key(t.o)))
      .filter((o) => shown.has(o) && g.out.has(o) && !view.cards.has(o));
    const keys = [...new Set([...selected, ...folded])];
    return { data: turtleOf(g, keys, P.prefixes, (t) => !isProposal(t) && !t.stub), proposal: turtleOf(g, keys, P.prefixes, isProposal) };
  }, [selected, g, P, view, shown]);
  const saveTtl = (text, name) => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type: 'text/turtle' }));
    a.download = name; a.click(); URL.revokeObjectURL(a.href);
  };
  const download = () => saveTtl(selTtl.data, 'selection.ttl');
  // everything that is open: all subjects of the shown subset (incl. runs folded into evidence cards), no proposals
  // a selection: all its claims, all pages; never the knowledge-graph stubs (not in the file)
  const exportAll = () => {
    const keys = pageClaims ? [...focusSetMany(g0, subsetAll, roleOf)] : [...shown];
    saveTtl(turtleOf(g0, keys.filter((k) => g0.out.has(k)), P.prefixes, (t) => !isProposal(t) && !t.stub),
      pageClaims ? 'selection.ttl' : 'evidence-graph.ttl');
  };

  return (
    <div className="app">
      <header>
        <a className="back-link" href={params.has('handoff') ? handoffUrl('global.html', source)
          : source.startsWith('local:') ? 'global.html' : `global.html?data=${encodeURIComponent(source)}`}
          title="back to the global view (reloads it)">← Global view</a>
        <h1>Evidence graph viewer <small>prototype</small></h1>
        <label>Data
          <select value={source} onChange={(e) => { setSource(e.target.value); setFocus(''); setSubset(null); setHandoffSel(null); }}>
            {datasets.map((d) => <option key={d.file} value={d.file}>{d.label}</option>)}
            {!datasets.some((d) => d.file === source) && <option value={source}>{source.replace('local:', '')}</option>}
          </select>
        </label>
        <label className="file" title="Turtle (.ttl); N-Quads, TriG and N-Triples work too">Open Turtle file…
          <input type="file" accept=".ttl,.nq,.trig,.nt" onChange={async (e) => {
            const f = e.target.files[0]; if (!f) return;
            setSource('local:' + f.name); setSubset(null); setHandoffSel(null); loadText(await f.text(), f.name, false);
          }} />
        </label>
        {/* Profile chooser hidden 2026-11-12 (only one profile for now); ?profile= still selects one, ?profile= (empty) = none */}
        <label>Show
          <select value={pageClaims ? (subset.all ? '__all__' : '__subset__') : effFocus} onChange={(e) => {
            const v = e.target.value; setSelected(null);
            if (v === '__subset__') { setSubset(handoffSel); setPage(0); setFocus(''); }
            else if (v === '__all__') { setSubset({ title: 'All claims', claims, all: true }); setPage(0); setFocus(''); }
            else { setFocus(v); if (!v) setSubset(null); }
          }}>
            {handoffSel && <option value="__subset__">selection from the global view ({handoffSel.claims.length} claims)</option>}
            {claims.length > 0 && <option value="__all__">all claims, {SUBSET_PAGE} per page ({claims.length} claims)</option>}
            <option value="" disabled={g && g.out.size > MAX_ALL && claims.length > 0}>everything ({g?.out.size ?? 0} subjects)</option>
            {L && claims.slice(0, 2000).map((k) => <option key={k} value={k}>{titleFor(g, k, 'claim', P, L)} — {P.compact(k)}</option>)}
          </select>
        </label>
        <label className="chk"><input type="checkbox" checked={runsAsCards} onChange={(e) => setRunsAsCards(e.target.checked)} />runs as cards</label>
        {/* "slide layout" checkbox hidden 2026-11-12; the slide order is still reachable with ?layout=slide */}
        <label className="chk" title={'Show an empty "missing" row for each required property that SHACL validation reports as absent, with the message under it.'
          + (g && !g.hasReport ? '\nThis file has no SHACL report yet (use "Run SHACL validation"), so nothing is added.' : '')}>
          <input type="checkbox" checked={showMissing} onChange={(e) => setShowMissing(e.target.checked)} />missing properties</label>
        <label className="chk" title={'Colour each property row by its status in the project\'s term table (specification/ontology_terms.csv): existing term reused, decision open, local placeholder, not in the table; and show the requirement badges (e.g. MET-12).\nOff: rows coloured by namespace only, no badges.'
          + (!termTable ? '\nTerm table not available.' : '')}>
          <input type="checkbox" checked={useTerms} disabled={!termTable} onChange={(e) => setUseTerms(e.target.checked)} />term table</label>
        <span className="spacer" />
        <span className="summary">{g?.hasReport ? `SHACL: ${nViol} violations, ${nWarn} warnings · `
          : (profileJson?.validation ? '' : 'no SHACL report · ')}{claims.length} claims</span>
        {/* in-browser SHACL validation (src/validation/, profile "validation"): a button where there is no report */}
        {profileJson?.validation && g0 && (
          <ValidationControl g={g0} config={profileJson.validation} done={validated}
            fileName={source.replace(/^local:/, '').replace(/\.[^./]+$/, '')}
            onReport={(quads, result) => { setG(indexGraph(quads)); setSelected(null); setValidated(result); }} />
        )}
        <span className="row-break" />{/* export buttons always on a second row (2026-11-12) */}
        <button onClick={() => exportRef.current?.('png')}>PNG</button>
        <button onClick={() => exportRef.current?.('svg')}>SVG</button>
        <button disabled={!shown || !P} onClick={exportAll}
          title={pageClaims ? `RDF of the whole selection (${subsetAll.length} claims, all pages), as Turtle`
            : 'RDF of everything shown, as Turtle (without proposal triples)'}>TTL</button>
      </header>
      {error && <div className="error">{error}</div>}
      {pageClaims && (
        <div className="subset-bar">
          <b>{subset.title || 'Selection from the global view'}</b>
          <span>claims {page * SUBSET_PAGE + 1}–{page * SUBSET_PAGE + pageClaims.length} of {subsetAll.length}
            {subsetAll.length < subset.claims.length && ` (${subset.claims.length - subsetAll.length} not in this file)`}</span>
          <button disabled={page === 0} onClick={() => { setPage(page - 1); setSelected(null); }}>‹ previous</button>
          <span>page {page + 1} / {nPages}</span>
          <button disabled={page >= nPages - 1} onClick={() => { setPage(page + 1); setSelected(null); }}>next ›</button>
        </div>
      )}
      <main>
        <div className="canvas">
          {view && P && (
            <ReactFlowProvider key={viewKey}>
              <Graph view={view} P={P} showMissing={showMissing} selected={selected} onSelect={setSelected} exportRef={exportRef}
                mode={slideLayout ? 'slide' : 'compact'} grid={!!pageClaims && !slideLayout} />
            </ReactFlowProvider>
          )}
          {P && <Legend P={P} hasTerms={!!terms} />}
        </div>
        {selTtl && (
          <aside>
            <div className="aside-head">
              <b title="Shift/Ctrl/Cmd-click a card to add or remove it; Shift-drag on the background to select a box">
                RDF of {nSel === 1 ? 'this card' : `${nSel} cards`}</b>
              <span className="aside-actions">
                <button disabled={!selTtl.data} onClick={() => navigator.clipboard?.writeText(selTtl.data)}>Copy</button>
                <button disabled={!selTtl.data} onClick={download} title="download the selection as Turtle (without proposal triples)">.ttl</button>
                <button onClick={() => setSelected(null)}>×</button>
              </span>
            </div>
            {selTtl.data && <pre>{selTtl.data}</pre>}
            {selTtl.proposal && <>
              <div className="aside-sub">proposal, not in the RDF export</div>
              <pre className="proposal">{selTtl.proposal}</pre>
            </>}
          </aside>
        )}
      </main>
    </div>
  );
}
