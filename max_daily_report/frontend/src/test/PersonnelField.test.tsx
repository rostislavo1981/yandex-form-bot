import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PersonnelField } from '../components/PersonnelField.tsx'

describe('PersonnelField', () => {
  it('does not allow negative values', async () => {
    const onChange = vi.fn()
    render(<PersonnelField value={{ itr: 0, internal: 0, external: 0 }} onChange={onChange} />)

    const itrInput = screen.getByLabelText('ИТР')
    await userEvent.type(itrInput, '-1')

    expect(onChange).toHaveBeenCalled()
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0]
    expect(lastCall.itr).toBeGreaterThanOrEqual(0)
  })
})
