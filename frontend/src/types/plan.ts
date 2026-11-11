export interface PlanFile {
  path: string
  size_bytes: number
  size_mb: number
  row_count: number
  checksum: string
}

export interface PlanGroup {
  group_id: string
  partition_value: string
  action: 'rewrite' | 'carry'
  risk: 'normal' | 'hot'
  defer_recommended: boolean
  file_count: number
  packed_size_bytes: number
  packed_size_mb: number
  fill_ratio: number
  target_size_mb: number
  saved_files: number
  output_file: string
  output_size_bytes: number
  output_rows: number
  files: PlanFile[]
}

export interface CostLedger {
  bandwidth_mb_per_s: number
  per_file_overhead_s: number
  unit_cost_per_gb: number
  cost_per_file_day: number
  rewrite_gb: number
  transfer_seconds: number
  overhead_seconds: number
  est_duration_seconds: number
  est_cost_yuan: number
  monthly_saving_yuan: number
  payback_days: number | null
}

export interface RiskFlag {
  partition_value: string
  code: string
  severity: 'warn' | 'info'
  message: string
}

export interface CompactPlan {
  id: number
  table_id: number
  table_fq_name: string | null
  partition_key: string
  strategy: string
  status: 'draft' | 'executing' | 'completed' | 'failed'
  partition_values: string[]
  risk_flags: RiskFlag[]
  cost: CostLedger
  candidate_file_count: number
  group_count: number
  expected_output_files: number
  saved_files: number
  rewritten_bytes: number
  est_duration_seconds: number
  est_cost_yuan: number
  savings_pct: number
  fingerprint: string
  note: string | null
  created_by: number | null
  created_by_name: string | null
  created_at: string | null
  groups?: PlanGroup[]
  latest_job: { id: number; status: string; progress: number } | null
}

export interface PlanCreateResult {
  plan: CompactPlan
  idempotent: boolean
  previous_plan: { id: number; created_at: string | null; status: string } | null
  quota: {
    daily_plan_quota: number
    plan_used: number
    quota_remaining: number
    plan_used_date: string | null
    window_max: number
    window_seconds: number
  }
  candidate_files: number
  empty_partitions: string[]
}
