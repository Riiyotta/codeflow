import Lenis from 'lenis'
import { lerp } from './env.js'

export function createScroll() {
  const lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    orientation: 'vertical',
    smoothWheel: true,
    touchMultiplier: 2,
  })

  // smoothed state read by the cube every frame
  const state = { y: 0, progress: 0, velocity: 0, lp: 0 }
  lenis.on('scroll', (l) => {
    state.y = l.scroll
    state.progress = l.progress || 0
    state.velocity = l.velocity
  })

  // in-page anchors (#signup etc.)
  const onClick = (e) => {
    const a = e.target.closest('a[href^="#"]')
    if (!a) return
    const id = a.getAttribute('href')
    if (id.length < 2) return e.preventDefault()
    const target = document.querySelector(id)
    if (!target) return
    e.preventDefault()
    // match the Webflow runtime's anchor scroll: distance-based duration, easeInOutCubic
    const dist = Math.abs(target.getBoundingClientRect().top)
    lenis.scrollTo(target, {
      duration: Math.max(0, 472.143 * Math.log(dist + 125) - 2000) / 1000,
      easing: (t) => (t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1),
    })
  }
  document.addEventListener('click', onClick)

  const setVh = () => document.documentElement.style.setProperty('--100vh', `${window.innerHeight}px`)
  setVh()
  window.addEventListener('resize', setVh)

  return {
    lenis,
    state,
    raf(time) {
      lenis.raf(time)
      state.lp = lerp(state.lp, state.progress, 0.1)
    },
    destroy() {
      document.removeEventListener('click', onClick)
      window.removeEventListener('resize', setVh)
      lenis.destroy()
    },
  }
}
