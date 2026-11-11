import { defineStore } from 'pinia'
import { fetchMe, login as apiLogin } from '../api/auth'
import type { QuotaSnapshot, User, UserRole } from '../types/user'
import { TOKEN_KEY } from '../utils/request'

interface AuthState {
  token: string
  user: User | null
  quota: QuotaSnapshot | null
  loading: boolean
  error: string
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY) ?? '',
    user: null,
    quota: null,
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state): boolean => Boolean(state.token),
    role: (state): UserRole => (state.user?.role ?? 'analyst') as UserRole,
    canWrite: (state): boolean => state.user?.role === 'admin' || state.user?.role === 'engineer',
    isAdmin: (state): boolean => state.user?.role === 'admin',
    isAnalyst: (state): boolean => state.user?.role === 'analyst',
    displayName: (state): string => state.user?.display_name ?? '',
    quotaRemaining: (state): number => state.quota?.quota_remaining ?? state.user?.quota_remaining ?? 0,
  },
  actions: {
    async login(email: string, password: string) {
      this.loading = true
      this.error = ''
      try {
        const result = await apiLogin(email, password)
        this.token = result.token
        this.user = result.user
        this.quota = result.user.quota ?? null
        localStorage.setItem(TOKEN_KEY, result.token)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async restore() {
      if (!this.token) return
      try {
        const result = await fetchMe()
        this.user = result.user
        this.quota = result.user.quota ?? null
      } catch {
        this.logout()
      }
    },
    setQuota(quota: QuotaSnapshot | null) {
      this.quota = quota
    },
    logout() {
      this.token = ''
      this.user = null
      this.quota = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
