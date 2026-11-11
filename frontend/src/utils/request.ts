import axios, { type AxiosInstance } from 'axios'
import type { ApiError } from '../types/api'
import { ERROR_MESSAGES } from '../constants/errorCodes'

export const TOKEN_KEY = 'lakepack_token'

export function createHttp(baseURL = '/api'): AxiosInstance {
  const instance = axios.create({ baseURL, timeout: 60000 })

  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      const status: number | undefined = error.response?.status
      const data = error.response?.data ?? {}
      const code: string = data.code ?? 'LAKE-5000'
      const normalized: ApiError = {
        code,
        message: data.message ?? ERROR_MESSAGES[code] ?? '网络请求失败，请稍后重试',
        detail: data.detail,
        requestId: data.request_id ?? error.response?.headers?.['x-request-id'] ?? null,
        status,
      }
      if (status === 401) {
        localStorage.removeItem(TOKEN_KEY)
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
      return Promise.reject(normalized)
    },
  )
  return instance
}
