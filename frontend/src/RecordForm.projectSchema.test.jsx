import { useState } from 'react'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecordForm from './RecordForm'
import schema from '../../indigo/jsonschema/cached_information/project.json.compiled_jsonschema.json'

// The real project schema, to check the form copes with how the data standard is written (references, value blocks...)
const path = '/investments/0/investment_type/value'
const warnings = [{ path, message: 'Investment type: "senior loan" is not one of the options', value: 'senior loan' }]

function Harness() {
  const [data, setData] = useState({ investments: [{ investment_type: { value: 'senior loan' } }] })
  return <RecordForm typeId="project" schema={schema} data={data} onChange={setData} warnings={warnings} />
}

describe('the project form', () => {
  it('shows a value that is not in the list, with its warning, and counts it on the tab', async () => {
    render(<Harness />)
    const tab = screen.getByRole('tab', { name: /Service & investment/ })
    expect(within(tab).getByTitle(/do not match the data standard/)).toHaveTextContent('1')
    await userEvent.click(tab)
    expect(screen.getByText('Investment type: "senior loan" is not one of the options')).toBeInTheDocument()
    const own = screen.getByRole('textbox', { name: 'Your own value' })
    expect(own).toHaveValue('senior loan')
    // The dropdown beside it still offers the real options
    const options = [...own.closest('.choice-or-other').querySelector('select').options].map(o => o.textContent)
    expect(options).toContain('Other (type your own)…')
    expect(options.length).toBeGreaterThan(3)
  })

  it('clears the warning when a listed option is chosen instead', async () => {
    render(<Harness />)
    await userEvent.click(screen.getByRole('tab', { name: /Service & investment/ }))
    const select = screen.getByRole('textbox', { name: 'Your own value' }).closest('.choice-or-other').querySelector('select')
    const listed = [...select.options].find(o => o.value !== '' && o.value !== '__other__')
    await userEvent.selectOptions(select, listed.value)
    expect(screen.queryByText('Investment type: "senior loan" is not one of the options')).toBeNull()
    expect(screen.queryByRole('textbox', { name: 'Your own value' })).toBeNull()
  })

  it('keeps a status as a plain dropdown', async () => {
    render(<Harness />)
    await userEvent.click(screen.getByRole('tab', { name: /Overview/ }))
    const statuses = [...document.querySelectorAll('select[id$="_status"]')]
    expect(statuses.length).toBeGreaterThan(0)
    for (const status of statuses) {
      expect([...status.options].map(o => o.textContent)).not.toContain('Other (type your own)…')
    }
  })
})
