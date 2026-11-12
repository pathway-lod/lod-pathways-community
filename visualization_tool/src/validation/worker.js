// Web Worker: runs the SHACL validation (engine.js) off the main thread, so the page stays responsive.
// in:  { dataNq, shapes: [turtle...], vocab }
// out: { type: 'progress', phase, done, total } ... then { type: 'done', reportNq, counts, ... } or { type: 'error', message }
import './worker-shim.js'; // must stay first
import { validate } from './engine.js';

self.onmessage = async ({ data }) => {
  try {
    const r = await validate({ ...data, onProgress: (p) => self.postMessage({ type: 'progress', ...p }) });
    self.postMessage({ type: 'done', ...r });
  } catch (e) {
    self.postMessage({ type: 'error', message: e?.message || String(e) });
  }
};
