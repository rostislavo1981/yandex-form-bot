import { useEffect, useState } from 'react'
import { verifyInitData } from '../api/auth'
import { notifyReady } from '../bridge'
import type { AuthState } from '../types'

export function useAuth(): AuthState {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    let cancelled = false

    async function init() {
      try {
        notifyReady()
        const user = await verifyInitData()
        if (!cancelled) {
          setState({ user, loading: false, error: null })
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Ошибка авторизации'
          setState({ user: null, loading: false, error: message })
        }
      }
    }

    void init()
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
