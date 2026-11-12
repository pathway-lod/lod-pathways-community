// Main-thread side of the in-browser SHACL validation: load the shapes named in the profile, run the worker,
// merge its report into the loaded quads, and write data + report as one N-Quads file (to save and reopen later).
// Knows no evidence vocabulary; the shapes come from the profile ("validation": {"index": ...}).
import { Parser, Writer } from 'n3';

const REPORT = 'urn:lodviz:report';
const SKIP = new Set([REPORT, 'urn:lodviz:vocab']); // not data: an old report, the vocabulary (sent separately)

// Shape files and vocabulary listed in index.json (paths relative to it). Fetched once per page.
let shapesPromise = null;
export function loadShapes(indexUrl) {
  if (!shapesPromise) {
    shapesPromise = (async () => {
      const base = new URL(indexUrl, window.location.href);
      const get = async (u) => { const r = await fetch(new URL(u, base)); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.text(); };
      const idx = JSON.parse(await get(base.href));
      return { shapes: await Promise.all(idx.shapes.map(get)), vocab: idx.vocab ? await get(idx.vocab) : '' };
    })();
    shapesPromise.catch(() => { shapesPromise = null; }); // allow a retry after a network error
  }
  return shapesPromise;
}

// Rough duration in seconds, shown before and during the run. Fitted to Edge (headless, 2026-11-12, one laptop):
// 54k triples 11.3 s, 27k 6.5 s, 7.5k 1.8 s, a 30-claim file 1.7 s (mostly starting the worker). Only an estimate;
// slower machines take longer, and files with many per-node cross-checks too.
export const estimateSeconds = (nTriples) => 1 + nTriples * 0.0002;

// N-Quads keep blank-node labels, so the report can refer to the data's blank nodes (evidence nodes)
export const toNQuads = (quads) => new Writer({ format: 'N-Quads' }).quadsToString(quads);
export const dataQuads = (quads) => quads.filter((q) => !SKIP.has(q.graph.value));

/**
 * Start a validation of `quads` (all graphs except an old report and the vocabulary).
 * @returns {{ promise: Promise<object>, cancel: () => void }} promise resolves with the worker's result
 *   ({ reportNq, counts, conforms, seconds, sparql }); rejects on error or cancel.
 */
export function startValidation({ quads, shapes, vocab, onProgress }) {
  const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
  let reject;
  const promise = new Promise((res, rej) => {
    reject = rej;
    worker.onmessage = ({ data }) => {
      if (data?.type === 'progress') onProgress?.(data);
      else if (data?.type === 'done') {
        worker.terminate();
        console.info('SHACL validation (seconds):', data.seconds, 'SPARQL queries [s, rows, query]:', data.sparql?.queryTimes);
        res(data);
      }
      else if (data?.type === 'error') { worker.terminate(); rej(new Error(data.message)); }
      // anything else (e.g. a library's own message) is ignored
    };
    worker.onerror = (e) => { worker.terminate(); rej(new Error(e.message || 'validation worker failed')); };
  });
  worker.postMessage({ dataNq: toNQuads(dataQuads(quads)), shapes, vocab });
  return { promise, cancel: () => { worker.terminate(); reject(new Error('cancelled')); } };
}

// The loaded quads with the report added (graph urn:lodviz:report), replacing an older report; keeps the file's prefixes
export function withReport(quads, reportNq) {
  const report = new Parser({ format: 'N-Quads', blankNodePrefix: '' }).parse(reportNq);
  const out = quads.filter((q) => q.graph.value !== REPORT).concat(report);
  out.prefixes = quads.prefixes;
  return out;
}
