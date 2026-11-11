import http from './http'
import type { CompactPlan, PlanCreateResult } from '../types/plan'

export async function createPlan(payload: {
  table_id: number
  partition_values: string[]
  strategy?: string
  target_file_size_mb?: number | null
  note?: string
}): Promise<PlanCreateResult> {
  const { data } = await http.post('/plans', payload)
  return data
}

export async function fetchPlans(tableId?: number): Promise<{ items: CompactPlan[] }> {
  const { data } = await http.get('/plans', { params: tableId ? { table_id: tableId } : {} })
  return data
}

export async function fetchPlan(planId: number): Promise<{ plan: CompactPlan }> {
  const { data } = await http.get(`/plans/${planId}`)
  return data
}

export async function executePlan(planId: number): Promise<{ job: import('../types/job').CompactJob }> {
  const { data } = await http.post(`/plans/${planId}/execute`)
  return data
}
