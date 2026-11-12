// Hand-off between the global view and the card viewer (2026-11-11): one record in the browser's IndexedDB,
// { source, name, text, claims, title }. Used instead of URL parameters because a selection can hold hundreds of claim
// IRIs (too long for a URL) and a file opened from disk cannot be reopened by URL (its text has to travel along).
// The record stays until the next hand-off, so reloading either page keeps working. Every call is wrapped: in a
// private window or with storage blocked it returns null / false and the caller falls back.

const DB = 'lodviz', STORE = 'handoff', KEY = 'current';

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function putHandoff(record) {
  try {
    const db = await open();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put({ ...record, created: Date.now() }, KEY);
      tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
    });
    db.close();
    return true;
  } catch { return false; }
}

export async function getHandoff() {
  try {
    const db = await open();
    const rec = await new Promise((resolve, reject) => {
      const req = db.transaction(STORE).objectStore(STORE).get(KEY);
      req.onsuccess = () => resolve(req.result || null); req.onerror = () => reject(req.error);
    });
    db.close();
    return rec;
  } catch { return null; }
}

// URL of the other page for a hand-off record: bundled data also travels in the URL, so a plain reload works too
export const handoffUrl = (page, source) =>
  `${page}?handoff=1${source && !source.startsWith('local:') ? `&data=${encodeURIComponent(source)}` : ''}`;
