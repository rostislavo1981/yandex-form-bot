import type { ApiError } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function getInitData(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  const webApp = window.WebApp
  if (webApp?.initData) {
    return webApp.initData
  }
  // Dev fallback: allowed only when backend explicitly enables dev auth.
  // Production local builds set VITE_ALLOW_DEV_AUTH so Docker smoke tests work.
  if (import.meta.env.VITE_ALLOW_DEV_AUTH === 'true') {
    return 'dev'
  }
  return ''
}

function getAdminPassword(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.localStorage.getItem('admin_password') ?? ''
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  idempotencyKey?: string,
): Promise<T> {
  const initData = getInitData()
  const adminPassword = getAdminPassword()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (adminPassword) {
    headers['X-Admin-Password'] = adminPassword
  } else if (initData) {
    headers['X-Init-Data'] = initData
  }
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    let parsed: ApiError = {}
    try {
      parsed = (await response.json()) as ApiError
    } catch {
      // ignore parse failure
    }
    const message =
      typeof parsed.detail === 'string'
        ? parsed.detail
        : parsed.error ?? `HTTP ${response.status}`
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }
  const contentType = response.headers?.get?.('content-type') || ''
  if (contentType.includes('application/json')) {
    return (await response.json()) as T
  }
  return undefined as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body: unknown, idempotencyKey?: string) =>
    request<T>('POST', path, body, idempotencyKey),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  delete: <T = void>(path: string) => request<T>('DELETE', path),
}
