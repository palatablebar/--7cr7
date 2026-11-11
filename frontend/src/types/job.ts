export interface CompactJob {
  id: number
  plan_id: number
  table_id: number
  table_fq_name: string | null
  partition_values: string[]
  strategy: string | null
  fingerprint: string | null
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  progress: number
  groups_total: number
  processed_groups: number
  rewritten_files: number
  produced_files: number
  bytes_written: number
  rows_before: number
  rows_after: number
  row_conserved: boolean
  snapshot_id: number | null
  celery_task_id: string | null
  failure_reason: string | null
  triggered_by: number | null
  triggered_by_name: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string | null
  est_duration_seconds: number | null
}
