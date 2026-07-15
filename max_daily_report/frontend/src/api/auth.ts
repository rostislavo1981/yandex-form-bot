import { api } from './client'
import type { User } from '../types'

export interface AuthResponse {
  user: User
}

export async function verifyInitData(): Promise<User> {
  const response = await api.get<AuthResponse>('/api/auth/me')
  return response.user
}
