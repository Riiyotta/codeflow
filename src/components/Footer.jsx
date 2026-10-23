import { Logo } from './Icons.jsx'

const NB = ' '

const Big = ({ children, className = 'ft-btxt' }) => (
  <div data-y="-150%" data-a="char" className={className}>{children}</div>
)

export default function Footer() {
  return (
    <footer className="s footer">
      <div className="c footer-c">
        <div className="ft-row">
          <div className="ft-block align-r">
            <a href="https://federic.ooo/s/twitter" target="_blank" rel="noreferrer" className="ft-lk w-inline-block">
              <div data-a="scramble" className="font-fira xs ul">TWEET{NB}@ ME</div>
            </a>
          </div>
        </div>
        <div className="ft-row">
          <Big>THE</Big>
          <div data-hide="tablet" className="ft-block">
            <div data-a="scramble" className="font-fira xs">WEBSITE</div>
            <ul data-a="alpha" role="list" className="ft-li w-list-unstyled">
              {[['#intro', 'INTRO'], ['#content', 'CONTENT'], ['#cta', 'CTA'], ['#signup', `SIGN${NB}UP`]].map(([href, t], i) => (
                <li key={href} className="ft-li-it">
                  <a href={href} className={`ft-li-lk w-inline-block${i === 0 ? ' w--current' : ''}`}>
                    <div>{t}</div>
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div className="z minus">
            <Big>CODE</Big>
          </div>
        </div>
        <div className="ft-row mob-vert">
          <div className="z">
            <Big>FLOW</Big>
          </div>
          <Big className="ft-btxt pl-sm"> CO</Big>
          <div className="ft-block flex-hb">
            <div data-hide="tablet">
              <Logo />
            </div>
            <div className="div-block-4">
              <a href="https://docs.google.com/document/d/1tzCCJaDVQFgwG0ai2A-VjvCNXtm4i-UmXPj6v0ZfiYQ/edit?usp=sharing" target="_blank" rel="noreferrer" className="w-inline-block">
                <div className="font-fira xs ul">PRIVACY{NB}POLICY</div>
              </a>
              <div data-a="alpha" className="font-fira xs tx-r">
                © 2024 —{NB}2025
                <br />
                <br />
                MADE BY{' '}
                <a href="https://federic.ooo/" target="_blank" rel="noreferrer" className="ul">
                  HTTPS://FEDERIC.OOO
                  <br />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
