export function formatBytes(bytes: number | null | undefined, digits = 1): string {
  const value = Number(bytes ?? 0)
  if (Math.abs(value) < 1024) return `${Math.round(value)}B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let scaled = value / 1024
  let unit = units[0]
  for (let index = 0; index < units.length; index += 1) {
    unit = units[index]
    if (Math.abs(scaled) < 1024 || index === units.length - 1) break
    scaled /= 1024
  }
  return `${scaled.toFixed(digits)}${unit}`
}

export function formatMb(bytes: number | null | undefined, digits = 1): string {
  return `${(Number(bytes ?? 0) / (1024 * 1024)).toFixed(digits)} MB`
}

export function formatCount(value: number | null | undefined): string {
  return Number(value ?? 0).toLocaleString('zh-CN')
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  return `${Number(value ?? 0).toFixed(digits)}%`
}
