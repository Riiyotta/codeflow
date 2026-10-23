Source: https://www.thecodeflow.co/

# thecodeflow.co clone spec (single route `/`)

How this was measured: on 2026-10-23 I ran Playwright against the live site at 1440x900 and 375x812, read computed styles and rects, logged the network, and sampled animation frames. I also read the saved copy (`Join*.html`, `Join*_files/codeflowco.shared.c5325f8b3.min.css`) and the custom bundle (`Join*_files/app.js`). The saved `app.js` is **byte-identical** to the live bundle at `https://codeflowco-webflow.vercel.app/app.js`. The live HTML first tries `http://localhost:6545/app.js`, which fails, and its `onerror` then injects the vercel URL. The jsdelivr `app.10.js` reference is commented out and not used.

The bundle includes **GSAP 3.13.0** with SplitText, ScrambleTextPlugin and CustomEase (since 3.13 these plugins are free on npm), **Lenis 1.3.4**, **OGL** (WebGL renderer plus GLTFLoader) and a tiny event emitter. Everything is driven by `data-*` attributes.

---

## 0. Global

### Tokens (`:root`)
| var | value |
|---|---|
| `--black` | `#0c0c0c` (page bg; animated by the "solve cube" easter egg) |
| `--white` | `#f5d0e6` (pink, used for all text, borders, lines, dots) |
| `--grey` | `#707070` (focused input underline) |
| `--dark` | `#181818` (unused) |
| `--space--py` / `--space--px` | `5vh` / `3vw` (unused, only on `.fx-w`) |
| `--100vh` | set by JS to `${innerHeight}px` on `<html>` (resize) |

WebGL clear color in the shader: `COL_BG = vec3(0.0588)` = `#0f0f0f`.

### Body
`background:#0c0c0c; color:#f5d0e6; cursor:crosshair; font-family:"Helvetica Neue",Arial,sans-serif; font-size:14px; line-height:1.1em (15.4px)`. The page has no custom cursor element. `crosshair` is the only cursor effect.
`html` gets class `lenis` from Lenis (no `lenis-smooth` CSS is shipped).

### Global embed CSS (inline `<style>` at top of body, copy verbatim)
```css
.FULLPAGEWRAPPER,body,html{overscroll-behavior:none}
body,h1,h2,h3,h4,html,p{user-select:none;-webkit-user-select:none}
[data-selectable]{user-select:text;-webkit-user-select:text}
[data-z="u"]{position:relative;z-index:-11}
[data-counter]{counter-reset:itemcounter}
[data-counter] li{position:relative;counter-increment:itemcounter}
@media (min-width:991px){
  [data-counter] li:nth-child(2n){transform:translateX(10%)}
  [data-counter] li:nth-child(n*2+2){transform:translateX(-10%)}   /* INVALID selector -> ignored by browser */
  [data-counter] li:nth-child(n*3+1){transform:translateX(-50%)}   /* INVALID selector -> ignored by browser */
  [data-counter] li::before{content:"0" counter(itemcounter,decimal-leading-zero) " ";position:absolute;left:-4em;font-size:.6em;font-family:firacode;font-weight:lighter}
  [data-counter] li:nth-child(2n)::before{left:calc(100% + 4em)}
}
@keyframes marquee{0%{transform:translateX(0)}100%{transform:translateX(-100%)}}
.scroller-item{animation-name:marquee;animation-duration:30s;animation-iteration-count:infinite}
[data-a=char] div,[data-a=line] div,[data-a=word] div{overflow:hidden;box-sizing:border-box}
[data-a=char] div div,[data-a=line] div div,[data-a=word] div div{box-sizing:border-box}
@media (max-width:991px){[data-hide=tablet]{display:none}}
@media (max-width:767px){[data-hide=mobile]{display:none}}
input+.line{transform:scaleX(.5)}
```
Head CSS: `[data-start="hidden"]{visibility:hidden}` `[data-viz="hidden"]{visibility:hidden}` `[data-pointer="none"]{pointer-events:none}`.

**Counter list offsets as measured (1440):** only the **even** `li` get `transform: translateX(10%)`, because the other two rules are invalid CSS. The `::before` counters are Firacode at 8.4px (0.6em of 14px), weight `lighter` (computes to 100, but only 400 is loaded so it renders as Regular), `top:0`. Odd items use `left:-33.6px` (-4em). Even items use `left: calc(100% + 33.6px)`, so the counter sits to the right of the word. Content renders as "001 ", "002 ", ... (the literal "0" plus a leading-zero counter). Below 991px there is no offset and no counter.

### Breakpoints (Webflow)
`max-width:991px` (tablet), `max-width:767px` (mobile landscape), `max-width:479px` (mobile portrait). The global embed uses `min-width:991px` for the counters.

### Stacking (important for the cube effect)
- `.canvas` (wrapper `div.canvas.w-embed` > `div.canvas[data-gl=c]` > `<canvas>`) is `position:fixed; inset:0; width:100vw; height:100vh; z-index:-10`. It is placed **after** `.pw` in the body.
- `.pw` and `.w` are `position:static; z-index:auto` (no stacking context). This is required.
- `.z` = `position:relative; z-index:-11`, so these words render **behind** the cube. `.z.minus` = `z-index:-21`. At ≤991px `.z` becomes `position:static; z-index:0`.
- `.z` is used on: the hero word "LIMITS"; list items MANIPULATIONS, COMPILERS and PERFORMANCE; "THE" in "FIND THE MISSING PIECE"; footer "CODE" (`.z.minus`); footer "FLOW".

### Layout primitives
| class | rule |
|---|---|
| `.w` | `min-height:100vh; margin:0 auto` (main wrapper) |
| `.s` | `flex-direction:column; min-height:50vh; margin:0 auto; padding:10vh 3vw 5vh` (1440x900: `90px 43.2px 45px`). ≤767: `padding-top:5vh` |
| `.s.hero` | `display:flex; justify-content:center; min-height:90vh; padding-top:5vh; padding-bottom:1vh` |
| `.s.flex-vb` | `display:flex; justify-content:flex-end; padding-top:20vh` |
| `.s.footer` | `min-height:auto; padding-top:15vh; padding-bottom:1vh`. ≤479: `padding-top:5vh` |
| `.c` | `flex:none; width:80%; margin:2em auto` (2em = 28px). ≤991: `width:90%` |
| `.c.heading-w` | `width:100%; text-align:center` |
| `.c.flex-vc` | `display:flex; flex-direction:column; align-items:center` |
| `.c.flex-hb` | `display:flex; justify-content:space-between; gap:2em (28px)`. ≤991: `flex-direction:column; align-items:flex-start` |
| `.c.py-lg` | `margin-top:10em; margin-bottom:10em` (140px) |
| `.c.py-0` | `margin-top:0; margin-bottom:0` |
| `.c.fs` | `width:100%` |
| `.tb-w` | `flex:none; width:45%`. ≤991: 70%. ≤767: `width:90%; margin-bottom:3em` |
| `.tb-w._1-2` | width 50%. ≤991: `width:70%; height:auto; margin-bottom:1rem`. ≤767: 100% |
| `._1-2` | `display:flex; flex-direction:column; align-items:flex-start; width:50%; height:26vw; position:relative` |
| `.mt-xl` | **not defined in CSS** (no-op) |

