const NB = '\u00a0'

const TOPICS = [
  'API AND DATA', 'DOM', 'MANIPULATIONS', 'GSAP', 'ANIMATIONS', 'SMOOTH SCROLL', 'PAGE TRANSITIONS',
  'ADVANCED JS', 'RIVE & LOTTIE', 'LIBRARIES', 'DEV SETUP', 'COMPILERS', 'WORKFLOWS', 'THE BOILERPLATE™',
  'OPTIMISATION', 'BACKEND', 'WEBFLOW API', 'CI/CD', 'VIBE CODING', 'PERFORMANCE',
]
// these rows render behind the cube
const BEHIND = new Set(['MANIPULATIONS', 'COMPILERS', 'PERFORMANCE'])

export default function CourseContent() {
  return (
    <section id="content" className="s">
      <div className="c py-0">
        <h2 data-a="scramble" className="font-fira center">COURSE{NB}CONTENT</h2>
      </div>
      <ul data-counter="" role="list" className="list w-list-unstyled">
        {TOPICS.map((t) => (
          <li key={t} className={BEHIND.has(t) ? 'z' : undefined}>
            <h3 data-a="word" className="li-he">{t}</h3>
          </li>
        ))}
      </ul>
      <div className="c flex-vc">
        <div data-a="alpha" className="font-fira center max-w">
          <strong>8+ hours</strong> of In depth <strong>video MATERIAL,</strong> beginners to advanced, and advanced to
          masters with <strong>custom code in webflow</strong>
        </div>
      </div>
    </section>
  )
}
