import { onBeforeUnmount, ref, watch } from 'vue'
import { isActiveJob } from '../constants/jobStatus'
import type { CompactJob } from '../types/job'

/**
 * Polls the job list while any job is queued/running. The screenshot driver
 * relies on this to observe the worker progressing from running -> succeeded.
 */
export function useJobPolling(load: () => Promise<CompactJob[]>, intervalMs = 1500) {
  const timer = ref<number | null>(null)
  const active = ref(false)

  function stop() {
    if (timer.value !== null) {
      window.clearInterval(timer.value)
      timer.value = null
    }
    active.value = false
  }

  function start() {
    if (timer.value !== null) return
    active.value = true
    timer.value = window.setInterval(async () => {
      try {
        const jobs = await load()
        if (!jobs.some((job) => isActiveJob(job.status))) stop()
      } catch {
        stop()
      }
    }, intervalMs)
  }

  watch(active, (value) => {
    if (!value) stop()
  })

  onBeforeUnmount(stop)

  return { active, start, stop }
}