Section y-positions (1440x900, doc height 7047px): hero 0 (h810), #content 810 (h2249), #cta(1) 3059 (h1177), #cta(2) 4236 (h1465), #signup 5701 (h655), footer 6356 (h691).
At 375x812 (doc height 6884): hero 0 (h731), #content 731 (h1184), #cta(1) 1914 (h1990), #cta(2) 3905 (h1634), #signup 5539 (h968), footer 6507 (h377).

---

## 1. Fonts

`@font-face`, all with `font-display:block`. Local copies are in `/Users/riyaghosh/V3/codeflow/public/assets/fonts/`.

| family (CSS name) | weight/style | remote URL | local |
|---|---|---|---|
| `Helvetica Neue` | 400 normal | https://cdn.prod.website-files.com/651ef6c5494f36508ea49212/65550d7daafc53997a52c682_HelveticaNeue.woff2 | `/assets/fonts/HelveticaNeue.woff2` |
| `Helvetica Neue` | 700 normal | https://cdn.prod.website-files.com/651ef6c5494f36508ea49212/65562f1e837e6badca45958b_HelveticaNeue-Bold.woff2 | `/assets/fonts/HelveticaNeue-Bold.woff2` |
| `Helvetica Neue Condensed` | 700 normal | https://cdn.prod.website-files.com/651ef6c5494f36508ea49212/65550d7da960578574d88b25_HelveticaNeueBoldCondensed.woff2 | `/assets/fonts/HelveticaNeueBoldCondensed.woff2` |
| `Firacode` | 400 normal | https://cdn.prod.website-files.com/651ef6c5494f36508ea49212/651ef6fdacd1cf1eb66a18c1_FiraCode-Regular.woff2 | `/assets/fonts/FiraCode-Regular.woff2` |
| `Firacode` | 700 normal | https://cdn.prod.website-files.com/651ef6c5494f36508ea49212/651ef6fd9afcaade5204536e_FiraCode-Bold.woff2 | `/assets/fonts/FiraCode-Bold.woff2` |

The CSS also declares `Neuemontreal` 400/400i/700/700i (`651ef6fd...NeueMontreal-*.woff2`), but it is **never used or loaded**, so skip it.
Fallback stacks: `"Helvetica Neue", Arial, sans-serif`; `"Helvetica Neue Condensed", Arial, sans-serif`; `Firacode, Arial, sans-serif`.
Note: `h1` declares `font-weight:400`, but `.hero-he` is 700, so it renders 700. The condensed family only has 700.

### Text roles (computed; 1440 / 375)
| role | selector | family | size / line-height | ls | weight | transform |
|---|---|---|---|---|---|---|
| body | body | Helvetica Neue | 14 / 15.4 | normal | 400 | none |
| nav paragraph | `.nav-par` | Helvetica Neue | 12.6 (.9em) / 13.86; `text-indent:2em`; `<strong>` = 700 | normal | 400 | none |
| mono label | `.font-fira` | Firacode | 0.8rem = 12.8 / 12.8 (1em) | 0.1em (1.28px) | 400 | uppercase |
| mono xs | `.font-fira.xs` | Firacode | 10 / 10 | 1px | 400 | uppercase |
| mono at ≤479 | `.font-fira` | Firacode | **1em**, i.e. inherits: 14px in body (17px inside `.hero-tx-w`) | 0.1em | | |
| mono bold | `.font-fira.bold-text` | Firacode | 12.8 | 1.28px | 700 (`.bold-text` alone is 400; the `.font-fira.bold-text` combo is 700) | uppercase |
| hero heading | `.hero-he` (h1 & h2) | HN Condensed | 9vw = 129.6 / 0.8em = 103.68; `white-space:nowrap`, centered. ≤991: 11vw. ≤767: 11vw + `white-space:normal`. ≤479: **3.9rem = 62.4 / 49.92**, `white-space:break-spaces` | normal | 700 | h2 uppercase |
| list heading | `.li-he` (h3) | HN Condensed | 7vw = 100.8 / 0.9em = 90.72. ≤767: 9vw. ≤479: 12vw (45 / 40.5 @375) | normal | 700 | |
| block heading | `.tb-he` | HN Condensed | 5vw = 72 / 57.6 (0.8em); `.tb-he.py-xs` margin 1rem 0. ≤991: py-xs 9vw. ≤767: 11vw (py-xs 12vw). ≤479: 13vw (py-xs **14vw** = 52.5 / 42 @375) | normal | 700 | h2 uppercase |
| block text | `.tb-text` | Helvetica Neue | 1rem = 16 / 1.2em = 19.2; `width:80%; max-width:50ch`; `margin-bottom:10px`; `.ul` = underline; `<strong>` 700 | normal | 400 | none |
| hero sub | `.hero-tx-w` | wrapper 17px, centered; children `.font-fira` | | | | |
| CTA button | `.button-c` | HN Condensed | 1.2rem = 19.2 (`.cta-tx` sets 1rem = 16 text); line-height 15.4 | normal | 700 | none |
| nav button | `.button-c.sm` | HN Condensed | 1rem = 16 | | 700 | |
| timeline header | `.tl-header-he` | Helvetica Neue | 0.8rem = 12.8 / 15.4; `padding:.4rem 0` | | 700 | |
| form label | `.lead-label` | HN Condensed | 16 / 1.4em = 22.4; `display:block; margin-bottom:5px` (Webflow label) | | 700 | |
| input | `.lead-field` | Firacode | 14 / 20 | | 400 | none |
| hint | `.lead-hint` | Firacode | 0.7rem = 11.2 | | 400 | uppercase |
| join list | `.join-li` | Firacode | 0.8rem = 12.8 / 15.4 (≤479: .6rem = 9.6) | normal | 400 | uppercase |
| success heading | `.succ-he` | HN Condensed (from `.lead-succ-w`) | 3rem / .9em; `margin:1rem 0` | | | |
| error | `.lead-err` | Firacode | .8rem | | | uppercase |
| footer big | `.ft-btxt` | HN Condensed | 18vw = 259.2 / 0.8em = 207.36. ≤767: 15vw. ≤479: 20vw (75 / 60 @375) | | 700 | |
| footer nav | `.ft-li` | Helvetica Neue | 0.7rem = 11.2 / 15.4 | | 700 | uppercase |

