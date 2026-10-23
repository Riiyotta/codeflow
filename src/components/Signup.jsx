const NB = ' '

export default function Signup() {
  return (
    <section id="signup" className="s flex-vb">
      <div className="c flex-hb">
        <div className="tb-w _1-2">
          <h2 data-a="word" className="tb-he py-xs">
            JOIN THE
            <br />
            WAITLIST
          </h2>
          <p data-a="alpha" className="tb-text">
            <strong>Lock launch price at 200$ and guarantee entry to first cohort.</strong> I'll only send few updates on
            course completion, or probably just the launch one.
          </p>
          <ul role="list" className="join-li w-list-unstyled">
            <li><div data-a="word">Early access at 50% discount (then 250$+)</div></li>
            <li><div data-a="word">Early access to Discord inner circle</div></li>
            <li><div data-a="word">Guaranteed entry to 1st cohort</div></li>
          </ul>
        </div>
        <div className="tb-w _1-2 vc">
          <div data-dom="form" className="form-block w-form">
            <form id="email-form" name="email-form" data-name="Email Form" method="post" className="lead-c" aria-label="Email Form">
              <div className="lead-b-w">
                <div data-a="alpha" className="lead-block">
                  <label htmlFor="name" className="lead-label">First Name *</label>
                  <div className="field-w">
                    <input className="lead-field w-input" maxLength={256} name="name" data-name="Name" placeholder="Your Name" type="text" id="name" required />
                    <div data-origin="left center" data-a="sx" className="line abs"></div>
                  </div>
                </div>
                <div data-a="alpha" className="lead-block">
                  <label htmlFor="email" className="lead-label">Email Address *</label>
                  <div className="field-w">
                    <input className="lead-field w-input" maxLength={256} name="email" data-name="Email" placeholder="example@email.com" data-validate="email" type="email" id="email" required />
                    <div data-a="sx" className="line abs"></div>
                  </div>
                </div>
                <div className="lead-block">
                  <div data-viz="hidden" data-form="hint" className="lead-hint">...</div>
                </div>
              </div>
              <input type="submit" data-wait="Almost there!" data-form="submit" className="button-c lock w-button" value="Get In" />
            </form>
            <div data-listen="success" className="lead-succ-w w-form-done" tabIndex={-1} role="region" aria-label="Email Form success">
              <div className="div-block-5">
                <div data-a="scramble" className="succ-he">YOU{NB}ARE{NB}IN.<br /></div>
                <div data-a="scramble" className="font-fira"> Catch up soon!</div>
              </div>
            </div>
            <div className="lead-err w-form-fail" tabIndex={-1} role="region" aria-label="Email Form failure">
              <div>Something went wrong. Try again?</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
