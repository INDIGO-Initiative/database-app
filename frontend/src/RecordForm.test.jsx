import { useState } from 'react'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecordForm from './RecordForm'
import { prune } from './utils'

const schema = {
  type: 'object',
  properties: {
    amount: { type: 'object', title: 'Amount', properties: { value: { type: 'number', title: 'Amount' } } },
    kind: { type: 'string', title: 'Kind', enum: ['a', 'b'] },
    status: { type: 'string', title: 'Status', enum: ['PUBLIC', 'PRIVATE'] },
  },
}

function Harness({ initial, warnings, errors }) {
  const [data, setData] = useState(initial)
  return <RecordForm typeId="other" schema={schema} data={data} onChange={setData} warnings={warnings} errors={errors} />
}

const warnings = [
  { path: '/amount/value', message: 'Amount: "TBD" is not of type number', value: 'TBD' },
  { path: '/kind', message: 'Kind: "zz" is not one of the options', value: 'zz' },
]

describe('warnings on the form', () => {
  it('shows each warning under its field, and counts them on the tab', () => {
    render(<Harness initial={{ amount: { value: 'TBD' }, kind: 'zz' }} warnings={warnings} />)
    expect(screen.getByText('Amount: "TBD" is not of type number')).toBeInTheDocument()
    expect(screen.getByText('Kind: "zz" is not one of the options')).toBeInTheDocument()
    const tab = screen.getByRole('tab', { name: /General/ })
    expect(within(tab).getByTitle(/do not match the data standard/)).toHaveTextContent('2')
  })

  it('shows no warnings, and no badge, when there are none', () => {
    render(<Harness initial={{ amount: { value: 5 } }} warnings={[]} />)
    expect(screen.queryByTitle(/do not match the data standard/)).toBeNull()
    expect(document.querySelector('.warning-detail')).toBeNull()
  })

  it('drops a warning once its value is changed', async () => {
    render(<Harness initial={{ amount: { value: 'TBD' }, kind: 'zz' }} warnings={warnings} />)
    const amount = document.querySelector('.value-block input')
    await userEvent.clear(amount)
    await userEvent.type(amount, '12')
    expect(screen.queryByText('Amount: "TBD" is not of type number')).toBeNull()
    // The warning about the other field stays
    expect(screen.getByText('Kind: "zz" is not one of the options')).toBeInTheDocument()
    const tab = screen.getByRole('tab', { name: /General/ })
    expect(within(tab).getByTitle(/do not match the data standard/)).toHaveTextContent('1')
  })

  it('shows a value that is not in a list of options, and keeps it unless it is changed', async () => {
    render(<Harness initial={{ kind: 'zz' }} warnings={[]} />)
    expect(screen.getByRole('textbox', { name: 'Your own value' })).toHaveValue('zz')
  })

  it('lets a status be one of its options only', () => {
    render(<Harness initial={{ status: 'PUBLIC' }} warnings={[]} />)
    const status = screen.getByLabelText('Status')
    expect(status.tagName).toBe('SELECT')
    // RJSF's own dropdown: just the options, with no "Other" and no text box
    expect([...status.options].map(o => o.textContent)).toEqual(['', 'PUBLIC', 'PRIVATE'])
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('still shows the errors the server found, in red, apart from the warnings', () => {
    render(
      <Harness
        initial={{ kind: 'zz' }}
        warnings={[]}
        errors={[{ path: '/amount/value', message: 'Amount: must be a number' }]}
      />,
    )
    expect(screen.getByText('Amount: must be a number')).toBeInTheDocument()
    const tab = screen.getByRole('tab', { name: /General/ })
    expect(within(tab).getByTitle('Problems found when saving')).toHaveTextContent('1')
    expect(prune({ kind: 'zz' })).toEqual({ kind: 'zz' })
  })
})
