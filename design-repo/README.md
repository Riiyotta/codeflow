# codeflow waitlist design-repo

This repo is an AI-ready design contract extracted from a clone of **https://www.thecodeflow.co/**. That site is a single-route Webflow waitlist page for a JavaScript course. The repo gives you tokens, primitives, components, section contracts, one page template, a compatibility graph, a Draft-07 PageSpec schema, a semantic validator and an adversarial suite. A generator uses these to compose pages without inventing colours, copy budgets, sections or assets.

**Status:** `design-review-pending`, `productionApproved: false` (see `registry.manifest.json`). Version 1.1.0.

## Read this first: real, live site

The source is a real site by a real named author, identified on the page only as `federic.ooo`. It is load-bearing for how the repo may be used:

- **Never reproduce or imitate these:** the "THE CODE FLOW. CO" logo, the Rubik's-cube GLB model and its matcap and colour-map textures, the og image and favicon, the author's links (personal site, Twitter redirect, privacy-policy Google Doc), or the Discord trademark glyph. `assets/asset-roles.json` gives each of these the policy `must-not-reproduce`. Only `placeholder` sources are valid.
- **Never reuse live endpoints.** The original form posts to a live MailChimp list, and the page loads Umami analytics with a real website id. Both have the policy `must-not-reuse-live-endpoint`, and their real hosts and ids are in `refDenylist`. The clone itself has no form `action` (verified: `mv.endpoint.clone-has-no-action`).
- **Commercial fonts.** Helvetica Neue and Helvetica Neue Condensed have the policy `license-required`. Use the fallback stack or a font the deployer has licensed. Firacode is also `license-required`, because the project has no licence file for it.
- **Real copy** appears only in `schema/example.pagespec.json`, which has `contentProvenance: "evidence-reference"`. It is reference material, not publishable content. A PageSpec marked `generated` is rejected if any of its text contains the brand or the author identity (`BRAND_PASSOFF`). That includes a footer wordmark spelling the brand.
- Eleven compliance-critical roles are **pinned**: `schema/semantic_validate.py` (`PINNED_POLICIES`) compares their policy against a hard-coded table. Changing one of them to a different policy that is still valid gets caught, not only a policy that isn't in the enum.
- Do not make this repository public.

## Layout

```
registry.manifest.json      status, versions, recomputed counts, sourceStack (documentation-only), entryPoints (inside this folder only)
tokens/00-foundation/       color, typography, radius, spacing, breakpoint, layering (z-index contract), icon-size, motion
tokens/10-semantic/         semantic roles -> foundation refs
tokens/20-component/        pill button, underline input, dot, rule line
tokens/30-layout/           container / block / timeline widths per breakpoint
tokens/themes/dark.json     the only theme (the site has no light mode)
tokens/llm/                 component-allowlist.json (versioned, closed), motion-patterns.json (closed vocabulary + reduced-motion fallbacks)
assets/asset-roles.json     closed assetRole enum, generation policies, ref / brand denylists
primitives/ components/     10 primitives, 6 components
sections/                   8 section contracts (8 variants): closed schema, `semantic` {id, category} vs `source` {id, tag, file, lines, citation}, retrievalEligible, maxWords, motion, structured responsive field, quirks
templates/templates.json    1 template, structured nodes {section, variant, required, repeatable}; route map
compatibility/graph.json    26 rules with severity; must agree with the validator's RULES (checked)
schema/                     pagespec.schema.json, section-contract.schema.json (closed), example.pagespec.json, semantic_validate.py, tests/adversarial_test.py
extraction/                 measured-values.json (citation ledger + sectionHeights), verify_all.py, prove_drift.py, wrapper_gate.py + wrapper-whitelist.json, measure_sections.mjs (optional)
```

## Counts (recomputed from disk by `extraction/verify_all.py`)

| key | count |
|---|---|
| tokens | 139 |
| primitives | 10 |
| components | 6 |
| sections | 8 |
| sectionVariants | 8 |
| templates | 1 |
| routes | 1 |
| assetRoles | 13 |
| pinnedAssetRoles | 11 |
| retrievalIneligibleSections | 1 |
| motionPatterns | 18 |
| compatibilityRules | 26 |
| measuredValueEntries | 95 |

## Page shape

There is one route (`/`) and one template, `template.waitlist-landing`. Every node is required and non-repeatable, because that is the only composition the source shows:

