import gsap from 'gsap'
import { CustomEase } from 'gsap/CustomEase'
import { Renderer, Camera, Transform, Program, Texture, GLTFLoader } from 'ogl'
import { isMobile, lerp } from './env.js'

gsap.registerPlugin(CustomEase)

const ASSETS = {
  mtc1: '/assets/webgl/mtc16.webp',
  mtc2: '/assets/webgl/mtc3.webp',
  colMap: '/assets/webgl/col_map.webp',
  model: '/assets/webgl/cube8.glb',
}

// push-back-and-spring curve used on click
const CLICK_EASE = CustomEase.create(
  'cubeClick',
  'M0,0 C0.126,0.382 0.18,0.726 0.241,0.726 0.397,0.726 0.482,-0.234 0.619,-0.234 0.746,-0.234 0.768,0 1,0',
)

const vertex = /* glsl */ `
  attribute vec3 position;
  attribute vec3 normal;
  attribute vec2 uv;
  uniform mat4 modelViewMatrix;
  uniform mat4 projectionMatrix;
  uniform mat3 normalMatrix;
  varying vec3 vNormal;
  varying vec3 vView;
  varying vec2 vUv;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vView = normalize(-mv.xyz);
    vNormal = normalize(normalMatrix * normal);
    vUv = uv;
    gl_Position = projectionMatrix * mv;
  }
`

// Matcap shading: the top half of the UV atlas is the plastic body, the bottom half the stickers.
// Hover darkens the stickers and hints at their colors; "solved" shows full colors.
const fragment = /* glsl */ `
  precision highp float;
  varying vec3 vNormal;
  varying vec3 vView;
  varying vec2 vUv;
  uniform sampler2D tMatcapA;
  uniform sampler2D tMatcapB;
  uniform sampler2D tColors;
  uniform float uHover;
  uniform float uSolved;
  const vec3 BG = vec3(15.0 / 255.0);

  void main() {
    vec3 side = normalize(vec3(vView.z, 0.0, -vView.x));
    vec3 up = cross(vView, side);
    vec2 capUv = vec2(dot(side, vNormal), dot(up, vNormal)) * 0.495 + 0.5;

    vec3 capA = texture2D(tMatcapA, capUv).rgb;
    vec3 capB = texture2D(tMatcapB, capUv).rgb;
    float body = 1.0 - step(vUv.y, 0.5);
    float sticker = 1.0 - body;

    vec3 cap = mix(capA, capB, body);
    cap = mix(cap, capB, body * (1.0 - capUv.y));
    vec3 col = mix(BG * 0.9, vec3(1.0), cap);

    vec3 colors = texture2D(tColors, vUv).rgb;
    col = mix(col, col * 0.1, sticker * uHover);
    col = mix(col, col + colors * 0.1, sticker * uHover);
    col = mix(col, col + colors, sticker * uSolved);
    gl_FragColor = vec4(col, 1.0);
  }
`

function loadTexture(gl, src, opts = {}) {
  return new Promise((resolve) => {
    const texture = new Texture(gl, opts)
    const img = new Image()
    img.onload = () => {
      texture.image = img
      resolve(texture)
    }
    img.src = src
  })
}

// pointer inertia: moving the mouse adds spin, which decays back to a constant idle drift
class Spinner {
  velocity = { x: 0.05, y: 0.05 }
  spin = { x: 0, y: 0 }
  mult = 0.8
  down = false
  last = null

  constructor() {
    this.onMove = (e) => {
      const p = e.touches ? e.touches[0] : e
      if (this.last) {
        this.velocity.x += (p.clientX - this.last.x) * 0.002 * this.mult
        this.velocity.y += (p.clientY - this.last.y) * 0.002 * this.mult
      }
      this.last = { x: p.clientX, y: p.clientY }
    }
    this.onDown = () => ((this.down = true), (this.mult = 1))
    this.onUp = () => ((this.down = false), (this.mult = 0.8))
    window.addEventListener('mousemove', this.onMove)
    window.addEventListener('touchmove', this.onMove, { passive: true })
    window.addEventListener('pointerdown', this.onDown)
    window.addEventListener('pointerup', this.onUp)
  }

