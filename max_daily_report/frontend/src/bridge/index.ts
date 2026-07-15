export interface WebApp {
  initData: string
  initDataUnsafe: {
    user?: {
      id: number | string
      first_name?: string
      last_name?: string
      username?: string
    }
  }
  ready: () => void
  close: () => void
  expand: () => void
}

declare global {
  interface Window {
    WebApp?: WebApp
  }
}

export function getWebApp(): WebApp | null {
  if (typeof window === 'undefined') {
    return null
  }
  return window.WebApp ?? null
}

export function notifyReady(): void {
  getWebApp()?.ready()
}

export function getInitData(): string {
  return getWebApp()?.initData ?? ''
}

export function getInitDataUnsafe(): WebApp['initDataUnsafe'] | null {
  return getWebApp()?.initDataUnsafe ?? null
}
