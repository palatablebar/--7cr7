import http from './http'
import type { PartitionRetirement, ReclaimManifest, RetirementActionResult } from '../types/retirement'

export async function fetchReclaimManifest(tableId: number): Promise<ReclaimManifest> {
  const { data } = await http.get(`/tables/${tableId}/reclaim-manifest`)
  return data
}

export async function fetchRetirements(tableId: number): Promise<{ items: PartitionRetirement[] }> {
  const { data } = await http.get(`/tables/${tableId}/retirements`)
  return data
}

export async function createRetirement(
  tableId: number,
  payload: { partition_values: string[]; note?: string },
): Promise<RetirementActionResult> {
  const { data } = await http.post(`/tables/${tableId}/retirements`, payload)
  return data
}

export async function executeRetirement(
  retirementId: number,
  payload: { simulate_failure?: boolean } = {},
): Promise<RetirementActionResult> {
  const { data } = await http.post(`/retirements/${retirementId}/execute`, payload)
  return data
}

export async function restoreRetirement(retirementId: number): Promise<RetirementActionResult> {
  const { data } = await http.post(`/retirements/${retirementId}/restore`)
  return data
}
