import {
  buildTabs,
  buildUiSchema,
  countErrorsByTopLevelKey,
  errorsToExtraErrors,
  isValueBlock,
  currentWarnings,
  mergeTabData,
  orderedKeys,
  pathToPointer,
  pointerToPath,
  prune,
  resolveRef,
  tabSchema,
  valueAtPath,
  warningsByPointer,
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

describe('lists of options', () => {
  const schema = {
    type: 'object',
    properties: {
      kind: { type: 'string', enum: ['a', 'b'] },
      status: { type: 'string', enum: ['PUBLIC', 'PRIVATE'] },
      note: { type: 'string' },
      rows: {
        type: 'array',
        items: { type: 'object', properties: { kind: { type: 'string', enum: ['x'] }, status: { type: 'string', enum: ['PUBLIC'] } } },
      },
    },
  }

  it('lets you type your own value, except for a status', () => {
    const ui = buildUiSchema(schema)
    expect(ui.kind['ui:widget']).toBe('choiceOrOtherWidget')
    expect(ui.status).toBeUndefined()
    expect(ui.note).toBeUndefined()
    expect(ui.rows.items.kind['ui:widget']).toBe('choiceOrOtherWidget')
    expect(ui.rows.items.status).toBeUndefined()
  })
})

describe('warnings', () => {
  it('turns a path into a pointer and back', () => {
    expect(pathToPointer(['a', 0, 'b/c'])).toBe('/a/0/b~1c')
    expect(pathToPointer([])).toBe('')
    expect(pointerToPath(pathToPointer(['a', 0, 'b/c']))).toEqual(['a', '0', 'b/c'])
  })

  it('finds the value at a pointer', () => {
    const data = { a: [{ b: 'x' }], n: null }
    expect(valueAtPath(data, '/a/0/b')).toBe('x')
    expect(valueAtPath(data, '/a/3/b')).toBeUndefined()
    expect(valueAtPath(data, '/n/x')).toBeUndefined()
    expect(valueAtPath(data, '')).toBe(data)
  })

  it('keeps a warning only while the value it is about is unchanged', () => {
    const warnings = [
      { path: '/amount', message: 'not a number', value: 'TBD' },
      { path: '/rows', message: 'too short', value: [] },
    ]
    expect(currentWarnings(warnings, { amount: 'TBD', rows: [] })).toHaveLength(2)
    expect(currentWarnings(warnings, { amount: '12', rows: [] })).toEqual([warnings[1]])
    expect(currentWarnings(warnings, { rows: [{}] })).toEqual([warnings[0]].filter(() => false))
    expect(currentWarnings(undefined, {})).toEqual([])
  })

  it('groups the messages by where they are, and counts them by top level key', () => {
    const warnings = [
      { path: '/a/0/x', message: 'one' },
      { path: '/a/0/x', message: 'two' },
      { path: '/b', message: 'three' },
    ]
    expect(warningsByPointer(warnings)).toEqual({ '/a/0/x': ['one', 'two'], '/b': ['three'] })
    expect(countErrorsByTopLevelKey(warnings)).toEqual({ a: 2, b: 1 })
  })
})