  render() {
    const drift = this.down ? 0 : 0.005
    for (const k of ['x', 'y']) {
      this.velocity[k] *= 0.97
      this.spin[k] += this.velocity[k] + Math.sign(this.velocity[k]) * drift
    }
  }

  destroy() {
    window.removeEventListener('mousemove', this.onMove)
    window.removeEventListener('touchmove', this.onMove)
    window.removeEventListener('pointerdown', this.onDown)
    window.removeEventListener('pointerup', this.onUp)
  }
}

class Cube extends Transform {
  a = { mx: 0, my: 0, scale: 0.1, lspeed: 0, initial: 3, click: 0 }
  isSolved = false
  rotateAxis = true
  layerIndex = 0
  shouldReset = false

  constructor(gl, { model, mtc1, mtc2, colMap }) {
    super()
    this.ctrl = new Transform()
    this.ctrl.setParent(this)
    this.program = new Program(gl, {
      vertex,
      fragment,
      transparent: true,
      cullFace: null,
      uniforms: {
        tMatcapA: { value: mtc1 },
        tMatcapB: { value: mtc2 },
        tColors: { value: colMap },
        uHover: { value: 0 },
        uSolved: { value: 0 },
      },
    })
    this.model = model
    this.layers = model.children
    this.layers.forEach((layer) => layer.traverse((n) => n.program && (n.program = this.program)))
    model.setParent(this.ctrl)
    model.scale.set(this.a.scale)

    this.spinner = new Spinner()
    gsap.to(this.a, { initial: 0, ease: 'back.out', duration: 1.2 })
    this.startTwists()
  }

  startTwists(on = true) {
    clearInterval(this.interval)
    if (!on) return void (this.shouldReset = true)
    this.interval = setInterval(() => this.twist(0.8), 0.8 * 2100)
  }

  stopTwists() {
    this.startTwists(false)
  }

  resetCube() {
    this.shouldReset = false
    this.layers.forEach((l) => (l.rotation.y = 0))
    this.ctrl.rotation.x = 0
    this.ctrl.rotation.z = 0
  }

  // one Rubik move on the next layer; afterwards the whole cube is re-oriented so the next move uses another axis
  twist(duration) {
    this.layerIndex = (this.layerIndex + 1) % 3
    const layer = this.layers[this.layerIndex]
    const dir = Math.random() > 0.5 ? 1 : -1
    const amount = Math.random() > 0.5 ? Math.PI / 2 : Math.PI
    gsap.to(layer.rotation, {
      y: layer.rotation.y + amount * dir,
      duration,
      // the original asks for "slow.out", which is unavailable there and falls back to power1.out
      ease: Math.random() > 0.5 ? 'power1.out' : 'back.inOut',
      onComplete: () => {
        if (this.shouldReset) return this.resetCube()
        if (!this.rotateAxis) return
        if (Math.random() > 0.5) this.ctrl.rotation.z += Math.PI / 2
        else this.ctrl.rotation.x += Math.PI / 2
      },
    })
  }

  hover(v) {
    if (this.isSolved) return
    if (v > 0.5) this.rotateAxis = false
    this.hoverTween?.kill()
    this.hoverTween = gsap.to(this.program.uniforms.uHover, {
      value: v,
      ease: 'expo.out',
      duration: 1.2,
      onComplete: () => {
        if (v < 0.5) {
          this.stopTwists()
          this.startTwists()
        }
      },
    })
  }

  click() {
    if (this.clicking) return
    this.clicking = true
    gsap.to(this.a, { click: 5, duration: 1.6, ease: CLICK_EASE, onComplete: () => (this.clicking = false) })
  }

