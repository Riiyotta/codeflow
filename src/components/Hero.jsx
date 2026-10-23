import { CtaButton } from './Icons.jsx'

export function PriceNote({ xs }) {
  return (
    <div data-a="alpha" className={`font-fira ${xs ? 'xs ' : ''}text-center`}>
      *LOCK PRICE AT <strong>200$,</strong>
      <br />
      <strong>GUARANTEES</strong> ENTRY
    </div>
  )
}

export default function Hero() {
  return (
    <header id="intro" className="s hero">
      <div className="c">
        <div className="c heading-w">
          <div data-a="scramble" className="font-fira xs">A 8+ HOURS VIDEO COURSE</div>
          <h1 data-a="word" className="hero-he">
            WEBFLOW BUILDS
            <br />
            WITH NO WEBFLOW
            <br />
            {/* source markup as served; SplitText itself adds the leading empty span.z */}
            <span className="z">LIMITS</span>
            <span className="z"></span>
          </h1>
        </div>
        <div className="c flex-vc">
          <div className="hero-tx-w">
            <div data-delay="1" data-a="scramble" className="font-fira">JAVASCRIPT COURSE FOR</div>
            <div data-delay="1" data-a="scramble" className="font-fira bold-text">WEBFLOW DEVELOPERS</div>
          </div>
          <CtaButton>Reserve your Spot</CtaButton>
          <PriceNote xs />
        </div>
      </div>
    </header>
  )
}
