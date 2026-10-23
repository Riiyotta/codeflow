import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { ScrambleTextPlugin } from 'gsap/ScrambleTextPlugin'
import { isMobile } from './env.js'

gsap.registerPlugin(SplitText, ScrambleTextPlugin)

const EASE = 'expo.out'
const SCRAMBLE_CHARS = '▖▗ ▘ ▙ ▚ ▛ ▜ ▝ ▞ ▟'

// Every element animates in at 50% visibility and resets the moment it fully leaves,
// so animations replay on each re-entry.
function observe(el, { animateIn, setOut }) {
  setOut()
  const inObs = new IntersectionObserver(
    (entries) => entries.forEach((e) => e.isIntersecting && animateIn()),
    { threshold: 0.5 },
  )
  const outObs = new IntersectionObserver(
    (entries) => entries.forEach((e) => !e.isIntersecting && setOut()),
    { threshold: 0 },
  )
  inObs.observe(el)
  outObs.observe(el)
  return () => {
    inObs.disconnect()
    outObs.disconnect()
  }
}

// lines -> extra overflow:hidden wrapper -> words/chars.
// Same calls as the original bundle: one default split into lines, wrap each line, then ONE
// split over the whole lines array (default aria:"auto" gives the h/line aria-labels).
// Splitting each line separately duplicated empty <span class="z"> nodes.
function splitText(el, type) {
  const outer = new SplitText(el, { type: 'lines' })
  outer.lines.forEach((line) => {
    const wrap = document.createElement('div')
    line.parentNode.insertBefore(wrap, line)
    wrap.appendChild(line)
  })
  // revert() restores the authored markup, so a re-boot (HMR / effect re-run) never splits twice
  if (type === 'line') return { targets: outer.lines, revert: () => outer.revert() }
  const key = type === 'char' ? 'chars' : 'words'
  const inner = new SplitText(outer.lines, { type: key })
  return { targets: inner[key], revert: () => (inner.revert(), outer.revert()) }
}

function textReveal(el) {
  const { targets, revert } = splitText(el, el.dataset.a)
  const from = el.dataset.y || '150%'
  let tween
  const stop = observe(el, {
    setOut: () => {
      tween?.kill()
      gsap.set(targets, { y: from })
    },
    animateIn: () => {
      tween?.kill()
      tween = gsap.to(targets, {
        y: '0%',
        duration: 1.2,
        ease: EASE,
        delay: isMobile ? 0 : 0.1,
        stagger: { each: 0.05, from: 'start' },
      })
    },
  })
  return () => {
    stop()
    tween?.kill()
    revert()
  }
}

function alpha(el, extraIn) {
  let tweens = []
  const kill = () => tweens.forEach((t) => t.kill())
  return observe(el, {
    setOut: () => {
      kill()
      gsap.set(el, { autoAlpha: 0 })
    },
    animateIn: () => {
      kill()
      tweens = [gsap.to(el, { autoAlpha: 1, duration: 1.2, ease: EASE, delay: 0.1 })]
      if (extraIn) tweens.push(extraIn())
    },
  })
}

function scramble(el) {
  // like the original, inner markup is flattened to plain text
  const text = el.textContent
  return alpha(el, () =>
    gsap.to(el, {
      duration: 0.6 + Math.random() * 0.3,
      scrambleText: { text, chars: SCRAMBLE_CHARS, revealDelay: 0.3, speed: 1, delimiter: '', rightToLeft: false },
    }),
  )
}

function scale(el) {
  const kind = el.dataset.a
  const outState = { s: { scaleX: 0, scaleY: 0 }, sx: { scaleX: 0, scaleY: 1 }, sy: { scaleX: 1, scaleY: 0 } }[kind]
  const transformOrigin = el.dataset.origin || 'right center'
  let tween
  return observe(el, {
    setOut: () => {
      tween?.kill()
      gsap.set(el, { ...outState, transformOrigin })
    },
    animateIn: () => {
      tween?.kill()
      tween = gsap.to(el, { scaleX: 1, scaleY: 1, transformOrigin, duration: 1.2 + Math.random() * 0.2, ease: EASE, delay: 0.1 })
    },
  })
}

const HANDLERS = { word: textReveal, char: textReveal, line: textReveal, alpha, scramble, s: scale, sx: scale, sy: scale }

export function createReveals(root = document) {
  const cleanups = [...root.querySelectorAll('[data-a]')]
    .map((el) => HANDLERS[el.dataset.a]?.(el))
    .filter(Boolean)
  return () => cleanups.forEach((c) => c())
}
