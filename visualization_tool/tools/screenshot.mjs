#!/usr/bin/env node
// Visual check: build the viewer, serve dist/ on a local port, take headless-browser screenshots, stop the server.
// This is how changes to the viewer are checked (there are no automated visual tests).
//
//   node tools/screenshot.mjs out.png "data=slide25.nq"
//   node tools/screenshot.mjs shots/ "data=slide25.nq" "data=sample_evidence_graph.nq&layout=slide"
//   node tools/screenshot.mjs out.png "data=pilot_bgc.nq" --no-build --size 2200,1400
//
// Arguments: an output .png (one query) or a directory (several queries, files named after the queries), then the
// URL query strings (see README: data, focus, profile, runs, layout, terms). Options: --no-build (use existing dist/),
// --size W,H (default 2200,1400), --port N (default 4199), --wait MS (virtual time budget, default 15000).
// Browser: $BROWSER, else Edge or Chrome in their usual places (Windows, macOS, Linux).
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); if (i < 0) return def; const v = args[i + 1]; args.splice(i, 2); return v; };
const flag = (name) => { const i = args.indexOf(name); if (i < 0) return false; args.splice(i, 1); return true; };
const size = opt('--size', '2200,1400'), port = opt('--port', '4199'), wait = opt('--wait', '15000');
const noBuild = flag('--no-build');
const [out, ...queries] = args;
if (!out || !queries.length) { console.error('usage: node tools/screenshot.mjs <out.png | dir/> <query> [query ...] [--no-build] [--size W,H]'); process.exit(2); }

const BROWSERS = [process.env.BROWSER,
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/microsoft-edge'].filter(Boolean);
const browser = BROWSERS.find((b) => existsSync(b));
if (!browser) { console.error('no Chrome/Edge found; set BROWSER=/path/to/browser'); process.exit(2); }

const npx = process.platform === 'win32' ? 'npx.cmd' : 'npx';
if (!noBuild) {
  const b = spawnSync(npx, ['vite', 'build'], { cwd: ROOT, stdio: 'inherit', shell: process.platform === 'win32' });
  if (b.status !== 0) process.exit(b.status ?? 1);
}
const server = spawn(npx, ['vite', 'preview', '--port', port, '--strictPort'], { cwd: ROOT, shell: process.platform === 'win32' });
const stop = () => { if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(server.pid), '/T', '/F']); else server.kill(); };

const ready = async () => {
  for (let i = 0; i < 60; i++) {
    try { if ((await fetch(`http://localhost:${port}/`)).ok) return; } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error('vite preview did not start');
};

try {
  await ready();
  const many = queries.length > 1 || out.endsWith('/') || out.endsWith('\\');
  if (many) mkdirSync(out, { recursive: true });
  for (const q of queries) {
    const file = many ? join(out, q.replace(/[^A-Za-z0-9._-]+/g, '_').slice(0, 120) + '.png') : out;
    const r = spawnSync(browser, ['--headless=new', '--disable-gpu', `--window-size=${size}`, `--virtual-time-budget=${wait}`,
      `--screenshot=${resolve(file)}`, `http://localhost:${port}/?${q}`], { encoding: 'utf8' });
    console.log(existsSync(file) ? `wrote ${file}  (?${q})` : `FAILED ${q}: ${r.stderr?.slice(0, 300)}`);
  }
} finally { stop(); }
