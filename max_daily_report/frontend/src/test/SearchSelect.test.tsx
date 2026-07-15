import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchSelect } from '../components/SearchSelect.tsx'
import type { CatalogItem } from '../types/catalogs'

const mockItem: CatalogItem = { id: 1, code: 'OBJ-1', name: 'Объект один' }

describe('SearchSelect', () => {
  it('renders input and shows results after typing', async () => {
    const searchFn = vi.fn().mockResolvedValue([mockItem])
    render(
      <SearchSelect
        label="Объект"
        value={null}
        onChange={vi.fn()}
        searchFn={searchFn}
      />,
    )

    const input = screen.getByLabelText('Объект')
    await userEvent.type(input, 'об')

    await waitFor(() => expect(searchFn).toHaveBeenCalled())
    expect(await screen.findByText('Объект один')).toBeInTheDocument()
    expect(screen.getByText('OBJ-1')).toBeInTheDocument()
  })

  it('calls onChange when item selected and clears stage', async () => {
    const onChange = vi.fn()
    const searchFn = vi.fn().mockResolvedValue([mockItem])
    render(
      <SearchSelect
        label="Объект"
        value={null}
        onChange={onChange}
        searchFn={searchFn}
      />,
    )

    const input = screen.getByLabelText('Объект')
    await userEvent.type(input, 'об')
    const option = await screen.findByText('Объект один')
    await userEvent.click(option)

    expect(onChange).toHaveBeenCalledWith(mockItem)
  })
})