---

## 2. Section-by-section structure (exact markup order and text)

Skeleton:
```
body
  div.style----global.w-embed        (global <style>, see §0)
  div.pw[data-start=hidden]          (whole page; GSAP fades it in)
    nav.nav
    div.w
      header#intro.s.hero
      section#content.s
      section#cta.s                  (1st)
      section#cta.s                  (2nd; duplicate id on the original)
      section#signup.s.flex-vb
      footer.s.footer
  div.canvas.w-embed > div.canvas[data-gl=c][position=fixed][width=100vw][height=100vh] > canvas
```

### 2.1 Nav `nav.nav`
CSS: `position:fixed; inset:0 0 auto; z-index:20; display:flex; justify-content:space-around; align-items:center; margin:1em auto (14px); padding:0 2vw (28.8px @1440)`. Transparent at desktop.
Measured at 1440: nav box y14 h75.
1. `div.nav-par` (width 40%, 553px @1440; x29 y30): "A practical **Javascript** course to **level up** no-code developers**.** From the basics to doing anything you can imagine, through **animations,** custom libraries, dev environment, a proper setup and all that fun stuffs." ≤991: width 50%. ≤767: `display:none`.
2. `div.nav-cent` (width 20%, centered flex) > `div.font-fira.xs[data-a=scramble]` "(ver 0.2)". ≤991: hidden.
3. `div.nav-cta-w` (width 40%, flex, `justify-content:flex-end; align-items:center`):
   - `a.link-c.w-inline-block[data-hide=mobile][arial-label=discord][href=#]` > `div.icon.w-embed` (Discord SVG, `width:1rem; margin:1rem`). **`.link-c{display:none}`, so it is never visible.**
   - `a.button-c.sm.w-inline-block[data-a=cta][href=#signup]` > `div.cta-tx` "Join Waitlist" + `div.btn-ic.w-embed` (arrow SVG). Box 176x37 @1440 (x1179 y33); margin 19.2px 16px; padding 9.6px 19.2px; gap 48px (3em); radius 48px.
   - `div.logo.xs.w-embed` (logo SVG, `width:2.5rem` = 40px, rendered 40x38).
- ≤991: `.nav-cta-w{flex:1}`.
- ≤767: `.nav{background:#0c0c0c; margin-top:0}`; `.nav-cta-w{flex-direction:row-reverse; justify-content:space-between}`, so the logo is on the left and the button on the right.
- ≤479: `.nav{justify-content:space-between; width:100%; margin-left:0; padding:0}`; `.nav-cta-w{flex:none; width:100%; padding:0 1.4rem (22.4px)}`; `.button-c.sm{margin-left:0; margin-right:0}`. Measured at 375: nav at y0, height 75, bg #0c0c0c; logo x22 y19 40x38; button x208 y19 144x37.

### 2.2 Hero `header#intro.s.hero`
Box at 1440: h810, padding `45px 43.2px 9px`, flex column centered.
```
div.c
  div.c.heading-w
    div.font-fira.xs[data-a=scramble]  "A 8+ HOURS VIDEO COURSE"        (y163 @1440)
    h1.hero-he[data-a=word]  "WEBFLOW BUILDS<br>WITH NO WEBFLOW<br><span.z></span><span.z>LIMITS</span><span.z></span>"
                              (y199 h324 @1440; margin-top .2em = 25.92px; 3 lines)
  div.c.flex-vc                                                         (y551 @1440)
    div.hero-tx-w
      div.font-fira[data-a=scramble][data-delay=1]            "JAVASCRIPT COURSE FOR"
      div.font-fira.bold-text[data-a=scramble][data-delay=1]  "WEBFLOW DEVELOPERS"
    a.button-c.w-inline-block[data-a=cta][href=#signup]  > div.cta-tx "Reserve your Spot" + div.btn-ic(arrow)
                              (257x40 @1440 at x592 y599; margin 23.04px 16px; padding 11.52px 23.04px; radius 57.6px; gap 57.6px)
    div.font-fira.xs.text-center[data-a=alpha]  "*LOCK PRICE AT <strong>200$,</strong><br><strong>GUARANTEES</strong> ENTRY"
```
`data-delay` is **not read by app.js** (no effect).
At 375: hero h731; h1 62.4px over 4 lines (h262); button 192x40; `.button-c` gap is 2em at ≤767 and 1rem at ≤479.

### 2.3 Course content `section#content.s`
```
div.c.py-0 > h2.font-fira.center[data-a=scramble]  "COURSE CONTENT"   (Firacode 12.8, weight 700 from h2, centered)
ul.list.w-list-unstyled[data-counter][role=list]   (flex column, align-items:center, margin-top 2em; Webflow ul margin-top 2em)
  li > h3.li-he[data-a=word]  ×20, in order:
    01 API AND DATA
    02 DOM
    03 MANIPULATIONS      (li.z)
    04 GSAP
    05 ANIMATIONS
    06 SMOOTH SCROLL
    07 PAGE TRANSITIONS
    08 ADVANCED JS
    09 RIVE & LOTTIE
    10 LIBRARIES
    11 DEV SETUP
    12 COMPILERS          (li.z)
    13 WORKFLOWS
    14 THE BOILERPLATE™
    15 OPTIMISATION
    16 BACKEND
    17 WEBFLOW API
    18 CI/CD
    19 VIBE CODING
    20 PERFORMANCE        (li.z)
div.c.flex-vc > div.font-fira.center.max-w[data-a=alpha]
   "<strong>8+ hours</strong> of In depth <strong>video MATERIAL,</strong> beginners to advanced, and advanced to masters with <strong>custom code in webflow</strong>"
   (width 60ch = 461px @1440; ≤479 max-width 90%)
```
Each li is 99px tall at 1440 (one line of 100.8 / 90.72 plus the split wrappers). Measured at 1440 (x, width): API AND DATA 439/562; DOM 645/189 (+18.85px tx); MANIPULATIONS 391/659; GSAP 633/217 (+21.67); … ; THE BOILERPLATE™ 395/813 (+81.26). The list spans y941–2920. At 375: li height 45, no transforms.

