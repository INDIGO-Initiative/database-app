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

export const widgets = {
  organisationWidget: props => <OrganisationInput multiple={false} {...props} />,
  organisationsWidget: props => <OrganisationInput multiple {...props} />,
}
