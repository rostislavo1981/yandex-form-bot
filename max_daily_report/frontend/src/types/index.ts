export interface User {
  id: number
  max_user_id: string
  full_name: string
  role: 'responsible' | 'manager' | 'admin'
}

export interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
}

export interface ApiError {
  detail?: string | Record<string, unknown>
  error?: string
}