### 2.4 First `section#cta.s`
Two `div.c.flex-hb.py-lg` rows. Each row has two `div.tb-w` columns (45% each = 487px @1440, `space-between`). The **right column carries class `mt-xl`, which does nothing**. Each block follows this pattern:
```
div.tb-w
  div.font-fira[data-a=scramble]   <label>
  h3.tb-he.py-xs[data-a=word]       <line1><br><line2>
  p.tb-text[data-a=alpha]           <rich text>
  div.font-fira.mt-md[data-a=alpha] <bullets>     (optional; margin-top 3rem = 48px)
```
Row 1:
- Left: label "CONTENT"; heading "10+ HOURS / OF VIDEO"; text "Split into **skill-based modules,** you'll learn different <u class=ul>workflows</u> that are effective and applicable, even if you haven't completed the entire course."; bullets "• 4 sections<br>‍<br>• 2 FULL LIVE BUILDS<br><br>• COMMUNITY SUPPORT<br><br>• LEARN TOGETHER<br><br>• LIVE SESSION MONTHLY" (the spaces are `&nbsp;`; there is a zero-width joiner on the 2nd line).
- Right (`.mt-xl`): "SKILLS"; "BEGINNER TO / ADVANCED"; text "**And Advanced to master****.** Tailored to accommodate learners at any stage of their journey, ensuring <span.ul>you can start from your current skill</span> level and gain practical, actionable knowledge at every step."; mono "&gt; JOIN AT ANY POINT<br>‍<br>&lt; END AT ANY PoNT" (sic: "PoNT").

Row 2:
- Left: "FEATURES (1/2)"; "DISCORD / COMMUNITY"; "**Learn with others** following the same path, get help and share progress. Plus challenges, and <span.ul>a network of other freelancers</span> with the same skillset as you."
- Right (`.mt-xl`): "FEATURES (2/2)"; "REAL LIFE / LIVE BUILDS"; "**Featuring a full real-life website build:** dive into building and deconstructing fully functional websites with the newly acquired skills."

Measured at 1440: row 1 at y3289 h387, margins 140px; tb-he 72/57.6 h120 (2 lines); tb-text width 390 (80%).

### 2.5 Second `section#cta.s`
```
div.c.py-lg
  div.c.heading-w
    div.font-fira[data-a=scramble]  "Solve Webflow with code"   (uppercased by CSS)
    h2.hero-he[data-a=word]  "FIND <span.z></span><span.z>THE</span><br>MISSING PIECE"
  div.c.flex-vc
    a.button-c[data-a=cta][href=#signup] "Reserve your Spot" + arrow
    div.font-fira.text-center[data-a=alpha]  "*LOCK PRICE AT <strong>200$,</strong><br><strong>GUARANTEES</strong> ENTRY"  (12.8px here, not xs)
div.c.flex-hb.py-lg
  div.tb-w: "TIMELINE" / "LIVE SEPT / 2025" /
      p "**Recording is starting for the first module. **The course goes live progressively, with additional sections after initial launch."
      mono "• SECTION 1 EST Q1 2025<br><br>• COMMUNITY LIVE<br><br>• First live session"
  div.tb-w: "PRICE" / "LOCK PRICE / AT 200$*" /
      p "**By joining the waitlist now.** You'll receive a discount before the course goes live, allowing you to signup early, <span.ul>guaranteeing entry</span> to the first cohort, and at a special discount."
      mono "* THEN 250? Maybe 300? Maybe more? not sure"
div.c.fs[data-hide=mobile]    (timeline table, full width 1354 @1440, y5477)
  div.timeline-row.header   (flex, position:relative, text-align:center, padding-bottom 1rem)
    div.table-first > div.font-fira.xs[data-a=scramble] "PRICE"     (width 10%, padding-left 1em, flex start/center)
    div._1-4.py-sm[data-a=alpha] > div.tl-header-he "WAITLIST AND EARLY ACCESS" + div.font-fira.xs "SEPT 2024"
    div._1-4.py-sm[data-a=alpha] > div.tl-header-he "FIRST MODULE LAUNCH"     + div.font-fira.xs "SEPT 2025"
    div._1-4.py-sm[data-a=alpha] > div.tl-header-he "FULL COURSE LIVE"        + div.font-fira.xs "~ +4M > ∞"
    div.line.abs[data-a=sx]
  ul.timeline-li.w-list-unstyled  (margin-top 0, font-size .8rem)
    li.timeline-row
      div.table-first > div.font-fira.bold-text > strong[data-a=scramble] "200$"
      div._1-4.py-sm.flex-c > div.dot[data-a=s]
      div._1-4.py-sm  (empty)  div._1-4.py-sm (empty)
      div.line.abs[data-a=sx]
    li.timeline-row
      div.table-first > div.font-fira[data-a=scramble] "300+ $"
      div._1-4.py-sm.flex-c (empty)
      div.line.abs[data-a=sx]
      div._1-4.py-sm.flex-c > div.dot[data-a=s]
```
`._1-4` is width 30% (406px), `padding:1em 0` (14px). `.dot` is 0.7em circle (9px at 12.8px) `#f5d0e6`. `.line.abs` is `position:absolute; inset:auto 0 0; height:1px; width:100%; bg #f5d0e6`. Rows are 35px tall and the header 82px. The table is hidden at ≤767.

