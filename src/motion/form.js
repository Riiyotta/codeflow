// Submit stays locked until every non-email field is valid (i.e. the name is filled), as on the original.
// There is no MailChimp backend here, so a valid submit fakes Webflow's success state.
export function createForm({ onSuccess }) {
  const block = document.querySelector("[data-dom='form']")
  if (!block) return () => {}
  const form = block.querySelector('form')
  const submit = block.querySelector("[data-form='submit']")
  const done = block.querySelector("[data-listen='success']")
  const inputs = [...form.querySelectorAll('input:not([type=submit])')]

  const check = () => {
    const ok = inputs.every((i) => i.type === 'email' || i.checkValidity())
    submit.classList.toggle('lock', !ok)
    submit.style.pointerEvents = ok ? 'auto' : 'none'
  }
  // like the original, validity is only evaluated on input events (no inline pointer-events at load)
  inputs.forEach((i) => i.addEventListener('input', check))

  const onSubmit = (e) => {
    e.preventDefault()
    const label = submit.value
    submit.value = submit.dataset.wait
    setTimeout(() => {
      submit.value = label
      form.style.display = 'none'
      done.style.display = 'block'
      onSuccess()
    }, 800)
  }
  form.addEventListener('submit', onSubmit)
  return () => form.removeEventListener('submit', onSubmit)
}
