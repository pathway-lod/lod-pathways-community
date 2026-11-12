// Header control for the in-browser SHACL validation (src/validation/): a button where the summary says that the file
// has no SHACL report; while running a progress bar with a time estimate and Cancel; afterwards a button that saves
// data + report as one N-Quads file (open it again with "Open Turtle file…" to see the report without re-running).
import { useEffect, useRef, useState } from 'react';
import { loadShapes, startValidation, estimateSeconds, dataQuads, withReport, toNQuads } from './validation/run.js';

const fmt = (s) => (s < 60 ? `${Math.round(s)} s` : `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`);

/**
 * @param {object} p
 * @param {object} p.g          the parsed file (indexGraph): quads, hasReport
 * @param {object} p.config     profile.validation: { index, label }
 * @param {string} p.fileName   base name for the saved file
 * @param {object|null} p.done  result of a validation of this file in this page ({seconds, counts}), or null
 * @param {(quads: object[], result: object) => void} p.onReport  called with the quads + report when finished
 */
export default function ValidationControl({ g, config, fileName, done, onReport }) {
  const [run, setRun] = useState(null); // { phase, start, est, cancel }
  const [now, setNow] = useState(0);
  const [error, setError] = useState(null);
  const runRef = useRef(null);
  useEffect(() => () => runRef.current?.cancel(), []); // leaving the page / another file: stop the worker
  useEffect(() => {
    if (!run) return undefined;
    const t = setInterval(() => setNow(performance.now()), 250);
    return () => clearInterval(t);
  }, [run]);

  const nTriples = g ? dataQuads(g.quads).length : 0;
  const est = estimateSeconds(nTriples);

  const start = async () => {
    setError(null);
    const t0 = performance.now();
    setRun({ phase: 'loading the shapes', start: t0, est }); setNow(t0);
    try {
      const { shapes, vocab } = await loadShapes(config.index);
      const job = startValidation({
        quads: g.quads, shapes, vocab,
        onProgress: (p) => setRun((r) => (r ? { ...r, phase: p.phase } : r)),
      });
      runRef.current = job;
      setRun((r) => ({ ...r, phase: 'starting', cancel: job.cancel }));
      const result = await job.promise;
      onReport(withReport(g.quads, result.reportNq), { ...result, browserSeconds: (performance.now() - t0) / 1000 });
    } catch (e) {
      if (e.message !== 'cancelled') setError(e.message);
    } finally {
      runRef.current = null; setRun(null);
    }
  };

  const save = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([toNQuads(g.quads)], { type: 'application/n-quads' }));
    a.download = `${fileName}.validated.nq`; a.click(); URL.revokeObjectURL(a.href);
  };

  if (run) {
    const elapsed = (now - run.start) / 1000;
    // time-based bar (the phases are very uneven); never full before the result is there
    const frac = Math.min(0.95, elapsed / Math.max(run.est, elapsed * 1.1));
    const left = run.est - elapsed;
    return (
      <span className="validation running" title="Validating in your browser; the data is not uploaded anywhere">
        <progress value={frac} max={1} />
        <span>{run.phase} · {fmt(elapsed)}{left > 1 ? ` of about ${fmt(run.est)}` : ', almost done (estimate exceeded)'}</span>
        <button onClick={() => run.cancel?.()} disabled={!run.cancel}>Cancel</button>
      </span>
    );
  }
  if (done) {
    return (
      <span className="validation">
        <button onClick={save} title={'Save your data together with the SHACL report as one N-Quads file.\n'
          + 'Open that file later with "Open Turtle file…" to see the report again without re-running the validation.'}>
          Save data + report (.nq)</button>
        <span className="note" title={done.seconds ? `${done.triples?.toLocaleString() ?? '?'} triples. In the worker: reading ${done.seconds.parse.toFixed(1)} s, `
          + `cross-checks (SPARQL) ${done.seconds.sparql.toFixed(1)} s, basic rules ${done.seconds.core.toFixed(1)} s` : ''}>
          validated here in {fmt(done.browserSeconds)}</span>
      </span>
    );
  }
  if (g?.hasReport) return null; // the file brings its own report
  return (
    <span className="validation">
      <button className="validate-btn" disabled={!g} onClick={start}
        title={`Check this file against ${config.label || 'the SHACL shapes'}.\nRuns in your browser; nothing is uploaded. `
          + `${nTriples.toLocaleString()} triples, about ${fmt(est)}. Violations and warnings then appear on the cards.`}>
        Run SHACL validation</button>
      <span className="note">about {fmt(est)}</span>
      {error && <span className="validation-error" title={error}>failed: {error.slice(0, 80)}</span>}
    </span>
  );
}
