import http from './http'
import type { SnapshotDiffResult, TableSnapshot } from '../types/snapshot'
import type { ListResponse } from '../types/api'

export async function fetchSnapshots(tableId: number): Promise<ListResponse<TableSnapshot>> {
  const { data } = await http.get(`/tables/${tableId}/snapshots`)
  return data
}

export async function createSnapshot(tableId: number, note?: string): Promise<{ snapshot: TableSnapshot }> {
  const { data } = await http.post(`/tables/${tableId}/snapshots`, { note })
  return data
}

export async function diffSnapshots(leftId: number, rightId: number): Promise<SnapshotDiffResult> {
  const { data } = await http.get('/snapshots/diff', { params: { left_id: leftId, right_id: rightId } })
  return data
}
