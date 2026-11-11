import http from './http'
import type { DataFile, LakeTable, PartitionSpec, TableSummary } from '../types/table'
import type { ListResponse } from '../types/api'

export async function fetchTables(): Promise<{ items: LakeTable[]; summary: TableSummary }> {
  const { data } = await http.get('/tables')
  return data
}

export async function fetchTable(tableId: number): Promise<{ table: LakeTable; partitions: PartitionSpec[] }> {
  const { data } = await http.get(`/tables/${tableId}`)
  return data
}

export async function fetchPartitions(tableId: number): Promise<ListResponse<PartitionSpec>> {
  const { data } = await http.get(`/tables/${tableId}/partitions`)
  return data
}

export interface FileQuery {
  partition_value?: string
  size_lt_mb?: number
  size_gte_mb?: number
  sort?: string
  offset?: number
  limit?: number
}

export async function fetchFiles(tableId: number, query: FileQuery = {}): Promise<ListResponse<DataFile>> {
  const { data } = await http.get(`/tables/${tableId}/files`, { params: query })
  return data
}

export async function createTable(payload: {
  db_name: string
  table_name: string
  partition_key: string
  target_file_size_mb: number
  small_file_threshold_mb: number
  description?: string
}): Promise<{ table: LakeTable }> {
  const { data } = await http.post('/tables', payload)
  return data
}
