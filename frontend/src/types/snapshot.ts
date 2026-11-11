export interface VerificationInfo {
  baseline?: boolean
  compared_to_version?: number | null
  rows_before?: number
  rows_after?: number
  row_conserved?: boolean
  row_delta?: number
  checksum_ok?: boolean
  conservation_ok?: boolean
  added_count?: number
  removed_count?: number
  changed_count?: number
  checksum_mismatches?: string[]
  file_count_delta?: number
  detail_truncated?: boolean
}

export interface TableSnapshot {
  id: number
  table_id: number
  table_fq_name: string | null
  version: number
  file_count: number
  total_rows: number
  total_bytes: number
  checksum: string
  note: string | null
  job_id: number | null
  created_at: string | null
  verification?: VerificationInfo
}

export interface ManifestEntry {
  path: string
  size_bytes: number
  rows: number
  checksum: string | null
  partition: string | null
}

export interface ChangedEntry {
  path: string
  before: ManifestEntry
  after: ManifestEntry
}

export interface SnapshotDiff {
  added: ManifestEntry[]
  removed: ManifestEntry[]
  changed: ChangedEntry[]
  added_count: number
  removed_count: number
  changed_count: number
  file_count_before: number
  file_count_after: number
  file_count_delta: number
  size_before_bytes: number
  size_after_bytes: number
  rows_before: number
  rows_after: number
  row_delta: number
  row_conserved: boolean
  checksum_mismatches: string[]
  checksum_ok: boolean
  conservation_ok: boolean
  detail_truncated: boolean
}

export interface SnapshotDiffResult {
  left: TableSnapshot
  right: TableSnapshot
  diff: SnapshotDiff
}
