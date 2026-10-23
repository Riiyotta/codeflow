/**
 * Validates ia.json against its own stated invariants.
 *
 * ia.json's `meta` block makes claims (total routes, total templates) and each
 * section's `scope` string is prose that implicitly claims a route/template
 * count too. Those are independent of the per-template data actually encoded —
 * if they don't reconcile, either the transcription is wrong or the source
 * itself is inconsistent, and both are worth knowing before anyone builds
 * against this IA.
 *
 * This script derives every check from ia.json's own data — it has no
 * hardcoded numbers for any particular project.
 *
 * Run from the project directory that contains ia.json:
 *   node validate.mjs
 */
import { readFileSync } from 'node:fs';

const ia = JSON.parse(readFileSync(new URL('./ia.json', import.meta.url)));
const problems = [];
const notes = [];
const ok = (label, got, want) => {
  if (got === want) console.log(`  ok    ${label}: ${got}`);
  else {
    console.log(`  FAIL  ${label}: got ${got}, expected ${want}`);
    problems.push(`${label}: got ${got}, expected ${want}`);
  }
};

console.log('\nTOTALS');
const routeSum = ia.templates.reduce((n, t) => n + t.routeCount, 0);
if (ia.meta.totalRoutes !== undefined) ok('routes across templates', routeSum, ia.meta.totalRoutes);
else console.log(`  info  routes across templates: ${routeSum} (meta.totalRoutes not set)`);

if (ia.meta.totalTemplates !== undefined) ok('template count', ia.templates.length, ia.meta.totalTemplates);
else console.log(`  info  template count: ${ia.templates.length} (meta.totalTemplates not set)`);

console.log('\nREFERENTIAL INTEGRITY');
const defined = new Set(Object.keys(ia.sections));
const used = new Set(ia.templates.flatMap((t) => t.sections));
const undef = [...used].filter((s) => !defined.has(s));
const unused = [...defined].filter((s) => !used.has(s));
ok('undefined section references', undef.length, 0);
if (undef.length) console.log('        ' + undef.join(', '));
ok('defined but unused sections', unused.length, 0);
if (unused.length) console.log('        ' + unused.join(', ') + '  (fine if intentionally future/reserved, otherwise dead data)');

console.log('\nCATEGORY COVERAGE');
const cats = new Set(Object.keys(ia.categories || {}));
const badCat = Object.entries(ia.sections).filter(([, s]) => !cats.has(s.category));
ok('sections with an unknown category', badCat.length, 0);
if (badCat.length) console.log('        ' + badCat.map(([id]) => id).join(', '));

console.log('\nCHROME PARTITION');
const chromeGroups = {};
for (const t of ia.templates) {
  const key = t.chrome ?? 'unspecified';
  chromeGroups[key] = (chromeGroups[key] || 0) + t.routeCount;
}
for (const [chrome, n] of Object.entries(chromeGroups)) {
  console.log(`  info  chrome="${chrome}": ${n} routes`);
}

console.log('\nSECTION REUSE (how many templates use each)');
const reuse = {};
for (const t of ia.templates) for (const s of t.sections) reuse[s] = (reuse[s] || 0) + 1;
const byReuse = Object.entries(reuse).sort((a, b) => b[1] - a[1]);
for (const [id, n] of byReuse) {
  const routes = ia.templates.filter((t) => t.sections.includes(id))
                             .reduce((s, t) => s + t.routeCount, 0);
  console.log(`  ${String(n).padStart(2)} templates · ${String(routes).padStart(3)} routes  ${id}`);
}

console.log('\nSINGLE-USE SECTIONS (candidates to keep page-local, not shared)');
const singleUse = byReuse.filter(([, n]) => n === 1).map(([id]) => id);
console.log(singleUse.length ? '  ' + singleUse.join('\n  ') : '  (none)');

// Heuristic prose-vs-data reconciliation: a scope string often embeds a number
// ("all 247 routes", "the 118 chrome-less routes"). Extract every standalone
// number in the scope text and flag it if it doesn't match this section's
// actual computed route count — this is informational, not a hard failure,
// because prose can legitimately describe a different (but still true) set
// (e.g. "the toolbar" count vs "chrome-less" count over the same routes).
console.log('\nSCOPE PROSE vs COMPUTED ROUTE COUNTS (informational)');
let anyScopeNote = false;
for (const [id, s] of Object.entries(ia.sections)) {
  if (!s.scope) continue;
  const actual = ia.templates.filter((t) => t.sections.includes(id))
                             .reduce((sum, t) => sum + t.routeCount, 0);
  const numbers = [...s.scope.matchAll(/\d+/g)].map((m) => Number(m[0]));
  const mismatched = numbers.filter((n) => n !== actual);
  if (mismatched.length) {
    anyScopeNote = true;
    const note = `${id}: scope says [${mismatched.join(', ')}] but computed route count is ${actual}. ` +
      `Scope: "${s.scope}"`;
    notes.push(note);
    console.log(`  note  ${id}: scope mentions ${mismatched.join(', ')}, computed = ${actual}`);
  }
}
if (!anyScopeNote) console.log('  (every number in every scope string matches its computed route count)');

if (notes.length) {
  console.log('\nNOTES (review — may be a real ambiguity in the source, or may be fine)');
  notes.forEach((n) => console.log('  · ' + n.replace(/(.{78}) /g, '$1\n    ')));
}

console.log(
  problems.length
    ? `\n${problems.length} INCONSISTENCY(IES)\n` + problems.map((p) => '  - ' + p).join('\n')
    : '\nAll hard invariants reconcile.'
);
process.exit(problems.length ? 1 : 0);
