#!/usr/bin/env node
// Optional: measures every template section's rendered height and records it in
// extraction/measured-values.json -> sectionHeights (read by extraction/wrapper_gate.py).
// verify_all.py never runs this (no browser needed to verify); re-run it after the page changes.
//
// Usage (from design-repo/):
//   PLAYWRIGHT_MODULE=<path-or-specifier of playwright's index.mjs> \
//   BASE_URL=http://localhost:5483/  node extraction/measure_sections.mjs [--write]
//
// BASE_URL is a locally served build of the source page (e.g. `vite build --outDir <tmp>` then
// `vite preview --outDir <tmp> --port 5483`). Without --write it only prints. Viewport is read from
// sectionHeights.viewport (1440x900). No absolute path is stored in this repo: PLAYWRIGHT_MODULE and
// BASE_URL come from the environment.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';

const LEDGER = fileURLToPath(new URL('./measured-values.json', import.meta.url));
const modRef = process.env.PLAYWRIGHT_MODULE;
if (!modRef) { console.error('set PLAYWRIGHT_MODULE to the playwright module to import'); process.exit(2); }
const baseUrl = process.env.BASE_URL || 'http://localhost:5483/';
const write = process.argv.includes('--write');

const { chromium } = await import(/^(\/|[A-Za-z]:\\)/.test(modRef) ? pathToFileURL(modRef).href : modRef);
const ledger = JSON.parse(readFileSync(LEDGER, 'utf8'));
const sh = ledger.sectionHeights;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: sh.viewport });
await page.goto(baseUrl, { waitUntil: 'load' });
await page.waitForTimeout(3000); // let the reveal/scramble motion settle

const result = await page.evaluate((defs) => {
  const out = {};
  for (const [key, d] of Object.entries(defs)) {
    const el = document.querySelectorAll(d.selector)[d.nth || 0];
    if (!el) { out[key] = null; continue; }
    const r = el.getBoundingClientRect();
    out[key] = { heightPx: Math.round(r.height * 100) / 100, position: getComputedStyle(el).position };
  }
  return { sections: out, pageHeight: document.documentElement.scrollHeight };
}, sh.sections);
const version = browser.version();
await browser.close();

let missing = 0;
for (const [key, d] of Object.entries(sh.sections)) {
  const m = result.sections[key];
  if (!m) { missing++; console.log('MISSING  ' + key + '  (' + d.selector + ')'); continue; }
  const inFlow = !['fixed', 'absolute'].includes(m.position);
  console.log((inFlow ? 'in-flow ' : 'overlay ') + String(m.heightPx).padStart(9) + 'px  ' + key);
  if (write) { d.heightPx = m.heightPx; d.position = m.position; d.inFlow = inFlow; }
}
console.log('pageHeight ' + result.pageHeight);
if (missing) { console.error(missing + ' selector(s) matched nothing; not writing'); process.exit(1); }
if (write) {
  sh.pageHeight = result.pageHeight;
  sh.measuredOn = new Date().toISOString().slice(0, 10);
  sh.tool = 'playwright chromium ' + version + ' via measure_sections.mjs';
  writeFileSync(LEDGER, JSON.stringify(ledger, null, 2) + '\n');
  console.log('wrote sectionHeights');
}
