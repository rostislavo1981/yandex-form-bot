import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Layout } from '../components/Layout.tsx'
import * as authApi from '../api/auth'

const mockUser = {
  id: 1,
  max_user_id: 'max-1',
  full_name: 'Test User',
  role: 'responsible' as const,
}

describe('Layout', () => {
  it('renders user info and nav links after auth', async () => {
    vi.spyOn(authApi, 'verifyInitData').mockResolvedValue(mockUser)
    globalThis.window.WebApp = {
      initData: 'test-init-data',
      initDataUnsafe: { user: { id: 1 } },
      ready: vi.fn(),
      close: vi.fn(),
      expand: vi.fn(),
    }

    render(
      <MemoryRouter initialEntries={['/report']}>
        <Layout />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Test User')).toBeInTheDocument()
    expect(screen.getByText('Заполнить')).toBeInTheDocument()
    expect(screen.getByText('Мои отчёты')).toBeInTheDocument()
    expect(screen.getByText('Табель')).toBeInTheDocument()
    expect(screen.queryByText('Статус')).not.toBeInTheDocument()
  })

  it('shows status link for managers', async () => {
    vi.spyOn(authApi, 'verifyInitData').mockResolvedValue({ ...mockUser, role: 'manager' as const })
    globalThis.window.WebApp = {
      initData: 'test-init-data',
      initDataUnsafe: { user: { id: 1 } },
      ready: vi.fn(),
      close: vi.fn(),
      expand: vi.fn(),
    }

    render(
      <MemoryRouter initialEntries={['/report']}>
        <Layout />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Test User')).toBeInTheDocument()
    expect(screen.getByText('Статус')).toBeInTheDocument()
  })

  it('shows error on auth failure', async () => {
    vi.spyOn(authApi, 'verifyInitData').mockRejectedValue(new Error('Forbidden'))
    globalThis.window.WebApp = undefined

    render(
      <MemoryRouter initialEntries={['/report']}>
        <Layout />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Forbidden')).toBeInTheDocument()
  })
})
