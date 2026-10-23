import gsap from 'gsap'
import { createScroll } from './scroll.js'
import { createReveals } from './reveal.js'
import { createForm } from './form.js'
import { createCube } from './cube.js'
import { isMobile } from './env.js'

// Boots the whole motion layer once; returns a cleanup for React's effect.
export function boot() {
  let gl = null
  let disposed = false

  const page = document.querySelector('[data-start="hidden"]')
  gsap.to(page, { autoAlpha: 1, duration: 1, delay: 0.2 })

  const scroll = createScroll()
  const disposeReveals = createReveals()
  const disposeForm = createForm({ onSuccess: () => gl?.cube.solve() })

  // CTA hover darkens the cube (desktop only)
  const ctas = isMobile ? [] : [...document.querySelectorAll("[data-a='cta']")]
  const enter = () => gl?.cube.hover(1)
  const leave = () => gl?.cube.hover(0)
  ctas.forEach((el) => {
    el.addEventListener('mouseenter', enter)
    el.addEventListener('mouseleave', leave)
  })

  createCube(document.querySelector('[data-gl="c"]')).then((g) => {
    if (disposed) return g.destroy()
    gl = g
  })

  let raf = requestAnimationFrame(function loop(t) {
    scroll.raf(t)
    gl?.render(scroll.state)
    raf = requestAnimationFrame(loop)
  })

  return () => {
    disposed = true
    cancelAnimationFrame(raf)
    ctas.forEach((el) => {
      el.removeEventListener('mouseenter', enter)
      el.removeEventListener('mouseleave', leave)
    })
    disposeForm()
    disposeReveals()
    scroll.destroy()
    gl?.destroy()
  }
}
