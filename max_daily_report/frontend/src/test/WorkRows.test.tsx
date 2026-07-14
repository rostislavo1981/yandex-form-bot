import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WorkRows } from '../components/WorkRows.tsx'

describe('WorkRows', () => {
  it('renders empty state', () => {
    render(<WorkRows rows={[]} onChange={vi.fn()} />)
    expect(screen.getByText('Нет строк работ')).toBeInTheDocument()
    expect(screen.getByText('+ Добавить')).toBeInTheDocument()
  })
})