### 2.6 Signup `section#signup.s.flex-vb`
```
div.c.flex-hb
  div.tb-w._1-2      (541px @1440, height 26vw = 374px)
    h2.tb-he.py-xs[data-a=word]  "JOIN THE<br>WAITLIST"
    p.tb-text[data-a=alpha]  "<strong>Lock launch price at 200$ and guarantee entry to first cohort.</strong> I'll only send few updates on course completion, or probably just the launch one."
    ul.join-li.w-list-unstyled   (flex column, gap .5rem, margin-top 3em = 38.4px)
      li > div[data-a=word] "Early access at 50% discount (then 250$+)"
      li > div[data-a=word] "Early access to Discord inner circle"
      li > div[data-a=word] "Guaranteed entry to 1st cohort"
  div.tb-w._1-2.vc
    div.form-block.w-form[data-dom=form]
      form#email-form.lead-c  method=post action="https://ooo.us21.list-manage.com/subscribe/post?u=194504e1038ca7c499546ef86&amp;id=f8575c61aa&amp;f_id=0021e1e9f0"
        div.lead-b-w (flex column)
          div.lead-block[data-a=alpha]  label.lead-label[for=name] "First Name *"
              div.field-w > input.lead-field.w-input#name[name=name][type=text][placeholder="Your Name"][maxlength=256][required]
                          + div.line.abs[data-a=sx][data-origin="left center"]
          div.lead-block[data-a=alpha]  label.lead-label[for=email] "Email Address *"
              div.field-w > input.lead-field.w-input#email[name=email][type=email][placeholder="example@email.com"][data-validate=email][required]
                          + div.line.abs[data-a=sx]
          div.lead-block > div.lead-hint[data-viz=hidden][data-form=hint] "..."   (always hidden)
        input.button-c.lock.w-button[type=submit][value="Get In"][data-wait="Almost there!"][data-form=submit]
      div.lead-succ-w.w-form-done[data-listen=success]   (display:none until success)
        div.div-block-5 > div.succ-he[data-a=scramble] "YOU ARE IN.<br>" + div.font-fira[data-a=scramble] " Catch up soon!"
      div.lead-err.w-form-fail > div "Something went wrong. Try again?"
```
Input: 504x38 @1440 (max-width 60ch), padding 8px 12px, margin-bottom 10px. Border: `1px solid transparent` on top/sides with **no bottom border** (`border-style: solid solid none`); the visible underline is the `.line` div. Background transparent, text `#f5d0e6`, placeholder `#999` (Webflow default).
Submit button: 92x40; **text color #fff** (from `.w-button`, overriding the pink); border 1px `#f5d0e6`; radius 57.6px; `opacity:.3; cursor:not-allowed` while `.lock`.
`.w-form-done` defaults (from Webflow) are overridden by `.lead-succ-w{background:#ddd0}`; Webflow still gives `text-align:center; padding:20px`. `.w-form-fail` keeps `margin-top:10px; padding:10px`, with background made transparent by `.lead-err`.

### 2.7 Footer `footer.s.footer`
```
div.c.footer-c    (width 100%, flex column, gap 1rem, margin-bottom 2rem)
  div.ft-row
    div.ft-block.align-r > a.ft-lk[href=https://federic.ooo/s/twitter][target=_blank] > div.font-fira.xs.ul[data-a=scramble] "TWEET @ ME"
  div.ft-row
    div.ft-btxt[data-a=char][data-y=-150%] "THE"
    div.ft-block[data-hide=tablet]
      div.font-fira.xs[data-a=scramble] "WEBSITE"
      ul.ft-li.w-list-unstyled[data-a=alpha]  (margin-top 2em)
        li.ft-li-it > a.ft-li-lk[href=#intro].w--current > div "INTRO"
        li > a[href=#content] "CONTENT" ; a[href=#cta] "CTA" ; a[href=#signup] "SIGN UP"
    div.z.minus > div.ft-btxt[data-a=char][data-y=-150%] "CODE"
  div.ft-row.mob-vert
    div.z > div.ft-btxt[data-a=char][data-y=-150%] "FLOW"
    div.ft-btxt.pl-sm[data-a=char][data-y=-150%] "CO"     (margin-left .3em)
    div.ft-block.flex-hb  (row, space-between)
      div[data-hide=tablet] > div.logo.xs (logo SVG)
      div.div-block-4 (flex column, space-between, align-items:flex-end)
        a[href=https://docs.google.com/document/d/1tzCCJaDVQFgwG0ai2A-VjvCNXtm4i-UmXPj6v0ZfiYQ/edit?usp=sharing][target=_blank] > div.font-fira.xs.ul "PRIVACY POLICY"
        div.font-fira.xs.tx-r[data-a=alpha] "© 2024 — 2025<br><br>MADE BY <a.ul href=https://federic.ooo/ target=_blank>HTTPS://FEDERIC.OOO<br></a>"
        <link rel=prefetch href=https://federic.ooo/>
```
`.ft-block` = `flex:1; flex-direction:column; padding:1rem`. `.ft-row` = flex. `.ft-li-lk` padding .3rem (right/top/bottom), transition opacity .2s.
At 1440: THE x43 w393; links block x452; CODE sits right of the links; "CO" at x702.
At ≤479: `.ft-row.mob-vert{flex-flow:wrap}`; `.ft-block.flex-hb{justify-content:flex-start}`; `.div-block-4{align-items:flex-start; width:100%}`; `.tx-r{text-align:left; margin-top:1rem}`. The tablet-hidden blocks disappear.

### Unused CSS (no DOM on live page)
`.scroller-wrap` / `.scroller-item` / `.scroller-text` (the marquee), `.fx-w`, `.btn-bg` (`transform:scale(0)`, `transition: transform .8s cubic-bezier(.19,1,.22,1)`), `.webgl-btn`, `.st`. **The live page has no marquee.** If you want it anyway, the CSS is in §0 (30s linear-ish infinite translateX(0→-100%)), fixed bottom, 12px, bg `--black`, hidden ≤991.

---

## 3. Colors, borders, radii
- Text, borders, lines and dots: `#f5d0e6`. Page bg: `#0c0c0c`. Button hover fill: `#f5d0e6` with text `#0c0c0c`.
- `.button-c` bg `rgba(56,152,236,0)` (transparent); border `1px solid #f5d0e6`; `border-radius:3em` (48px at 16px, 57.6px at 19.2px); `padding:.6em 1.2em`; `margin:1.2em 1rem`; `display:flex; align-items:center; gap:3em`; `overflow:hidden; position:relative`.
- `.btn-ic` is `width:.8em; font-size:.8em; line-height:1em` (rendered 10x13 in the nav).
- Inputs: underline (`.line`) `#f5d0e6` 1px; focus sets `border-bottom-color: #707070`, but the bottom border style is none, so it has no visible effect.
- Lock button: `opacity:.3`; on hover it stays `color:#f5d0e6; background: transparent`. Note that the input's computed color is #fff, but the hover rule forces pink.

---

## 4. Assets (all network requests after a full scroll)