  solve() {
    this.isSolved = true
    this.stopTwists()
    const root = document.documentElement
    const original = getComputedStyle(root).getPropertyValue('--black').trim()
    const flash = ['#b71234', '#0046ad'][Math.floor(Math.random() * 2)]
    gsap
      .timeline()
      .to(root, { '--black': flash, duration: 1.2, delay: 0.4, ease: 'elastic.out' })
      .to(root, { '--black': original, duration: 1.2, delay: 0.4, ease: 'power1.out' })
    gsap.to(this.program.uniforms.uSolved, {
      value: 1,
      duration: 1.8,
      delay: 0.4,
      ease: 'elastic.out',
      onComplete: () =>
        setTimeout(() => {
          this.rotateAxis = false
          this.startTwists()
        }, 1000),
    })
  }

  update(time, scroll) {
    const a = this.a
    a.lspeed = lerp(a.lspeed, scroll.velocity * 0.015, 0.05)
    this.spinner.render()

    const base = time * 0.01
    const rx = this.spinner.spin.y * 0.1 + base + scroll.lp * 5
    const ry = this.spinner.spin.x * 0.1 + base + scroll.lp * 5
    if (!isMobile) {
      a.mx = lerp(a.mx, this.spinner.velocity.x, 0.1)
      a.my = lerp(a.my, -this.spinner.velocity.y, 0.1)
      this.position.x = a.mx * 0.5
    }
    const y = scroll.progress * 0.45 + a.lspeed + a.initial
    const s = a.scale + scroll.progress * (isMobile ? 0 : 0.05) + this.program.uniforms.uHover.value * 0.02
    const depth = Math.abs(Math.sin(this.position.x)) - Math.abs(Math.sin(this.position.y))

    this.model.scale.set(s)
    this.position.z = -depth - a.click
    this.position.y = y + a.my
    this.rotation.x = rx + a.click * 0.2
    this.rotation.y = ry + a.click * 0.2
  }

  destroy() {
    clearInterval(this.interval)
    this.spinner.destroy()
  }
}

// Find the node that holds the 3 horizontal layers (scene[0] -> "Empty.002").
function findLayerRoot(gltf) {
  const roots = [].concat(...gltf.scene)
  let found = null
  roots.forEach((r) =>
    r.traverse((n) => {
      if (!found && n.children.length === 3) found = n
    }),
  )
  return found || roots[0]
}

export async function createCube(container) {
  const renderer = new Renderer({ dpr: 2, antialias: true, alpha: true })
  const gl = renderer.gl
  gl.clearColor(0, 0, 0, 0)
  container.appendChild(gl.canvas)

  const camera = new Camera(gl, { fov: 25, near: 0.1, far: 100 })
  camera.position.set(0, 0, 5)
  const scene = new Transform()
  const group = new Transform()
  group.position.y = -0.5
  group.setParent(scene)

  const resize = () => {
    const { width, height } = container.getBoundingClientRect()
    renderer.setSize(width, height)
    camera.perspective({ aspect: width / height })
  }
  const ro = new ResizeObserver(resize)
  ro.observe(container)
  resize()

  const [mtc1, mtc2, colMap, gltf] = await Promise.all([
    loadTexture(gl, ASSETS.mtc1),
    loadTexture(gl, ASSETS.mtc2),
    loadTexture(gl, ASSETS.colMap, { flipY: false }),
    GLTFLoader.load(gl, ASSETS.model),
  ])
  const cube = new Cube(gl, { model: findLayerRoot(gltf), mtc1, mtc2, colMap })
  cube.setParent(group)

  const onClick = () => cube.click()
  const onKey = (e) => e.key === '!' && cube.solve()
  document.addEventListener('click', onClick)
  document.addEventListener('keydown', onKey)

  let time = 0
  return {
    cube,
    render(scroll) {
      time += 0.5
      cube.update(time, scroll)
      renderer.render({ scene, camera })
    },
    destroy() {
      ro.disconnect()
      cube.destroy()
      document.removeEventListener('click', onClick)
      document.removeEventListener('keydown', onKey)
      gl.canvas.remove()
    },
  }
}
