import { describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'

const originalFetch = globalThis.fetch

describe('api client', () => {
  it('sends X-Init-Data header from window.WebApp.initData', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ user: { id: 1 } }),
    } as Response)
    globalThis.fetch = fetchSpy
    globalThis.window.WebApp = {
      initData: 'test-init-data',
      initDataUnsafe: {},
      ready: vi.fn(),
      close: vi.fn(),
      expand: vi.fn(),
    }

    await api.get('/api/auth/me')

    const request = fetchSpy.mock.calls[0] as [string, RequestInit | undefined]
    expect(request[1]?.headers).toMatchObject({
      'X-Init-Data': 'test-init-data',
      'Content-Type': 'application/json',
    })
    globalThis.fetch = originalFetch
  })

  it('throws on HTTP error with parsed detail', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'validation failed' }),
    } as Response)
    globalThis.window.WebApp = undefined

    await expect(api.get('/api/reports')).rejects.toThrow('validation failed')
  })
})
