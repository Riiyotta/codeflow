/**
 * Generates human-readable IA views from ia.json.
 *
 * Everything downstream derives from the single source of truth (ia.json), so a
 * section's description can never disagree between two templates — the usual
 * failure mode of a hand-maintained IA document.
 *
 * Run from the project directory that contains ia.json:
 *   node build.mjs   →  writes IA.md and matrix.csv next to it
 */
import { readFileSync, writeFileSync } from 'node:fs';

const ia = JSON.parse(readFileSync(new URL('./ia.json', import.meta.url)));
const { sections, templates, meta, categories } = ia;

const routesFor = (id) =>
  templates.filter((t) => t.sections.includes(id)).reduce((s, t) => s + t.routeCount, 0);

const pct = (n, d) => (d ? ((n / d) * 100).toFixed(0) : '0');

/* ---------------------------------------------------------------- IA.md */

const L = [];
L.push(`# ${meta.title || meta.source || 'information architecture'}`);
L.push('');
if (meta.source) L.push(`Source: ${meta.source}${meta.mirror ? ` · ${meta.mirror}` : ''}`);
if (meta.status) L.push(`Status: **${meta.status}**${meta.productionApproved !== undefined ? ` · production approved: **${meta.productionApproved}**` : ''}`);
L.push(`${meta.totalRoutes} routes · ${meta.totalTemplates} templates · ${Object.keys(sections).length} unique sections`);
L.push('');
L.push('> Generated from `ia.json` by `build.mjs`. Edit the JSON, not this file.');
L.push('');

L.push('## Shape of the site');
L.push('');
const byRouteCount = [...templates].sort((a, b) => b.routeCount - a.routeCount);
const top = byRouteCount.slice(0, Math.min(3, byRouteCount.length));
const topRoutes = top.reduce((s, t) => s + t.routeCount, 0);
L.push(`The largest ${top.length} template${top.length > 1 ? 's' : ''} (${top.map((t) => t.name).join(', ')}) ` +
  `account${top.length === 1 ? 's' : ''} for ${topRoutes} of ${meta.totalRoutes} routes (${pct(topRoutes, meta.totalRoutes)}%). ` +
  `The remaining ${meta.totalRoutes - topRoutes} routes span ${templates.length - top.length} template${templates.length - top.length === 1 ? '' : 's'}.`);
L.push('');
L.push('| template | routes | share |');
L.push('|---|---:|---:|');
for (const t of byRouteCount) {
  L.push(`| ${t.name} | ${t.routeCount} | ${pct(t.routeCount, meta.totalRoutes)}% |`);
}
L.push('');

L.push('## Page chrome');
L.push('');
const chromeGroups = {};
for (const t of templates) {
  const key = t.chrome ?? 'unspecified';
  (chromeGroups[key] ??= []).push(t);
}
for (const [chrome, ts] of Object.entries(chromeGroups)) {
  const n = ts.reduce((s, t) => s + t.routeCount, 0);
  L.push(`**${n} routes carry chrome = \`${chrome}\`** — ${ts.map((t) => t.name).join(', ')}.`);
  L.push('');
}

L.push('## Sections by reuse');
L.push('');
L.push('How widely a section is shared determines whether it belongs in a shared');
L.push('component library or stays local to its page.');
L.push('');
const anyImpl = Object.values(sections).some((s) => s.implementedBy);
L.push(anyImpl
  ? '| section | category | templates | routes | implementation | scope |'
  : '| section | category | templates | routes | scope |');
L.push(anyImpl ? '|---|---|---:|---:|---|---|' : '|---|---|---:|---:|---|');
const byReuse = Object.entries(sections)
  .map(([id, s]) => ({
    id, ...s,
    templates: templates.filter((t) => t.sections.includes(id)).length,
    routes: routesFor(id),
  }))
  .sort((a, b) => b.routes - a.routes || b.templates - a.templates);
for (const s of byReuse) {
  L.push(anyImpl
    ? `| \`${s.id}\` | ${s.category} | ${s.templates} | ${s.routes} | ${s.implementedBy ? `\`${s.implementedBy}\`` : '_not yet built_'} | ${s.scope || ''} |`
    : `| \`${s.id}\` | ${s.category} | ${s.templates} | ${s.routes} | ${s.scope || ''} |`);
}
L.push('');

