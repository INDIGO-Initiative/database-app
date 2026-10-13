import {
  buildTabs,
  buildUiSchema,
  countErrorsByTopLevelKey,
  errorsToExtraErrors,
  isValueBlock,
  mergeTabData,
  orderedKeys,
  pointerToPath,
  prune,
  resolveRef,
  tabSchema,
} from './utils'

describe('propertyOrder', () => {
  const ordered = {
    properties: {
      zeta: { type: 'string', propertyOrder: 10 },
      alpha: { type: 'string', propertyOrder: 30 },
      loose: { type: 'string' },
      middle: { type: 'string', propertyOrder: 20 },
    },
  }
  it('sorts by propertyOrder, with properties that have none after', () => {
    expect(orderedKeys(ordered, ordered.properties)).toEqual(['zeta', 'middle', 'alpha', 'loose'])
  })
  it('orders the tab contents the same way', () => {
    const tabs = buildTabs('whatever', ordered)
    expect(tabs[0].keys).toEqual(['zeta', 'middle', 'alpha', 'loose'])
  })
  it('orders nested groups with ui:order, but not the top level', () => {
    const nested = { properties: { group: { type: 'object', properties: ordered.properties } } }
    const ui = buildUiSchema(nested)
    expect(ui['ui:order']).toBeUndefined()
    expect(ui.group['ui:order']).toEqual(['zeta', 'middle', 'alpha', 'loose', '*'])
  })
})

const schema = {
  definitions: {
    str: { type: 'object', properties: { value: { type: 'string' }, status: { type: 'string' } } },
    org: { type: 'object', properties: { value: { type: 'string', 'references-model': 'organisation' } } },
  },
  properties: {
    name: { title: 'Name', $ref: '#/definitions/str' },
    lead: { $ref: '#/definitions/org' },
    notes: { type: 'string' },
    rows: { type: 'array', title: 'Rows', items: { type: 'object', properties: { a: { type: 'string' } } } },
  },
}

describe('resolveRef', () => {
  it('follows $ref and keeps sibling keys such as title', () => {
    const r = resolveRef(schema, schema.properties.name)
    expect(r.title).toBe('Name')
    expect(Object.keys(r.properties)).toEqual(['value', 'status'])
  })
})

describe('isValueBlock', () => {
  it('spots value/status blocks only', () => {
    expect(isValueBlock(resolveRef(schema, schema.properties.name))).toBe(true)
    expect(isValueBlock({ properties: { value: {}, other: {} } })).toBe(false)
  })
})

describe('buildUiSchema', () => {
  it('uses the organisation widget for organisation references', () => {
    const ui = buildUiSchema(schema)
    expect(ui.lead.value['ui:widget']).toBe('organisationWidget')
  })
  it('puts the value first in value blocks, and gives status a plain title', () => {
    const ui = buildUiSchema(schema)
    expect(ui.name['ui:order']).toEqual(['value', 'status', 'source_ids', '*'])
    expect(ui.name.status['ui:title']).toBe('Status')
    expect(ui.name.source_ids).toBeUndefined()
  })
})

describe('buildTabs', () => {
  it('puts unlisted properties in Other for hand-picked types', () => {
    const tabs = buildTabs('project', { properties: { name: {}, mystery: {} } })
    expect(tabs.map(t => t.label)).toEqual(['Overview', 'Other'])
  })
  it('gives each list its own tab for other types', () => {
    const tabs = buildTabs('whatever', schema)
    expect(tabs.map(t => t.label)).toEqual(['General', 'Rows'])
  })
})

describe('tab data', () => {
  it('merges a tab back into the whole record, removing cleared keys', () => {
    const whole = { a: 1, b: 2, c: 3 }
    expect(mergeTabData(whole, ['a', 'b'], { a: 9 })).toEqual({ a: 9, c: 3 })
  })
  it('restricts the schema to the tab keys', () => {
    const s = tabSchema({ required: ['name', 'notes'], properties: schema.properties }, ['name'])
    expect(Object.keys(s.properties)).toEqual(['name'])
    expect(s.required).toEqual(['name'])
  })
})

describe('prune', () => {
  it('removes blanks and the empty objects they leave', () => {
    expect(prune({ a: { value: '' }, b: { value: 'x', status: undefined }, c: null })).toEqual({ b: { value: 'x' } })
  })
  it('drops blank list items but keeps an empty list', () => {
    expect(prune({ rows: [{ a: '' }, { a: 'x' }], none: [] })).toEqual({ rows: [{ a: 'x' }], none: [] })
  })
})

describe('server errors', () => {
  const errors = [
    { path: '/name/value', message: 'Too long' },
    { path: '/outcome_funds/0/id', message: 'This field is required' },
    { path: '/outcome_funds/0/id', message: 'Another' },
    { path: '', message: 'Whole record' },
  ]
  it('reads a JSON pointer, including escaped characters', () => {
    expect(pointerToPath('/a~1b/0/c~0d')).toEqual(['a/b', '0', 'c~d'])
    expect(pointerToPath('')).toEqual([])
  })
  it('builds the tree RJSF shows against each field', () => {
    const tree = errorsToExtraErrors(errors)
    expect(tree.name.value.__errors).toEqual(['Too long'])
    expect(tree.outcome_funds[0].id.__errors).toEqual(['This field is required', 'Another'])
    expect(tree.__errors).toEqual(['Whole record'])
  })
  it('counts errors per top level key', () => {
    expect(countErrorsByTopLevelKey(errors)).toEqual({ name: 1, outcome_funds: 2, '': 1 })
  })
})
