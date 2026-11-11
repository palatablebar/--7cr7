import type { CompactJob } from '../types/job'

export const JOB_STATUS_LABELS: Record<CompactJob['status'], string> = {
  queued: '排队中',
  running: '执行中',
  succeeded: '已完成',
  failed: '失败',
}

export const ACTIVE_JOB_STATUSES: CompactJob['status'][] = ['queued', 'running']

export function isActiveJob(status: CompactJob['status']): boolean {
  return ACTIVE_JOB_STATUSES.includes(status)
}
