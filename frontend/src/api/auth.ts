import http from './http'
import type { QuotaSnapshot, User } from '../types/user'

export async function login(email: string, password: string): Promise<{ token: string; user: User }> {
  const { data } = await http.post('/auth/login', { email, password })
  return data
}

export async function fetchMe(): Promise<{ user: User & { quota: QuotaSnapshot } }> {
  const { data } = await http.get('/auth/me')
  return data
}
