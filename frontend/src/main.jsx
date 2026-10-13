import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import './rjsf-form.css'
import RecordForm from './RecordForm'
import { prune } from './utils'

function readJson(id) {
  const el = document.getElementById(id)
  return el ? JSON.parse(el.textContent) : null
}

function Editor({ holder, input, schema, initial, errors }) {
  const [data, setData] = useState(initial || {})

  function change(next) {
    setData(next)
    // The Django form submits the whole record from this hidden field
    input.value = JSON.stringify(prune(next))
  }

  return (
    <RecordForm
      typeId={holder.dataset.typeId}
      schema={schema}
      data={data}
      onChange={change}
      organisationSearchUrl={holder.dataset.organisationSearchUrl}
      errors={errors}
    />
  )
}

function mount(holder) {
  const input = document.getElementById(holder.dataset.inputId)
  const schema = readJson(holder.dataset.schemaId)
  if (!input || !schema) return

  let initial = {}
  try {
    initial = input.value ? JSON.parse(input.value) : {}
  } catch (e) {
    initial = {}
  }

  // Enter in a text box must not submit the page: edits go to moderation, so saving should be deliberate.
  holder.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT') e.preventDefault()
  })

  // Problems the server found the last time this was saved, if any
  const errors = readJson(holder.dataset.errorsId) || []

  createRoot(holder).render(<Editor holder={holder} input={input} schema={schema} initial={initial} errors={errors} />)
}

function mountAll() {
  document.querySelectorAll('.rjsf-holder').forEach(mount)
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountAll)
} else {
  mountAll()
}
