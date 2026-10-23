import { CtaButton, Discord, Logo } from './Icons.jsx'

export default function Navbar() {
  return (
    <nav className="nav">
      <div className="nav-par">
        A practical <strong>Javascript</strong> course to <strong>level up</strong> no-code developers<strong>.</strong> From
        the basics to doing anything you can imagine, through <strong>animations,</strong> custom libraries, dev
        environment, a proper setup and all that fun stuffs.
      </div>
      <div className="nav-cent">
        <div data-a="scramble" className="font-fira xs">(ver 0.2)</div>
      </div>
      <div className="nav-cta-w">
        <a arial-label="discord" data-hide="mobile" href="#" className="link-c w-inline-block">
          <Discord />
        </a>
        <CtaButton className="sm">Join Waitlist</CtaButton>
        <Logo />
      </div>
    </nav>
  )
}
