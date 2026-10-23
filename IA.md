# https://www.thecodeflow.co/ (single-page Webflow waitlist site for a JavaScript course), cloned in this project

Source: https://www.thecodeflow.co/ (single-page Webflow waitlist site for a JavaScript course), cloned in this project
Status: **measured-from-live-site** · production approved: **false**
1 routes · 1 templates · 10 unique sections

> Generated from `ia.json` by `build.mjs`. Edit the JSON, not this file.

## Shape of the site

The largest 1 template (Waitlist landing page) accounts for 1 of 1 routes (100%). The remaining 0 routes span 0 templates.

| template | routes | share |
|---|---:|---:|
| Waitlist landing page | 1 | 100% |

## Page chrome

**1 routes carry chrome = `full`** — Waitlist landing page.

## Sections by reuse

How widely a section is shared determines whether it belongs in a shared
component library or stays local to its page.

| section | category | templates | routes | implementation | scope |
|---|---|---:|---:|---|---|
| `shell.nav` | SHELL | 1 | 1 | `src/components/Navbar.jsx` | Present on the single route /, fixed over every other section. |
| `hero.course-intro` | HERO | 1 | 1 | `src/components/Hero.jsx` | Opens the single route / as its first content section (#intro). |
| `content.curriculum-list` | CONTENT | 1 | 1 | `src/components/CourseContent.jsx` | Present once on the single route / (#content). |
| `features.course-blocks` | FEATURES | 1 | 1 | `src/components/Features.jsx (rows of Features.jsx > Block)` | Present once on the single route /, as the first of the two #cta sections. |
| `conversion.pitch-cta` | CONVERSION | 1 | 1 | `src/components/Pricing.jsx (first .c.py-lg block)` | Opens the second #cta section on the single route /. |
| `conversion.timeline-price-blocks` | CONVERSION | 1 | 1 | `src/components/Pricing.jsx (Features.jsx > Block)` | Present once on the single route /, inside the second #cta section. |
| `conversion.price-timeline-table` | CONVERSION | 1 | 1 | `src/components/Pricing.jsx (.c.fs table)` | Closes the second #cta section on the single route /, desktop and tablet only. |
| `conversion.waitlist-signup` | CONVERSION | 1 | 1 | `src/components/Signup.jsx + src/motion/form.js` | Present once on the single route / (#signup). |
| `shell.footer` | SHELL | 1 | 1 | `src/components/Footer.jsx` | Closes the single route /. |
| `shell.webgl-cube` | SHELL | 1 | 1 | `src/App.jsx ([data-gl=c] container) + src/motion/cube.js` | Present behind every section of the single route /, last in DOM order. |

**0 shared sections** appear in more than one template and belong in a component library.

**10 single-use sections** appear in exactly one template. Building these
as "reusable" components up front would be speculative — keep them page-local
until a second caller actually appears.

## Templates

### Waitlist landing page — `template.waitlist-landing`

1 route · `/` · chrome: **full**

| # | category | section | |
|---:|---|---|---|
| 1 | SHELL | `shell.nav` | page-local |
| 2 | HERO | `hero.course-intro` | page-local |
| 3 | CONTENT | `content.curriculum-list` | page-local |
| 4 | FEATURES | `features.course-blocks` | page-local |
| 5 | CONVERSION | `conversion.pitch-cta` | page-local |
| 6 | CONVERSION | `conversion.timeline-price-blocks` | page-local |
| 7 | CONVERSION | `conversion.price-timeline-table` | page-local |
| 8 | CONVERSION | `conversion.waitlist-signup` | page-local |
| 9 | SHELL | `shell.footer` | page-local |
| 10 | SHELL | `shell.webgl-cube` | page-local |

## Section reference

### SHELL

_Page chrome and layers that sit outside the content flow: fixed nav, footer, and the fixed full-screen WebGL backdrop._

**`shell.nav`** — Fixed top bar, transparent on desktop: a bold-keyword course blurb on the left, a scrambling '(ver 0.2)' version tag in the centre, and a small pill 'Join Waitlist' button plus the stacked 'THE CODE FLOW. CO' logo on the right. A Discord icon link exists in the markup but is always hidden. At 767px and below it gets a solid background, hides the blurb and version tag, and puts the logo left and the button right.

· Present on the single route /, fixed over every other section. · appears on 1 routes · implemented by `src/components/Navbar.jsx`

**`shell.footer`** — Footer built around giant condensed letters 'THE / CODE / FLOW CO' that drop in from above character by character, with a 'TWEET @ ME' link, a WEBSITE anchor list (INTRO, CONTENT, CTA, SIGN UP) whose links dim to 50% on hover, the small logo, a privacy-policy link and the copyright and credit line. CODE and FLOW render behind the cube; the anchor list and logo are hidden at 991px and below.

· Closes the single route /. · appears on 1 routes · implemented by `src/components/Footer.jsx`

**`shell.webgl-cube`** — Fixed full-screen transparent WebGL canvas behind all content (z-index -10) showing a dark glossy Rubik's cube. It drops in on load, tumbles and twists a layer every 1.68s, reacts to mouse movement, scroll position and clicks, darkens while a CTA button is hovered, and on '!' or a successful signup shows coloured stickers and flashes the page background. Words marked .z deliberately render behind it.

· Present behind every section of the single route /, last in DOM order. · appears on 1 routes · implemented by `src/App.jsx ([data-gl=c] container) + src/motion/cube.js`

### HERO

_The page-opening headline block with the primary call to action._

**`hero.course-intro`** — Full-viewport intro: a mono 'A 8+ HOURS VIDEO COURSE' label, a three-line giant condensed headline 'WEBFLOW BUILDS / WITH NO WEBFLOW / LIMITS' revealed word by word (the word LIMITS sits behind the cube), a two-line mono subline (JAVASCRIPT COURSE FOR / WEBFLOW DEVELOPERS), the 'Reserve your Spot' pill button, and a small '*LOCK PRICE AT 200$' note.

· Opens the single route / as its first content section (#intro). · appears on 1 routes · implemented by `src/components/Hero.jsx`

### CONTENT

_Course substance: what the course teaches._

**`content.curriculum-list`** — 'COURSE CONTENT' mono heading over a centred list of 20 very large condensed topic headings (API AND DATA through PERFORMANCE). At 991px and up every even item is shifted right by 10% and every item carries a small mono 001–020 counter, left of odd items and right of even ones; three items render behind the cube. Closes with a mono summary line about 8+ hours of video material.

· Present once on the single route / (#content). · appears on 1 routes · implemented by `src/components/CourseContent.jsx`

### FEATURES

_Course format and benefit explanations, written as labelled text blocks._

**`features.course-blocks`** — Two rows of two labelled text blocks (CONTENT, SKILLS, FEATURES (1/2), FEATURES (2/2)). Each block is a scrambling mono label, a two-line condensed heading, a short paragraph with an underlined phrase, and on some blocks a mono bullet list. Rows stack to one column at 991px and below.

· Present once on the single route /, as the first of the two #cta sections. · appears on 1 routes · implemented by `src/components/Features.jsx (rows of Features.jsx > Block)`

### CONVERSION

_Blocks whose job is getting the visitor onto the waitlist: pitch, price/timeline, and the signup form._

**`conversion.pitch-cta`** — Mid-page restatement of the offer: a mono 'SOLVE WEBFLOW WITH CODE' label, a two-line giant headline 'FIND THE / MISSING PIECE' (THE renders behind the cube), a second 'Reserve your Spot' button and the price note at normal mono size.

· Opens the second #cta section on the single route /. · appears on 1 routes · implemented by `src/components/Pricing.jsx (first .c.py-lg block)`

**`conversion.timeline-price-blocks`** — One row of two labelled text blocks with the same anatomy as features.course-blocks, but carrying launch and price facts: TIMELINE 'LIVE SEPT / 2025' with launch bullets, and PRICE 'LOCK PRICE / AT 200$*' with the price-increase caveat.

· Present once on the single route /, inside the second #cta section. · appears on 1 routes · implemented by `src/components/Pricing.jsx (Features.jsx > Block)`

**`conversion.price-timeline-table`** — Full-width table of price over time: a header row of three phases (WAITLIST AND EARLY ACCESS, FIRST MODULE LAUNCH, FULL COURSE LIVE) with dates, then rows '200$' and '300+ $' each marked by a dot under its phase. Rows are separated by 1px lines that grow from the right on scroll. Hidden at 767px and below.

· Closes the second #cta section on the single route /, desktop and tablet only. · appears on 1 routes · implemented by `src/components/Pricing.jsx (.c.fs table)`

**`conversion.waitlist-signup`** — Two columns: left has a 'JOIN THE / WAITLIST' heading, a paragraph and a mono list of 3 perks; right has a First Name + Email form with underlines that grow on scroll and a 'Get In' submit button that stays dimmed (opacity .3) until the name is filled. On success the form is replaced by a scrambling 'YOU ARE IN. Catch up soon!' and the cube solves itself.

· Present once on the single route / (#signup). · appears on 1 routes · implemented by `src/components/Signup.jsx + src/motion/form.js`
