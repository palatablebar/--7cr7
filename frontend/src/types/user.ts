export type UserRole = 'admin' | 'engineer' | 'analyst'

export interface QuotaSnapshot {
  daily_plan_quota: number
  plan_used: number
  quota_remaining: number
  plan_used_date: string | null
  window_max: number
  window_seconds: number
}

export interface User {
  id: number
  email: string
  display_name: string
  role: UserRole
  daily_plan_quota: number
  plan_used: number
  quota_remaining: number
  quota?: QuotaSnapshot
}

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: '平台管理员',
  engineer: '数据工程师',
  analyst: '分析师（只读）',
}
