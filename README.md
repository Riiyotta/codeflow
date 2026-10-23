# thecodeflow.co clone

Local React + Vite rebuild of https://www.thecodeflow.co/ (a single-page waitlist site for a JavaScript course).

```bash
npm install
npm run dev   # http://localhost:5273
```

The page copy, logo, cube model and the Helvetica Neue font files belong to the original site's author. Keep this clone for local study and replace them before deploying anywhere public.

## Information architecture

`ia.json` is the only IA file to hand-edit. `IA.md` and `matrix.csv` are **generated** — never edit them directly. After changing `ia.json`, re-run:

```bash
node validate.mjs && node build.mjs
```

`validate.mjs` checks that route and template totals add up, that every section a template references is defined (and every defined section is used), and that every section's category exists. `build.mjs` regenerates `IA.md` and `matrix.csv`.

### Findings

- The site is 1 route (`/`) built from 1 template of 10 sections in a fixed order: nav, hero, curriculum list, course feature blocks, pitch, timeline/price blocks, price table, signup and footer, plus a fixed WebGL cube layer behind all of them.
- With only one template, all 10 sections count as single-use at the template level, so the IA itself shows no sharing. The real reuse is below the section level: `features.course-blocks` and `conversion.timeline-price-blocks` are two different sections (feature content vs launch/price facts) rendered by the same `Features.jsx > Block` component, and the hero and pitch both use the shared `CtaButton` and `PriceNote` pieces. They stay separate section ids because they carry different content, not because they're built differently.
- Every section has an `implementedBy` component, so `IA.md` doubles as a map of `src/`. Three sections (pitch, timeline/price blocks, price table) live together in `Pricing.jsx`, matching the original's second `#cta` section. That's a candidate to split if those blocks ever need to move independently.
- The original page uses `id="cta"` on two different sections. The IA keeps them as two distinct sections (`features.course-blocks` and the second `#cta`'s three blocks) rather than treating the shared id as one section.

The measured visual and motion values live in `CLONE_SPEC.md`. A machine-validated design-repo (tokens, section contracts, schema) is being built under `design-repo/`.
