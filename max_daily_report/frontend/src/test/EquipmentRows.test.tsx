import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EquipmentRows } from '../components/EquipmentRows.tsx'

describe('EquipmentRows', () => {
  it('renders empty state', () => {
    render(<EquipmentRows rows={[]} onChange={vi.fn()} />)
    expect(screen.getByText('Нет строк техники')).toBeInTheDocument()
    expect(screen.getByText('+ Добавить')).toBeInTheDocument()
  })
})
