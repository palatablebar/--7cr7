export function formatTime(value: string | null | undefined): string {
  if (!value) return '—'
  return value.replace('T', ' ').slice(0, 19)
}

export function secondsLabel(seconds: number | null | undefined): string {
  const value = Number(seconds ?? 0)
  if (value < 60) return `${value.toFixed(1)}s`
  const minutes = Math.floor(value / 60)
  const rest = Math.round(value % 60)
  return `${minutes}m ${rest}s`
}
