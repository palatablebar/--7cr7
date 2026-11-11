export type RetirementStatus = 'retiring' | 'retired' | 'failed' | 'restored'

export interface ReclaimFile {
  path: string
  size_bytes: number
  row_count: number
  checksum: string
  snapshot_versions?: number[]
}

export interface ReclaimItem {
  partition_value: string
  lifecycle: PartitionLifecycle
  file_count: number
  protected_count: number
  reclaimable_count: number
  protected_bytes: number
  reclaimable_bytes: number
  invariant_ok: boolean
  protected_files: ReclaimFile[]
  reclaimable_files: ReclaimFile[]
  files_truncated: boolean
}

export type PartitionLifecycle = 'active' | 'retiring' | 'retired'

export interface ReclaimManifest {
  table_id: number
  table_fq_name: string
  partition_key: string
  retained_snapshot_versions: number[]
  snapshot_count: number
  items: ReclaimItem[]
  totals: {
    file_count: number
    protected_count: number
    reclaimable_count: number
    protected_bytes: number
    reclaimable_bytes: number
    invariant_ok: boolean
  }
}

export interface RetirementPartitionResult {
  partition_value: string
  reclaimed_count: number
  reclaimed_bytes: number
  protected_remaining: number
  skipped_protected: string[]
  missing: string[]
}

export interface RetirementResult {
  ok: boolean
  partitions?: RetirementPartitionResult[]
  reclaimed_file_count?: number
  reclaimed_bytes?: number
  executed_at?: string | null
  restored_partitions?: string[]
  restored_at?: string | null
  previous_status?: string
}

export interface PartitionRetirement {
  id: number
  table_id: number
  table_fq_name: string | null
  partition_key: string
  status: RetirementStatus
  partition_values: string[]
  protected_file_count: number
  reclaimable_file_count: number
  reclaimable_bytes: number
  fingerprint: string
  note: string | null
  failure_reason: string | null
  result: RetirementResult | null
  created_by: number | null
  created_by_name: string | null
  created_at: string | null
  executed_at: string | null
  finished_at: string | null
  items?: ReclaimItem[]
}

export interface RetirementActionResult {
  retirement: PartitionRetirement
  idempotent: boolean
  ok?: boolean
}
