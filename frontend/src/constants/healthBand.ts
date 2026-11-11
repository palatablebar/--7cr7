import type { HealthBand } from '../types/table'

export const HEALTH_BAND_LABELS: Record<HealthBand, string> = {
  healthy: '健康',
  watch: '观察',
  degraded: '碎片化',
}

export const HEALTH_BAND_TAG: Record<HealthBand, string> = {
  healthy: 'bp-tag--ok',
  watch: 'bp-tag--watch',
  degraded: 'bp-tag--hot',
}
