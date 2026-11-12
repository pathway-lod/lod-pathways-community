// Imported first by worker.js (ES modules run in import order). Some browser builds inside Comunica expect a page:
// they read `window.Headers` when loaded, and a setImmediate polyfill would fall back to window.postMessage (which in a
// worker would message the main page). Give them the worker's global object as `window`, and a real setImmediate
// (MessageChannel, no 4 ms timer clamping) so the polyfill keeps its hands off.
if (typeof globalThis.window === 'undefined') globalThis.window = globalThis;
if (typeof globalThis.setImmediate === 'undefined') {
  const tasks = new Map();
  let next = 1;
  const ch = new MessageChannel();
  ch.port1.onmessage = ({ data: id }) => {
    const t = tasks.get(id);
    if (t) { tasks.delete(id); t[0](...t[1]); }
  };
  globalThis.setImmediate = (fn, ...args) => { const id = next++; tasks.set(id, [fn, args]); ch.port2.postMessage(id); return id; };
  globalThis.clearImmediate = (id) => { tasks.delete(id); };
}
