import { CtaButton } from './Icons.jsx'
import { PriceNote } from './Hero.jsx'
import { Block } from './Features.jsx'

const NB = ' '

export default function Pricing() {
  return (
    <section id="cta" className="s">
      <div className="c py-lg">
        <div className="c heading-w">
          <div data-a="scramble" className="font-fira">Solve Webflow with code</div>
          <h2 data-a="word" className="hero-he">
            FIND <span className="z">THE</span>{' '}
            <br />
            MISSING PIECE
          </h2>
        </div>
        <div className="c flex-vc">
          <CtaButton>Reserve your Spot</CtaButton>
          <PriceNote />
        </div>
      </div>
      <div className="c flex-hb py-lg">
        <Block
          label="TIMELINE"
          l1="LIVE SEPT"
          l2="2025"
          mono={
            <>
              • SECTION 1 EST Q1 2025<br /><br />• COMMUNITY{NB}LIVE<br /><br />• First live session<br />
            </>
          }
        >
          <strong>Recording is starting for the first module. </strong>The course goes live progressively, with additional
          sections after initial launch.
          <br />
        </Block>
        <Block label="PRICE" l1="LOCK PRICE" l2="AT 200$*" mono="* THEN 250? Maybe 300? Maybe more? not sure">
          <strong>By joining the waitlist now.</strong> You'll receive a discount before the course goes live, allowing you
          to signup early, <span className="ul">guaranteeing entry</span> to the first cohort, and at a special discount.
        </Block>
      </div>
      <div data-hide="mobile" className="c fs">
        <div className="timeline-row header">
          <div className="table-first">
            <div data-a="scramble" className="font-fira xs">PRICE</div>
          </div>
          <div data-a="alpha" className="_1-4 py-sm">
            <div className="tl-header-he">WAITLIST{NB}AND{NB}EARLY{NB}ACCESS</div>
            <div className="font-fira xs">SEPT 2024</div>
          </div>
          <div data-a="alpha" className="_1-4 py-sm">
            <div className="tl-header-he">FIRST{NB}MODULE LAUNCH</div>
            <div className="font-fira xs">SEPT 2025</div>
          </div>
          <div data-a="alpha" className="_1-4 py-sm">
            <div className="tl-header-he">FULL COURSE LIVE</div>
            <div className="font-fira xs">~ +4M &gt; ∞</div>
          </div>
          <div data-a="sx" className="line abs"></div>
        </div>
        <ul role="list" className="timeline-li w-list-unstyled">
          <li className="timeline-row">
            <div className="table-first">
              <div className="font-fira bold-text">
                <strong data-a="scramble">200$</strong>
              </div>
            </div>
            <div className="_1-4 py-sm flex-c">
              <div data-a="s" className="dot"></div>
            </div>
            <div className="_1-4 py-sm"></div>
            <div className="_1-4 py-sm"></div>
            <div data-a="sx" className="line abs"></div>
          </li>
          <li className="timeline-row">
            <div className="table-first">
              <div data-a="scramble" className="font-fira">300+ $</div>
            </div>
            <div className="_1-4 py-sm flex-c"></div>
            <div data-a="sx" className="line abs"></div>
            <div className="_1-4 py-sm flex-c">
              <div data-a="s" className="dot"></div>
            </div>
          </li>
        </ul>
      </div>
    </section>
  )
}
