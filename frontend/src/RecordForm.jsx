import { useMemo, useState } from 'react'
import Form from '@rjsf/core'
import validator from '@rjsf/validator-ajv8'
import { widgets } from './widgets'
import { templates } from './templates'
import { buildTabs, buildUiSchema, countErrorsByTopLevelKey, errorsToExtraErrors, mergeTabData, tabSchema } from './utils'

/**
 * Tabbed form for one record, generated from its JSON Schema.
 *
 * Only the active tab is rendered. The server validates the whole record when the page is saved
 * (the schema is the single source of truth), so client side validation is off.
 */
export default function RecordForm({ typeId, schema, data, onChange, organisationSearchUrl, errors = [] }) {
  const tabs = useMemo(() => buildTabs(typeId, schema), [typeId, schema])
  const uiSchema = useMemo(() => buildUiSchema(schema), [schema])
  const errorCounts = useMemo(() => countErrorsByTopLevelKey(errors), [errors])
  const extraErrors = useMemo(() => errorsToExtraErrors(errors), [errors])
  const tabErrorCount = tab => tab.keys.reduce((n, k) => n + (errorCounts[k] || 0), 0)
  // Open on the first tab with a problem, if the server found any
  const [activeId, setActiveId] = useState((tabs.find(t => tabErrorCount(t) > 0) || tabs[0])?.id)
  const active = tabs.find(t => t.id === activeId) || tabs[0]

  const subSchema = useMemo(() => (active ? tabSchema(schema, active.keys) : null), [schema, active])
  const subUiSchema = useMemo(
    () => Object.fromEntries(Object.entries(uiSchema).filter(([k]) => active?.keys.includes(k) || k.startsWith('ui:'))),
    [uiSchema, active],
  )
  const formContext = useMemo(() => ({ organisationSearchUrl }), [organisationSearchUrl])

  if (!active) return null

  return (
    <div className="record-form">
      <ul className="nav nav-pills record-form__tabs" role="tablist" aria-orientation="vertical">
        {tabs.map(tab => (
          <li className="nav-item" key={tab.id}>
            <button
              type="button"
              role="tab"
              aria-selected={tab.id === active.id}
              className={`nav-link${tab.id === active.id ? ' active' : ''}`}
              onClick={() => setActiveId(tab.id)}
            >
              {tab.label}
              {tabErrorCount(tab) > 0 && (
                <span className="badge badge-danger record-form__badge" title="Problems found when saving">
                  {tabErrorCount(tab)}
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>

      <div className="record-form__panel" role="tabpanel">
        <h3 className="record-form__panel-title">{active.label}</h3>
        <Form
          key={active.id}
          tagName="div"
          schema={subSchema}
          uiSchema={subUiSchema}
          formData={Object.fromEntries(active.keys.filter(k => data[k] !== undefined).map(k => [k, data[k]]))}
          validator={validator}
          widgets={widgets}
          templates={templates}
          formContext={formContext}
          extraErrors={extraErrors}
          extraErrorsBlockSubmit={false}
          noValidate
          showErrorList={false}
          onChange={e => onChange(mergeTabData(data, active.keys, e.formData))}
        >
          {/* Saving is done by the page's own button */}
          <></>
        </Form>
      </div>
    </div>
  )
}
