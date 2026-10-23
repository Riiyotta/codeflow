import arrow from '../svg/arrow.svg?raw'
import logo from '../svg/logo.svg?raw'
import discord from '../svg/discord.svg?raw'

// Webflow "w-embed" wrappers: raw SVG markup, exactly as on the original
export const Arrow = () => <div className="btn-ic w-embed" dangerouslySetInnerHTML={{ __html: arrow }} />
export const Logo = () => <div className="logo xs w-embed" dangerouslySetInnerHTML={{ __html: logo }} />
export const Discord = () => <div className="icon w-embed" dangerouslySetInnerHTML={{ __html: discord }} />

export function CtaButton({ children, className = '' }) {
  return (
    <a href="#signup" data-a="cta" className={`button-c ${className} w-inline-block`.replace(/\s+/g, ' ')}>
      <div className="cta-tx">{children}</div>
      <Arrow />
    </a>
  )
}
