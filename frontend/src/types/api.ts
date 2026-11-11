export interface ApiError {
  code: string
  message: string
  detail?: unknown
  requestId?: string | null
  status?: number
}

export interface ListResponse<T> {
  items: T[]
  total?: number
  offset?: number
  limit?: number
}