1. `shell.nav` (shell): the fixed bar. Its Discord link is in the DOM but hidden at every width.
2. `hero.course-intro` (hero): anchor `intro`. The only hero.
3. `list.numbered-topics` (list): anchor `content`. It has 20 items. Desktop shows counters, and only even items are offset (two of the source's selectors are invalid).
4. `content.block-pairs` / `feature-pairs` (content): anchor `cta`. Four labelled blocks about the course.
5. `cta.pitch-timeline` / `default` (cta): also anchor `cta`. The offer restated: heading, join CTA, price note, two blocks and a price timeline table. **The duplicate id is real on the source.** It is kept and produces a warning. Any other duplicate anchor is an error.
6. `cta.waitlist-form` (cta): anchor `signup`. Every CTA targets it.
7. `shell.footer-wordmark` (shell)
8. `layer.webgl-object` (layer): the fixed canvas, which comes after the page wrapper in the DOM. `retrievalEligible: false`.

Structural rules key on `(section, variant)`. Every section has one variant today; the keying stays so a later multi-variant section remains valid.

**Layering contract:** at widths above 991px, the words marked `behind-canvas` or `behind-canvas-deep` (z -11 / -21) paint *behind* the WebGL canvas (z -10). At 991px and below they become static and paint in front of it.

## Section contracts: taxonomy, provenance, retrieval

Each `sections/*.json` must satisfy the closed `schema/section-contract.schema.json` (no unknown fields anywhere).

- `semantic` `{id, category}` is the **taxonomy**: what the section is. `category` is a closed enum (`shell, hero, list, content, cta, layer`) and equals the id prefix. Conversion blocks (waitlist form, the pitch/price/join block) are `cta`; a `cta` or `priceNote` field may not sit in a generic `content`/`list` section (`CONVERSION_BLOCK_CLASSED_CTA`). The table is pinned twice: in `schema/semantic_validate.py` and, independently, in `extraction/verify_all.py`.
- `source` `{id, tag, file, lines, citation}` is **provenance**: the element in the real source. `verify_all.py` checks the file exists, the line range is in bounds, the first line opens `<tag` (with the `id`), the last line closes it, and the ledger entry named by `citation` cites the same file. With no source tree next to `design-repo/` this check downgrades to WARN (structure and ledger links are still checked).
- `retrievalEligible` (boolean, default `true`) marks utility/runtime UI that retrieval must skip: cookie/consent, modals, dialogs, overlays, toasts. `false` needs a `retrievalReason` of 30+ characters. Here only `layer.webgl-object` (a fixed, text-free decorative canvas) is `false`. The site has no cookie banner, modal, dialog or toast (grep of `src/` finds none); the signup success/failure message is a state inside `cta.waitlist-form`, not a separate section. The value is mirrored in the allowlist, pinned in the validator and independently in `verify_all.py`.

## Whole-page-wrapper gate

`extraction/wrapper_gate.py` (run by `verify_all.py`) reads `sectionHeights` in `extraction/measured-values.json`, measured at 1440x900 by the optional `extraction/measure_sections.mjs`:

- a `hero` section taller than 1800px warns; taller than 3000px fails;
- one in-flow section holding more than 50% of the in-flow page height warns, more than 60% fails (skipped, and reported as skipped, with fewer than 3 in-flow sections);
- a template section with no usable measurement, a stale measurement, a wrong viewport, or heights that do not add up to `pageHeight` is an error;
- `extraction/wrapper-whitelist.json` is the only way to exempt a failure (cap in px, 30+ character justification, reviewer `human:` or `agent-attestation:`). It is empty. An `agent-attestation` is an automated reviewer's claim, not a human sign-off.

Measured on this page (local production build, 1440x900): hero 810px, list 2258.94px (32% of in-flow height), page 7060px. Fixed elements (nav 74.97px, WebGL layer 900px) take no page height.

To re-measure: build and serve the project (`npx vite build --outDir <tmp>`, `npx vite preview --outDir <tmp> --port 5483`), then from `design-repo/` run `PLAYWRIGHT_MODULE=<playwright index.mjs> BASE_URL=http://localhost:5483/ node extraction/measure_sections.mjs --write`.

## Motion

The motion vocabulary is closed: 18 patterns in `tokens/llm/motion-patterns.json`. Every pattern is grounded in source code and CLONE_SPEC. The 2026-10-23 QA pass matched them against the live original, including anchor scroll and wheel scroll after a 60fps re-measure (`mv.qa.anchor-scroll`, `mv.qa.wheel-scroll`). No motion deltas are open.

Reveals replay every time an element re-enters the viewport. "Mobile" is detected from the user agent, not the width. Every node needs a `reducedMotionFallback`. **The source has no reduced-motion handling at all**, so these fallbacks are design-repo policy (`mv.motion.no-reduced-motion`).

## Known source quirks, documented rather than normalized

- Duplicate `id="cta"`.
- `.mt-xl` is used but never defined.
- Two of the counter nth-child selectors are invalid.
- The Discord link is always `display:none`.
- Marquee CSS exists but has no DOM, so there is deliberately **no marquee section**.
- `data-delay` is present but never read.
- `.z` words render behind the canvas.
- Correction found during this build: CLONE_SPEC §1 says `.cta-tx` sets 1rem. That rule exists only inside the 479px media query (`mv.type.cta-tx-discrepancy`).

## Verify

```bash
pip install -r requirements.txt   # jsonschema, used for the Draft-07 layer
python3 extraction/verify_all.py            # schema, semantics, parity, versions, counts, citations (range + quote), graph agreement, pins, tokens, hygiene
python3 schema/tests/adversarial_test.py    # every mutation rejected with its expected rule, every control passes
python3 extraction/prove_drift.py           # proves each drift check fails on injected drift (scratch copies in the OS temp dir; --scratch DIR to choose where)
python3 extraction/wrapper_gate.py          # the whole-page-wrapper gate on its own
python3 schema/semantic_validate.py my-page.pagespec.json
```

Citation paths in `extraction/measured-values.json` are relative to the source project root, which is the folder that contains `design-repo/`. If this folder ships alone, the citation check downgrades to WARN.

## Packaging

The source project is now a git repository. `design-repo.zip` is a generated build artifact, listed in the project-root `.gitignore` and not tracked (`git ls-files` shows no zip), so none is shipped from this commit. If one is needed, regenerate it last with the CLI `zip` after every check passes.
