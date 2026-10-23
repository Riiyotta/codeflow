# codeflow waitlist design-repo

This repo is an AI-ready design contract extracted from a clone of **https://www.thecodeflow.co/**. That site is a single-route Webflow waitlist page for a JavaScript course. The repo gives you tokens, primitives, components, section contracts, one page template, a compatibility graph, a Draft-07 PageSpec schema, a semantic validator and an adversarial suite. A generator uses these to compose pages without inventing colours, copy budgets, sections or assets.

**Status:** `design-review-pending`, `productionApproved: false` (see `registry.manifest.json`).

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
sections/                   7 section contracts (8 section variants), each with maxWords, motion, structured responsive field, quirks
templates/templates.json    1 template, structured nodes {section, variant, required, repeatable}; route map
compatibility/graph.json    21 rules with severity; must agree with the validator's RULES (checked)
schema/                     pagespec.schema.json, example.pagespec.json, semantic_validate.py, tests/adversarial_test.py
extraction/                 measured-values.json (citation ledger), verify_all.py, prove_drift.py
```

## Counts (recomputed from disk by `extraction/verify_all.py`)

| key | count |
|---|---|
| tokens | 139 |
| primitives | 10 |
| components | 6 |
| sections | 7 |
| sectionVariants | 8 |
| templates | 1 |
| routes | 1 |
| assetRoles | 13 |
| pinnedAssetRoles | 11 |
| motionPatterns | 18 |
| compatibilityRules | 21 |
| measuredValueEntries | 94 |

## Page shape

There is one route (`/`) and one template, `template.waitlist-landing`. Every node is required and non-repeatable, because that is the only composition the source shows:

1. `shell.nav`: the fixed bar. Its Discord link is in the DOM but hidden at every width.
2. `hero.course-intro`: anchor `intro`.
3. `list.numbered-topics`: anchor `content`. It has 20 items. Desktop shows counters, and only even items are offset (two of the source's selectors are invalid).
4. `content.block-pairs` / `feature-pairs`: anchor `cta`.
5. `content.block-pairs` / `pitch-timeline`: also anchor `cta`. **The duplicate id is real on the source.** It is kept and produces a warning. Any other duplicate anchor is an error.
6. `form.waitlist`: anchor `signup`. Every CTA targets it.
7. `shell.footer-wordmark`
8. `layer.webgl-object`: the fixed canvas, which comes after the page wrapper in the DOM.

Structural rules key on `(section, variant)`, so the two `content.block-pairs` variants are allowed together.

**Layering contract:** at widths above 991px, the words marked `behind-canvas` or `behind-canvas-deep` (z -11 / -21) paint *behind* the WebGL canvas (z -10). At 991px and below they become static and paint in front of it.

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
python3 extraction/prove_drift.py           # proves each drift check fails on injected drift (scratch copies in the OS temp dir)
python3 schema/semantic_validate.py my-page.pagespec.json
```

Citation paths in `extraction/measured-values.json` are relative to the source project root, which is the folder that contains `design-repo/`. If this folder ships alone, the citation check downgrades to WARN.

## Packaging

The source project is **not a git repository**, so nothing is committed. `design-repo.zip` sits beside this folder as a build artifact. It is regenerated last, with the CLI `zip`, after every check passes. If the project is ever put under git, add `design-repo.zip` to the project-root `.gitignore` and confirm with `git ls-files` that it is not tracked.
