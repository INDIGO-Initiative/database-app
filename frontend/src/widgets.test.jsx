import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { widgets } from './widgets'

const ChoiceOrOther = widgets.choiceOrOtherWidget
const options = { enumOptions: [{ value: 'a', label: 'a' }, { value: 'b', label: 'b' }] }

function setup(value) {
  const onChange = vi.fn()
  render(<ChoiceOrOther id="f" value={value} onChange={onChange} options={options} />)
  return onChange
}

describe('a list of options you can add to', () => {
  it('shows a listed value in the dropdown, with no text box', () => {
    setup('b')
    expect(screen.getByRole('combobox')).toHaveValue('b')
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('offers every option, a blank one, and Other', () => {
    setup(undefined)
    const labels = screen.getAllByRole('option').map(o => o.textContent)
    expect(labels).toEqual(['', 'a', 'b', 'Other (type your own)…'])
    expect(screen.getByRole('combobox')).toHaveValue('')
  })

  it('shows a value that is not in the list as Other, with the value in a text box', () => {
    setup('senior loan')
    expect(screen.getByRole('combobox')).toHaveValue('__other__')
    expect(screen.getByRole('textbox', { name: 'Your own value' })).toHaveValue('senior loan')
  })

  it('shows a text box on choosing Other, and passes on what is typed', async () => {
    const onChange = setup(undefined)
    await userEvent.selectOptions(screen.getByRole('combobox'), '__other__')
    const box = screen.getByRole('textbox', { name: 'Your own value' })
    expect(onChange).not.toHaveBeenCalled()
    await userEvent.type(box, 'x')
    expect(onChange).toHaveBeenLastCalledWith('x')
  })

  it('passes on a listed choice, and undefined when the blank option is chosen', async () => {
    const onChange = setup('b')
    await userEvent.selectOptions(screen.getByRole('combobox'), 'a')
    expect(onChange).toHaveBeenLastCalledWith('a')
    await userEvent.selectOptions(screen.getByRole('combobox'), '')
    expect(onChange).toHaveBeenLastCalledWith(undefined)
  })

  it('is disabled when the field is read only', () => {
    render(<ChoiceOrOther id="f" value="zzz" onChange={() => {}} options={options} readonly />)
    expect(screen.getByRole('combobox')).toBeDisabled()
    expect(screen.getByRole('textbox')).toBeDisabled()
  })
})
