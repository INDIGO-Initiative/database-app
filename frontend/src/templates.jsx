import { getTemplate, getUiOptions } from '@rjsf/utils'
import { isValueBlock } from './utils'

function Help({ description }) {
  if (!description) return null
  const text = typeof description === 'string' ? description : null
  if (text === null) return <div className="field-help">{description}</div>
  if (text.length < 90) return <div className="field-help">{text}</div>
  return (
    <details className="field-help">
      <summary>Help</summary>
      <p>{text}</p>
    </details>
  )
}

function ObjectFieldTemplate(props) {
  const { title, description, properties, schema } = props

  // {value, source_ids, status}: one compact row.
  if (isValueBlock(schema)) {
    return (
      <div className="value-block">
        {title && <div className="value-block__title">{title}</div>}
        <Help description={description} />
        <div className="value-block__row">
          {properties.map(p => (
            <div key={p.name} className={`value-block__cell value-block__cell--${p.name}`}>{p.content}</div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <fieldset className="object-block">
      {title && <legend>{title}</legend>}
      <Help description={description} />
      {properties.map(p => p.content)}
    </fieldset>
  )
}

function DescriptionFieldTemplate({ description }) {
  return <Help description={description} />
}

function TitleFieldTemplate({ title, id }) {
  // Used for list titles. Objects render their own legend / value-block title.
  if (!title) return null
  return <h3 id={id} className="field-title">{title}</h3>
}

// RJSF's default buttons use Bootstrap 3 glyphicons, which Bootstrap 4 (used by the admin pages) does not have.
// Use Font Awesome instead, which the admin pages already load.
function iconButton(icon, variant, label) {
  return function IconButton({ id, className, onClick, disabled, title, style }) {
    return (
      <button
        type="button"
        id={id}
        className={`btn btn-sm btn-${variant} ${className || ''}`}
        onClick={onClick}
        disabled={disabled}
        title={title || label}
        style={style}
      >
        <i className={`fa-solid fa-${icon}`} aria-hidden="true" />
        <span className="sr-only">{label}</span>
      </button>
    )
  }
}

function AddButton({ id, className, onClick, disabled }) {
  return (
    <p>
      <button type="button" id={id} className={`btn btn-sm btn-info ${className || ''}`} onClick={onClick} disabled={disabled}>
        <i className="fa-solid fa-plus" aria-hidden="true" /> Add
      </button>
    </p>
  )
}

const ButtonTemplates = {
  AddButton,
  CopyButton: iconButton('copy', 'secondary', 'Copy'),
  MoveDownButton: iconButton('arrow-down', 'secondary', 'Move down'),
  MoveUpButton: iconButton('arrow-up', 'secondary', 'Move up'),
  RemoveButton: iconButton('xmark', 'danger', 'Remove'),
  ClearButton: iconButton('xmark', 'secondary', 'Clear'),
}

// The default item template lays out with Bootstrap 3 grid classes (col-xs-*); use flexbox instead.
function ArrayFieldItemTemplate({ children, className, buttonsProps, hasToolbar, registry, uiSchema }) {
  const Buttons = getTemplate('ArrayFieldItemButtonsTemplate', registry, getUiOptions(uiSchema))
  return (
    <div className={`${className || ''} array-item`}>
      <div className="array-item__content">{children}</div>
      {hasToolbar && (
        <div className="array-item__toolbox">
          <div className="btn-group">
            <Buttons {...buttonsProps} />
          </div>
        </div>
      )}
    </div>
  )
}

export const templates = {
  ObjectFieldTemplate,
  DescriptionFieldTemplate,
  TitleFieldTemplate,
  ButtonTemplates,
  ArrayFieldItemTemplate,
}