const shared = byReuse.filter((s) => s.templates > 1);
const local = byReuse.filter((s) => s.templates === 1);
L.push(`**${shared.length} shared section${shared.length === 1 ? '' : 's'}** appear${shared.length === 1 ? 's' : ''} in more than one template and belong${shared.length === 1 ? 's' : ''} in a component library.`);
L.push('');
L.push(`**${local.length} single-use section${local.length === 1 ? '' : 's'}** appear${local.length === 1 ? 's' : ''} in exactly one template. Building these`);
L.push('as "reusable" components up front would be speculative — keep them page-local');
L.push('until a second caller actually appears.');
L.push('');

if (anyImpl) {
  const unbuilt = byReuse.filter((s) => !s.implementedBy);
  if (unbuilt.length) {
    L.push(`**${unbuilt.length} section${unbuilt.length === 1 ? '' : 's'} have no \`implementedBy\` yet** — not necessarily missing, just not linked to a component in this pass: ${unbuilt.map((s) => `\`${s.id}\``).join(', ')}.`);
    L.push('');
  }
}

L.push('## Templates');
L.push('');
for (const t of templates) {
  L.push(`### ${t.name} — \`${t.id}\``);
  L.push('');
  const routeLine = t.routePattern
    ? `${t.routeCount} routes · \`${t.routePattern}\`${t.routeRange ? ` (${t.routeRange[0]}–${t.routeRange[1]})` : ''}`
    : `${t.routeCount} route${t.routeCount > 1 ? 's' : ''} · ${(t.routes || []).map((r) => `\`${r}\``).join(', ')}`;
  L.push(`${routeLine}${t.chrome !== undefined ? ` · chrome: **${t.chrome}**` : ''}`);
  L.push('');
  L.push('| # | category | section | |');
  L.push('|---:|---|---|---|');
  t.sections.forEach((id, i) => {
    const s = sections[id];
    if (!s) { L.push(`| ${i + 1} | ?? | \`${id}\` | **undefined section** |`); return; }
    const reuse = templates.filter((x) => x.sections.includes(id)).length;
    const tag = reuse > 1 ? `shared ×${reuse}` : 'page-local';
    L.push(`| ${i + 1} | ${s.category} | \`${id}\` | ${tag} |`);
  });
  L.push('');
}

L.push('## Section reference');
L.push('');
for (const cat of Object.keys(categories)) {
  const inCat = Object.entries(sections).filter(([, s]) => s.category === cat);
  if (!inCat.length) continue;
  L.push(`### ${cat}`);
  L.push('');
  L.push(`_${categories[cat]}_`);
  L.push('');
  for (const [id, s] of inCat) {
    L.push(`**\`${id}\`** — ${s.description}`);
    L.push('');
    const implLine = s.implementedBy ? ` · implemented by \`${s.implementedBy}\`` : '';
    L.push(`· ${s.scope || ''} · appears on ${routesFor(id)} routes${implLine}`);
    L.push('');
  }
}

writeFileSync(new URL('./IA.md', import.meta.url), L.join('\n'));

/* ------------------------------------------------------------ matrix.csv */

const head = ['section', 'category', 'templates', 'routes', ...templates.map((t) => t.name)];
const rows = [head.join(',')];
for (const s of byReuse) {
  const cells = templates.map((t) => (t.sections.includes(s.id) ? 'x' : ''));
  rows.push([s.id, s.category, s.templates, s.routes, ...cells].join(','));
}
rows.push(['ROUTE COUNT', '', '', meta.totalRoutes, ...templates.map((t) => t.routeCount)].join(','));
writeFileSync(new URL('./matrix.csv', import.meta.url), rows.join('\n'));

console.log(`IA.md      ${L.length} lines`);
console.log(`matrix.csv ${rows.length} rows × ${head.length} cols`);
console.log(`\n${shared.length} shared sections · ${local.length} page-local`);