| asset | remote | local | notes |
|---|---|---|---|
| Rubik cube model | https://uploads-ssl.webflow.com/651ef6c5494f36508ea49212/655637ab023b9146c71771e3_cube8.glb.txt | `/Users/riyaghosh/V3/codeflow/public/assets/webgl/cube8.glb` | glTF 2 binary, 648,832 B. Scene[0] = `Empty.002` with 3 child meshes (`Cube.051_Cube.043`, `Cube.052_Cube.044`, `Cube.056_Cube.048`), the 3 horizontal layers. Scene[1] `Cube.011` is unused. ~31.6k VEC3 verts total, no materials. Fetched with `fetch` (served as .txt). |
| matcap 1 (`u_mtc1`) | …/655637d3fc6e06242f0d7c95_mtc16.webp | `/public/assets/webgl/mtc16.webp` | 1080x1080 webp, 6.2 KB |
| matcap 2 (`u_mtc2`) | …/655637d30b73cf212f61b644_mtc3.webp | `/public/assets/webgl/mtc3.webp` | 1080x1080 webp, 5.3 KB |
| sticker color map (`u_col_map`) | …/6558b79dde12de54c5a514a9_col_map.webp | `/public/assets/webgl/col_map.webp` | 540x540 webp, 1.1 KB, `flipY=false` |
| favicon | https://cdn.prod.website-files.com/651ef6c5494f36508ea49212/65572c54e74627436d843ae9_favico.png | `/public/assets/images/favicon.png` | 32x32 png |
| apple-touch-icon | …/65572c59061e621b183714f1_webclip.png | `/public/assets/images/webclip.png` | 256x256 png |
| og/twitter image | …/655c967e409bdabd2e2f348a_og_img.jpg | `/public/assets/images/og_img.jpg` | 1200x630 jpg |
| fonts | see §1 | `/public/assets/fonts/*.woff2` | |
| Discord icon | inline SVG | `/public/assets/svg/discord.svg` | viewBox 0 0 17 14, `fill=currentColor` (hidden on site) |
| arrow icon | inline SVG | `/public/assets/svg/arrow.svg` | viewBox 0 0 14 14, `fill=currentColor`, ×3 |
| logo "THE CODE FLOW. CO" | inline SVG | `/public/assets/svg/logo.svg` | viewBox 0 0 53 50, path fill hardcoded `#F5D0E6`, ×2 (nav + footer) |

The uploads-ssl assets send `Access-Control-Allow-Origin: *`, so either remote or local works. Third-party scripts: Umami analytics `https://cloud.umami.is/script.js` with `data-website-id="13ed4638-a8ba-4623-9987-1f6112450739"`, which calls `umami.track("Signup Success")`. Webflow runtime (jQuery 3.5.1 + `codeflowco.schunk…js` + `codeflowco.a0aa6ca1…js`) is needed only for form handling. There are no videos, no other images and no CSS background images.

Meta: title `Join Waitlist — thecodeflow.co`. Description: "Level up your Webflow game by learning Javascript. Tailored to no-code and Webflow developers specifically, with 10+ hours of content, from zero experience to having no limits on what you can build." `og:type website`, `twitter:card summary_large_image`.

---

## 5. Motion (values taken from app.js and checked live)

### 5.1 Boot / intro
There is no separate loader screen. In order:
1. `.pw[data-start=hidden]` starts `visibility:hidden`. `gsap.to(.pw, {autoAlpha:1, duration:1, delay:0.2})` (default ease `power1.out`). Live samples: opacity .04 @0ms → .54 @300 → .92 @700 → 1 @1010ms.
2. All `[data-a]` controllers are created at boot. Each one immediately `set`s its "out" state, then starts IntersectionObservers. Anything in view (the hero) animates in at once, alongside the fade.
3. WebGL: the cube drops in from above. `a.initial: 3 → 0`, `ease:"back.out"`, `duration:1.2`, starting after the 3 textures and the GLB have loaded (`Promise.all`). `position.y` includes `+initial`, so it starts 3 world units high and overshoots slightly below before settling.

### 5.2 Observer base (`I8`)
Each element gets two IntersectionObservers:
- **in**: `threshold: 0.5` for all text/alpha/scramble/scale classes, `rootMargin:"0px"`. Fires `isIn` → animate in.
- **out**: `threshold: 0`. When the element fully leaves the viewport it calls `setOut()`, an instant reset. **So every animation replays each time the element re-enters** (`once` is false everywhere).

### 5.3 `data-a="word"` / `"char"` / `"line"` (class `k7`)
- Split: GSAP SplitText `type:"lines"` first, and each line is wrapped in an extra `<div>` (`overflow:hidden` via the global CSS). Then each line is split into `words` (for `word`) or `chars` (for `char`). Result per line: `div > div[aria-hidden](line, display:block, text-align inherited) > div(word, position:relative; display:inline-block)`. `aria-label` is set on the element.
- Out state: `y: el.dataset.y || "150%"` (i.e. `translate(0,150%)`). The footer uses `data-y="-150%"` so its chars drop in from above.
- In: `gsap.to(targets, {y:"0%", duration:1.2, ease:"expo.out", delay: isMobileUA ? 0 : 0.1, stagger:{each:0.05, from:"start"}})`.
- Live sample of the hero first word: translateY 115px @0 → 36.6 @200 → 10.6 @400 → 2.4 @600 → 0 @1200ms.
- Trigger: 50% of the **whole element** (h1/h3/div) visible.
- On resize only `data-a="lines"` re-splits (a typo, so effectively never).

### 5.4 `data-a="alpha"` (class `Q8`)
Out `autoAlpha:0`. In `gsap.to(el, {autoAlpha:1, duration:1.2, ease:"expo.out", delay:0.1})` (stagger is irrelevant for a single element). Threshold 0.5.

### 5.5 `data-a="scramble"` (class `S7` extends Q8)
On in, two tweens run at once:
1. autoAlpha 0→1, 1.2s expo.out, delay 0.1.
2. `gsap.to(el, {duration: 0.6 + Math.random()*0.3, delay:0, scrambleText:{chars:"▖▗ ▘ ▙ ▚ ▛ ▜ ▝ ▞ ▟", revealDelay:0.3, text: originalTextContent, speed:1, delimiter:"", rightToLeft:false}})` with the default ease (`power1.out`).
   - The char set is exactly `"▖▗ ▘ ▙ ▚ ▛ ▜ ▝ ▞ ▟"`: Unicode quadrant blocks U+2596–U+259F **including the spaces**, so the scrambled text contains gaps.
   - `speed:1` means the random chars are re-rolled every 0.05s.
   - For the first 0.3s the whole string is scrambled. Real characters are then revealed left to right over the rest of the duration, with the eased progress mapped onto (t-0.3)/(dur-0.3).
   - The text uses `textContent`, so inner markup (`<strong>`, `<br>`) is **flattened**. For example "YOU ARE IN.<br>" loses its `<br>`.
   - Live: "A 8+ HOURS VIDEO COURSE" was fully resolved at about 600ms.
