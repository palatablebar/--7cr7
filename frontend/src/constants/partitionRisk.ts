import type { PartitionRisk } from '../types/table'

export const PARTITION_RISK_LABELS: Record<PartitionRisk, string> = {
  normal: '可整理',
  hot: '最新分区·写入中',
}
