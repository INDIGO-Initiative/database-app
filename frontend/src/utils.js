import SECTION_GROUPS from '../../indigo/section_groups.json'

function isObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
}

// ------------------------------------------------------------------ JSON Schema

/** Follow $ref (and merge any sibling keys such as title and description, which our schemas put next to $ref). */
export function resolveRef(rootSchema, node) {
  let current = node
  const seen = new Set()
  while (current && current.$ref) {
    if (seen.has(current.$ref)) break
    seen.add(current.$ref)
    const target = current.$ref
      .replace(/^#\//, '')
      .split('/')
      .reduce((acc, part) => acc?.[part], rootSchema)
    const { $ref, ...siblings } = current
    current = { ...target, ...siblings }
  }
  return current
}

/** A {value, source_ids, status, sandboxes} block, which we render as one compact row. */
export function isValueBlock(schema) {
  const props = Object.keys(schema?.properties || {})
  return props.includes('value') && props.every(p => ['value', 'source_ids', 'status', 'sandboxes'].includes(p))
}

const VALUE_BLOCK_TITLES = { status: 'Status', source_ids: 'Sources' }

/** Does any property have a propertyOrder (a JSON Editor convention our schemas use)? */
function hasPropertyOrder(rootSchema, properties) {
  return Object.values(properties).some(p => typeof resolveRef(rootSchema, p)?.propertyOrder === 'number')
}

/** Property names sorted by propertyOrder. Properties without one keep their place, after the ones that have one. */
export function orderedKeys(rootSchema, properties) {
  const keys = Object.keys(properties)
  const order = k => {
    const o = resolveRef(rootSchema, properties[k])?.propertyOrder
    return typeof o === 'number' ? o : 1000 + keys.indexOf(k)
  }
  return [...keys].sort((a, b) => order(a) - order(b))
}

/**
 * Build an RJSF uiSchema from the JSON Schema: organisation references get the
 * lookup widget; long free text gets a textarea; lists of options let you type your own value too, except for
 * a status, which decides what is public and must be one of its options.
 */
export function buildUiSchema(rootSchema, node = rootSchema, depth = 0, propertyName = '') {
  const resolved = resolveRef(rootSchema, node)
  if (!resolved || depth > 12) return {}
  const ui = {}

  if (resolved['references-model'] === 'organisation') {
    ui['ui:widget'] = resolved['references-models-seperator'] ? 'organisationsWidget' : 'organisationWidget'
  } else if (resolved.type === 'string' && !resolved.enum && /\n|\(.{200,}/.test(resolved.description || '')) {
    ui['ui:widget'] = 'textarea'
  } else if (resolved.type === 'string' && Array.isArray(resolved.enum) && propertyName !== 'status') {
    ui['ui:widget'] = 'choiceOrOtherWidget'
  }

  if (resolved.type === 'array' && resolved.items) {
    const items = buildUiSchema(rootSchema, resolved.items, depth + 1)
    if (Object.keys(items).length) ui.items = items
  }
  for (const [name, child] of Object.entries(resolved.properties || {})) {
    const childUi = buildUiSchema(rootSchema, child, depth + 1, name)
    if (Object.keys(childUi).length) ui[name] = childUi
  }

  // Fields in the order the schema asks for (its propertyOrder), not alphabetical. The top level is ordered by
  // the tabs instead, because each tab only shows some of the fields, and RJSF refuses an order naming fields that are not there.
  if (depth > 0 && resolved.properties && hasPropertyOrder(rootSchema, resolved.properties)) {
    ui['ui:order'] = [...orderedKeys(rootSchema, resolved.properties), '*']
  }

  // {value, source_ids, status}: the value comes first, and the other parts get plain labels.
  if (isValueBlock(resolved)) {
    ui['ui:order'] = ['value', 'status', 'source_ids', '*']
    for (const [name, title] of Object.entries(VALUE_BLOCK_TITLES)) {
      if (resolved.properties[name]) ui[name] = { ...ui[name], 'ui:title': title }
    }
  }
  return ui
}

// ------------------------------------------------------------------------- tabs

// Hand-picked tab groups, roughly following the spreadsheet tabs. Properties not listed fall into "Other".
// They are in indigo/section_groups.json so the record pages (which show the same sections) use the same ones.
export const TAB_GROUPS = SECTION_GROUPS

/**
 * Split a schema's top-level properties into tabs: [{id, label, keys}].
 * Types without hand-picked groups get a "General" tab of single values and
 * a tab for each list.
 */
export function buildTabs(typeId, schema) {
  const all = orderedKeys(schema, schema.properties || {})
  const groups = TAB_GROUPS[typeId]
  if (groups) {
    const tabs = groups
      .map(([label, keys]) => ({ id: label, label, keys: keys.filter(k => all.includes(k)) }))
      .filter(t => t.keys.length)
    const used = new Set(tabs.flatMap(t => t.keys))
    const rest = all.filter(k => !used.has(k))
    if (rest.length) tabs.push({ id: 'Other', label: 'Other', keys: rest })
    return tabs
  }
  const isList = k => resolveRef(schema, schema.properties[k]).type === 'array' &&
    resolveRef(schema, resolveRef(schema, schema.properties[k]).items || {}).type === 'object'
  const general = all.filter(k => !isList(k))
  const tabs = [{ id: 'General', label: 'General', keys: general }]
  for (const k of all.filter(isList)) {
    tabs.push({ id: k, label: schema.properties[k].title || k, keys: [k] })
  }
  return tabs.filter(t => t.keys.length)
}

export function tabSchema(schema, keys) {
  return {
    ...schema,
    required: (schema.required || []).filter(k => keys.includes(k)),
    properties: Object.fromEntries(keys.map(k => [k, schema.properties[k]])),
  }
}

/** Merge one tab's edited values back into the whole record. */
export function mergeTabData(whole, tabKeys, tabData) {
  const next = { ...whole }
  for (const key of tabKeys) {
    if (tabData && tabData[key] !== undefined) next[key] = tabData[key]
    else delete next[key]
  }
  return next
}

// ------------------------------------------------------------------------ prune

const isBlank = v => v === null || v === undefined || v === ''

/**
 * Remove blank values and the empty objects they leave behind, so a field left blank is the same as a field
 * that was never filled in. Blank list items are dropped; an empty list is kept (it means "no rows").
 */
export function prune(value) {
  if (Array.isArray(value)) {
    return value.map(prune).filter(v => !isBlank(v) && !(isObject(v) && Object.keys(v).length === 0))
  }
  if (isObject(value)) {
    const out = {}
    for (const [k, v] of Object.entries(value)) {
      const pruned = prune(v)
      if (isBlank(pruned) || (isObject(pruned) && Object.keys(pruned).length === 0)) continue
      out[k] = pruned
    }
    return out
  }
  return value
}

// ----------------------------------------------------------------------- errors

/** "/outcome_funds/0/id" -> ['outcome_funds', '0', 'id'] */
export function pointerToPath(pointer) {
  if (!pointer) return []
  return pointer
    .slice(1)
    .split('/')
    .map(p => p.replace(/~1/g, '/').replace(/~0/g, '~'))
}

/**
 * Turn the server's [{path, message}] (path is a JSON pointer) into RJSF's extraErrors tree:
 * {outcome_funds: {0: {id: {__errors: ['msg']}}}}
 */
export function errorsToExtraErrors(errors) {
  const tree = {}
  for (const { path, message } of errors || []) {
    let node = tree
    for (const part of pointerToPath(path)) {
      if (!isObject(node[part])) node[part] = {}
      node = node[part]
    }
    node.__errors = [...(node.__errors || []), message]
  }
  return tree
}

/** How many errors are under each top level key: {outcome_funds: 2, name: 1} */
export function countErrorsByTopLevelKey(errors) {
  const counts = {}
  for (const { path } of errors || []) {
    const key = pointerToPath(path)[0] ?? ''
    counts[key] = (counts[key] || 0) + 1
  }
  return counts
}

// -------------------------------------------------------------------- warnings

/** ['outcome_funds', 0, 'id'] -> "/outcome_funds/0/id" */
export function pathToPointer(path) {
  return (path || []).map(p => '/' + String(p).replace(/~/g, '~0').replace(/\//g, '~1')).join('')
}

/** The value at a JSON pointer in the data, or undefined if there is nothing there. */
export function valueAtPath(data, pointer) {
  let node = data
  for (const part of pointerToPath(pointer)) {
    if (node === null || node === undefined || typeof node !== 'object') return undefined
    node = node[part]
  }
  return node
}

/**
 * The warnings that still apply. The server's [{path, message, value}] are about the data as it was loaded (or last
 * submitted); once someone changes a value, the warning about the old one no longer applies, so it is dropped.
 */
export function currentWarnings(warnings, data) {
  return (warnings || []).filter(w => JSON.stringify(valueAtPath(data, w.path)) === JSON.stringify(w.value))
}

/** The messages for each place in the data: {"/investments/0/investment_type/value": ['...']} */
export function warningsByPointer(warnings) {
  const lookup = {}
  for (const { path, message } of warnings || []) {
    lookup[path] = [...(lookup[path] || []), message]
  }
  return lookup
}