Out: instant `autoAlpha:0`.

### 5.6 `data-a="s" | "sx" | "sy"` (class `z7`)
- `sx`: out `scaleX:0, scaleY:1`, in `scaleX:1`.
- `s`: out `scale 0,0`, in `1,1`.
- `sy`: scaleY only.
- In: `duration: 1.2 + Math.random()*0.2`, `ease:"expo.out"`, `delay:0.1`, `transformOrigin: el.dataset.origin || "right center"`.
- Used by the timeline lines (grow from the right), the timeline dots, and the form underlines (name field `data-origin="left center"`, email field right).

### 5.7 `data-a="cta"` buttons
- CSS hover: `background-color: #f5d0e6` (0.4s), `color:#0c0c0c` (0.2s), `transition: color .2s, background-color .4s` (default ease). `cursor:pointer`.
- JS (only when the UA is not mobile): `mouseenter` → `cube.mouseCta(1)`; `mouseleave` → `mouseCta(0)`. This tweens the shader `hover` value with `{hover: v, ease:"expo.out", duration:1.2}`. On enter it also sets `rotateAxis=false`. When the leave tween completes it restarts the scramble interval.
- Effect: the cube's lower half darkens to 10% and the colored sticker map faintly shows (+10%); the cube scale grows by 0.02. Confirmed live: the uniform reached 0.993 about 0.6s after hover.

### 5.8 Smooth scroll: Lenis 1.3.4 (class `w7 extends Lenis`)
```js
new Lenis({ duration:1.2, smoothWheel:true, easing:t=>Math.min(1,1.001-Math.pow(2,-10*t)), orientation:"vertical", smoothTouch:false, touchMultiplier:2 })
```
- Other options at their defaults: lerp 0.1 (ignored because duration+easing take priority), `syncTouch:false` (native touch), `wheelMultiplier:1`, `anchors:false`, `autoRaf:false`.
- RAF is driven manually: `lenis.raf(time)` inside the app's rAF loop.
- On `scroll` it stores `y`, `limit`, `velocity` and `progress`, and every frame `lp = lerp(lp, progress, 0.1)`.
- `window.sscroll = lenis`.
- `#signup` anchor links are not handled by Lenis (`anchors:false`). The Webflow runtime does its own smooth anchor scroll.

### 5.9 WebGL (OGL): the Rubik's cube
The whole effect is one draw of a 3-layer cube mesh with a custom matcap shader, on a fixed full-screen transparent canvas behind the content.

- **Renderer**: `new Renderer({dpr:2, antialias:true, alpha:true})`, clearColor (0,0,0,0). DPR is fixed at 2: the canvas is 2880x1800 at 1440x900 and 750x1624 at 375. Canvas is appended to `[data-gl=c]`. Resized via `ResizeObserver` on the wrapper.
- **Camera**: perspective, fov 25, near .1, far 100, position (0,0,5), aspect = wrapper w/h.
- **Scene**: Transform `g` with `g.position.y = -0.5`, containing the Cube (`QZ`) Transform. Inside that, `ctrl` Transform, inside that the GLB scene[0] node.
- Mesh scale: `a.scale` (base 0.1).
- All 3 layer meshes share one Program, with `transparent:true, cullFace:null`.
- **Per-frame** (`time += 0.5` per rAF, frame-based):
  ```
  lspeed = lerp(lspeed, lenis.velocity*0.015, 0.05)
  spinner.render()                       // see below
  Z = time*0.01
  rotX = spinner.spin.y*0.1 + Z + lenis.lp*5
  rotY = spinner.spin.x*0.1 + Z + lenis.lp*5
  if !mobileUA: mx = lerp(mx, spinner.velocity.x, 0.1); my = lerp(my, -spinner.velocity.y, 0.1); position.x = mx*0.5
  posY  = lenis.progress*0.45 + lspeed + a.initial
  scale = 0.1 + lenis.progress*(mobileUA?0:0.05) + hover*0.02
  Q = |sin(position.x)| - |sin(position.y)|
  mesh.scale = scale
  position.z = -Q - a.click
  position.y = posY + my
  rotation.x = rotX + a.click*0.2
  rotation.y = rotY + a.click*0.2
  ```
  Scroll therefore moves the cube up (by 0.45 units over the full page), grows it slightly, and adds up to 5 rad of spin.
- **Spinner (mouse/touch inertia)**:
  - State: `velocity={x:.05,y:.05}`, `spin.mult=.8` (1 while the pointer is down).
  - On every `mousemove`/`touchmove` (no press needed): `velocity += (pointerDelta)*0.002*mult`.
  - Each frame: `velocity *= 0.97`, then `spin += velocity + sign(velocity)*0.005*(pointerDown?0:1)`, which gives a constant idle drift.
- **Layer "scramble"** (Rubik moves):
  - `setInterval(1680ms)` (0.8*2100). Each tick cycles through layer index 0→1→2.
  - Each tick: `gsap.to(layer.rotation, {y: y ± (Math.random()>.5 ? π/2 : π), duration:0.8, ease: random("slow.out","back.inOut")})`.
  - On complete, if `rotateAxis`: randomly do `ctrl.rotation.z += π/2` or `ctrl.rotation.x += π/2`. This instant re-orientation is invisible because the cube is symmetric, and it makes the next twist happen on another axis.
- **Click anywhere**: `gsap.to(a, {click:5, duration:1.6, ease: CustomEase("M0,0 C0.126,0.382 0.18,0.726 0.241,0.726 0.397,0.726 0.482,-0.234 0.619,-0.234 0.746,-0.234 0.768,0 1,0")})`. This is a bump curve that returns to 0: the cube pushes back up to about 3.6 units in z and swings rotation, then springs forward and back. Guarded so clicks do not overlap.
- **Solve** (keyboard `!` or form success via MutationObserver on `[data-listen=success]` style):
  - Sets `isSolved` and stops the interval.
  - Background: `gsap.to("html", {"--black": random(["#b71234","#0046ad"]), duration:1.2, delay:0.4, ease:"elastic.out"})`, then back to the original value `{duration:1.2, delay:0.4, ease:"slow.inOut"}`.
  - Shader: `u_a_solved 0→1`, duration 1.8, delay 0.4, `elastic.out`, so the stickers turn fully colored.
  - 1s later the interval restarts with `rotateAxis=false`.
