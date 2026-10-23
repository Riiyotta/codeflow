const NB = ' '
const ZWJ = '‍'

export function Block({ label, l1, l2, children, mono, right }) {
  return (
    <div className={right ? 'tb-w mt-xl' : 'tb-w'}>
      <div data-a="scramble" className="font-fira">{label}</div>
      <h3 data-a="word" className="tb-he py-xs">
        {l1}
        <br />
        {l2}
      </h3>
      <p data-a="alpha" className="tb-text">{children}</p>
      {mono && <div data-a="alpha" className="font-fira mt-md">{mono}</div>}
    </div>
  )
}

export default function Features() {
  return (
    <section id="cta" className="s">
      <div className="c flex-hb py-lg">
        <Block
          label="CONTENT"
          l1="10+ HOURS"
          l2="OF VIDEO"
          mono={
            <>
              • 4 sections<br />{ZWJ}<br />•{NB}2 FULL{NB}LIVE BUILDS<br /><br />•{NB}COMMUNITY{NB}SUPPORT<br /><br />• LEARN{NB}TOGETHER
              <br /><br />• LIVE{NB}SESSION{NB}MONTHLY
            </>
          }
        >
          Split into <strong>skill-based modules,</strong> you'll learn different <span className="ul">workflows</span> that
          are effective and applicable, even if you haven't completed the entire course.
          <br />
        </Block>
        <Block
          right
          label="SKILLS"
          l1="BEGINNER TO"
          l2="ADVANCED"
          mono={
            <>
              &gt; JOIN{NB}AT{NB}ANY{NB}POINT<br />{ZWJ}<br />&lt; END{NB}AT{NB}ANY{NB}PoNT
            </>
          }
        >
          <strong>And Advanced to master</strong>
          <strong>.</strong> Tailored to accommodate learners at any stage of their journey, ensuring{' '}
          <span className="ul">you can start from your current skill</span> level and gain practical, actionable knowledge
          at every step.
        </Block>
      </div>
      <div className="c flex-hb py-lg">
        <Block label="FEATURES (1/2)" l1="DISCORD" l2="COMMUNITY">
          <strong>Learn with others</strong> following the same path, get help and share progress. Plus challenges, and{' '}
          <span className="ul">a network of other freelancers</span> with the same skillset as you.
          <br />
        </Block>
        <Block right label="FEATURES (2/2)" l1="REAL LIFE " l2="LIVE BUILDS">
          <strong>Featuring a full real-life website build:</strong> dive into building and deconstructing fully functional
          websites with the newly acquired skills.
        </Block>
      </div>
    </section>
  )
}
