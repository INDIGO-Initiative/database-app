import { useEffect, useRef, useState } from 'react'

// Names of organisations we have already looked up, by ID.
const nameCache = new Map()

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
  if (!response.ok) throw new Error(`Request failed: ${response.status}`)
  return response.json()
}

function withParams(url, params) {
  return url + (url.includes('?') ? '&' : '?') + new URLSearchParams(params).toString()
}

function useOrganisationName(searchUrl, id) {
  const [name, setName] = useState(nameCache.get(id) ?? null)
  useEffect(() => {
    if (!id) return
    if (nameCache.has(id)) { setName(nameCache.get(id)); return }
    let cancelled = false
    getJson(withParams(searchUrl, { ids: id }))
      .then(r => {
        const found = r.results.find(o => o.id === id)
        nameCache.set(id, found ? found.name || '(no name)' : '(not found)')
      })
      .catch(() => nameCache.set(id, '(not found)'))
      .finally(() => { if (!cancelled) setName(nameCache.get(id)) })
    return () => { cancelled = true }
  }, [searchUrl, id])
  return name
}

function OrganisationName({ searchUrl, id }) {
  const name = useOrganisationName(searchUrl, id)
  return <span className="org-name">{id}{name ? ` — ${name}` : ''}</span>
}

function OrganisationSearch({ searchUrl, multiple, value, onChange }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const timer = useRef(null)

  useEffect(() => {
    clearTimeout(timer.current)
    if (query.trim().length < 2) { setResults([]); return }
    timer.current = setTimeout(() => {
      getJson(withParams(searchUrl, { search: query.trim() }))
        .then(r => setResults(r.results.slice(0, 8)))
        .catch(() => setResults([]))
    }, 250)
    return () => clearTimeout(timer.current)
  }, [searchUrl, query])

  function pick(org) {
    nameCache.set(org.id, org.name || '(no name)')
    if (multiple) {
      const ids = (value || '').split(',').map(s => s.trim()).filter(Boolean)
      if (!ids.includes(org.id)) ids.push(org.id)
      onChange(ids.join(','))
    } else {
      onChange(org.id)
    }
    setQuery('')
    setResults([])
  }

  return (
    <div className="org-search">
      <input
        type="search"
        className="form-control form-control-sm"
        placeholder="Search organisations by name…"
        value={query}
        onChange={e => setQuery(e.target.value)}
      />
      {results.length > 0 && (
        <ul className="org-search__results">
          {results.map(org => (
            <li key={org.id}>
              <button type="button" onClick={() => pick(org)}>{org.id} — {org.name || '(no name)'}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function OrganisationInput({ multiple, id, value, onChange, disabled, readonly, registry }) {
  const searchUrl = registry.formContext?.organisationSearchUrl
  const ids = multiple ? (value || '').split(',').map(s => s.trim()).filter(Boolean) : value ? [value] : []
  return (
    <div className="org-widget">
      <input
        id={id}
        type="text"
        className="form-control"
        value={value ?? ''}
        disabled={disabled || readonly}
        onChange={e => onChange(e.target.value === '' ? undefined : e.target.value)}
      />
      {searchUrl && ids.length > 0 && (
        <div className="org-widget__names">{ids.map(i => <OrganisationName key={i} searchUrl={searchUrl} id={i} />)}</div>
      )}
      {searchUrl && !(disabled || readonly) && (
        <OrganisationSearch
          searchUrl={searchUrl}
          multiple={multiple}
          value={value}
          onChange={v => onChange(v === '' ? undefined : v)}
        />
      )}
    </div>
  )
}

const OTHER = '__other__'

/**
 * A list of options as a dropdown, with "Other" to type a value that is not in the list. The standard has fixed
 * options, but the data does not always fit them, so a value that is not in the list is shown (and kept) instead of
 * vanishing from a dropdown that cannot show it.
 */
function ChoiceOrOther({ id, value, onChange, disabled, readonly, options, required }) {
  const choices = (options?.enumOptions || []).map(o => String(o.value)).filter(v => v !== '')
  const hasValue = value !== undefined && value !== null && value !== ''
  const notInList = hasValue && !choices.includes(String(value))
  // Chosen "Other" but not typed anything yet
  const [typing, setTyping] = useState(false)
  const showText = notInList || typing

  function pick(e) {
    const chosen = e.target.value
    if (chosen === OTHER) {
      setTyping(true)
    } else {
      setTyping(false)
      onChange(chosen === '' ? undefined : chosen)
    }
  }

  return (
    <div className="choice-or-other">
      <select
        id={id}
        className="form-control"
        value={showText ? OTHER : hasValue ? String(value) : ''}
        disabled={disabled || readonly}
        required={required}
        onChange={pick}
      >
        <option value="" />
        {choices.map(c => <option key={c} value={c}>{c}</option>)}
        <option value={OTHER}>Other (type your own)…</option>
      </select>
      {showText && (
        <input
          type="text"
          className="form-control choice-or-other__text"
          aria-label="Your own value"
          placeholder="Type your own value"
          value={hasValue ? String(value) : ''}
          disabled={disabled || readonly}
          onChange={e => onChange(e.target.value === '' ? undefined : e.target.value)}
        />
      )}
    </div>
  )
}

export const widgets = {
  choiceOrOtherWidget: ChoiceOrOther,
  organisationWidget: props => <OrganisationInput multiple={false} {...props} />,
  organisationsWidget: props => <OrganisationInput multiple {...props} />,
}
