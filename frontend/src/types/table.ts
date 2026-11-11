export type HealthBand = 'healthy' | 'watch' | 'degraded'
export type PartitionRisk = 'normal' | 'hot'

export interface LakeTable {
  id: number
  db_name: string
  table_name: string
  fq_name: string
  partition_key: string
  file_format: string
  target_file_size_mb: number
  small_file_threshold_mb: number
  status: 'active' | 'paused'
  description: string | null
  owner_name: string | null
  created_at: string | null
  partition_count: number
  file_count: number
  small_file_count: number
  total_size_bytes: number
  avg_file_size_bytes: number
  avg_health_score: number
  avg_health_band: HealthBand
  hot_partition_count: number
  pending_partition_count: number
  retiring_partition_count: number
  retired_partition_count: number
  reclaimable_file_count: number
  small_file_bytes: number
  latest_plan_id: number | null
  latest_plan_status: string | null
  partitions: PartitionBrief[]
}

export interface PartitionBrief {
  id: number
  partition_value: string
  file_count: number
  small_file_count: number
  health_score: number
  health_band: HealthBand
  risk: PartitionRisk
  lifecycle: 'active' | 'retiring' | 'retired'
}

export interface TableSummary {
  table_count: number
  file_count: number
  small_file_count: number
  total_size_bytes: number
  pending_partition_count: number
  hot_partition_count: number
  reclaimable_file_count: number
  avg_health_score: number
}

export interface PartitionSpec {
  id: number
  partition_value: string
  file_count: number
  small_file_count: number
  total_size_bytes: number
  total_rows: number
  avg_file_size_bytes: number
  health_score: number
  health_band: HealthBand
  risk: PartitionRisk
  lifecycle: 'active' | 'retiring' | 'retired'
  last_compacted_at: string | null
  target_file_size_mb: number
}

export interface DataFile {
  id: number
  path: string
  file_name: string
  partition_value: string
  size_bytes: number
  size_mb: number
  row_count: number
  checksum: string
  file_format: string
  write_source: string
  is_small: boolean
  created_at: string | null
}