- **Vertex shader** (verbatim):
```glsl
attribute vec3 position; attribute vec3 normal; attribute vec2 uv;
uniform mat4 modelViewMatrix; uniform mat4 projectionMatrix; uniform mat3 normalMatrix; uniform float u_time;
varying vec3 v_normal; varying vec3 v_view; varying vec2 v_uv;
void main(){ vec4 transformed = modelViewMatrix*vec4(position,1.0); v_view = normalize(-transformed.xyz);
  gl_Position = projectionMatrix*transformed; v_normal = normalize(normalMatrix*normal); v_uv = uv; }
```
- **Fragment shader** (verbatim logic):
```glsl
precision highp float;
varying vec3 v_normal; varying vec2 v_uv; varying vec3 v_view;
uniform sampler2D u_mtc1, u_mtc2, u_col_map; uniform float u_a_hover, u_a_solved;
vec3 COL_BG = vec3(0.058823529411764705);
void main(){
  vec3 color_map = texture2D(u_col_map, v_uv).rgb;
  vec3 x = normalize(vec3(v_view.z, 0., -v_view.x)); vec3 y = cross(v_view, x);
  vec2 fakeUv = vec2(dot(x, v_normal), dot(y, v_normal))*.495 + .5;       // matcap lookup
  vec3 mtc1 = texture2D(u_mtc1, fakeUv).rgb; vec3 mtc2 = texture2D(u_mtc2, fakeUv).rgb;
  float split = 1. - step(v_uv.y, .5);                                       // uv.y>.5 = body plastic, else stickers
  float mixing_value = 1. - fakeUv.y;
  vec3 mtc = mix(mtc1, mtc2, split); mtc = mix(mtc, mtc2, split*mixing_value);
  mtc = mix(COL_BG*.9, vec3(1.), mtc);
  vec3 col = mtc; float rev_split = 1. - split;
  col = mix(mtc, mtc*.1, rev_split*u_a_hover);
  col = mix(col, col + color_map*.1, rev_split*u_a_hover);
  col = mix(col, col + color_map, rev_split*u_a_solved);
  gl_FragColor = vec4(col, 1.0);
}
```
- Uniforms: `u_time`, `u_mtc1` = mtc16.webp, `u_mtc2` = mtc3.webp, `u_col_map` = col_map.webp, `u_a_hover` (copied from `mat.a.hover` each frame), `u_a_mouse` (unused), `u_a_solved`.
- Appearance at rest: a dark charcoal, glossy 3x3 cube centered in the lower half of the hero (about 310px wide at 1440, centered at x≈720 and y≈660), slowly tumbling, twisting a layer every 1.68s. Hero text and buttons draw over it, while `.z` words draw under it.
- **Weight**: about 650 KB GLB plus 3 tiny webp textures; one mesh group, one program, DPR 2, continuous rAF. The bundle is 208 KB unminified-ish. Light to moderate cost.
- `window.isDebug = location.pathname === "/webgl"` disables the scroll coupling (ignore it). `window.isMobile` comes from a UA regex (the classic detectmobilebrowsers), not from viewport width. Playwright at 375 with a desktop UA reported `isMobile=false`.

**Can app.js be reused as-is?** Yes. It is a self-contained IIFE that, at script execution time:
- queries `[data-start=hidden]`, `[data-a=…]`, `[data-dom=form]`, `[data-gl=c]`;
- creates `window.app` / `window.sscroll`;
- mutates the DOM through SplitText.

To reuse it in React+Vite:
- render the identical static markup first, then inject `/app.js` once after mount (do not re-run it on re-render, because it would create a duplicate canvas and Lenis);
- keep those subtrees static (React must not re-render split text);
- asset URLs are hard-coded to uploads-ssl.webflow.com (CORS `*`, which works).

The cleaner route is to reimplement the same logic with npm `gsap@3.13` (SplitText, ScrambleTextPlugin, CustomEase), `lenis@1.3.4` and `ogl`, using the values above and the local assets.

### 5.10 Other hovers
- Footer nav links `.ft-li-lk:hover{opacity:.5}` with `transition: opacity .2s`.
- Other links (`TWEET @ ME`, `PRIVACY POLICY`, `HTTPS://FEDERIC.OOO`) have no hover style (always underlined via `.ul`).
- No focus styles are defined beyond the browser default. Webflow adds `outline:0` on `a:active/hover` and `.w-input:focus{outline:0}`. The input focus border color change to #707070 is invisible (see §3).
- No custom cursor and no magnetic effects.

---

## 6. Form / signup behaviour
1. The submit button starts as `.lock` (opacity .3, not-allowed). On every `input` event, app.js `V7.isValid()` checks all inputs **except type=email** with `checkValidity()`. That means the button unlocks (removes `.lock`, `pointer-events:auto`) as soon as the Name field is non-empty. Email validity is not checked by JS, but HTML `required`/`type=email` still blocks native submit.
2. Submit is handled by the Webflow runtime. Because the action matches `list-manage.com`, Webflow converts it to a MailChimp JSONP post (`/subscribe/post-json?…&c=?`) with the field values. While waiting, the button value becomes `data-wait` "Almost there!".
3. On success Webflow hides the form and shows `.w-form-done` (`display:block`). The MutationObserver sees the style change, calls `umami.track("Signup Success")` and then `cube.animateFormSuccess()`, which triggers the solve animation (§5.9: colored stickers plus a red or blue background flash). The success texts are `data-a=scramble`, so they scramble in when visible.
4. On failure Webflow shows `.w-form-fail` "Something went wrong. Try again?" (Firacode .8rem uppercase, transparent bg, margin-top 10px, padding 10px).
5. A clone without MailChimp should use the same lock logic and fake a success state that triggers the same solve animation.

---

## 7. Not determined / caveats
- I did not run with a mobile UA, so `window.isMobile=true` behaviour was not observed. From code: no CTA hover coupling, no word delay, no mouse x/y offset, no scroll-based scale.
- I did not submit the real MailChimp form; the success and failure flows come from code reading.
- The visual look of the cube (matcap shading) cannot be read from the DOM. The description is from the shader, the textures and one screenshot.
- GSAP `"slow.out"` / `"slow.inOut"` need EasePack (SlowMo), and **EasePack is not in the bundle**. GSAP therefore falls back to its default ease (`power1.out`) for those layer twists and the background-restore tween. Use `power1.out` to match.
