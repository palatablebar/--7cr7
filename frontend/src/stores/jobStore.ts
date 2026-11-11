import { defineStore } from 'pinia'
import { fetchJobs, retryJob } from '../api/job'
import type { CompactJob } from '../types/job'

interface JobState {
  items: CompactJob[]
  selectedId: number | null
  loading: boolean
  error: string
}

export const useJobStore = defineStore('jobs', {
  state: (): JobState => ({
    items: [],
    selectedId: null,
    loading: false,
    error: '',
  }),
  getters: {
    selected: (state): CompactJob | undefined =>
      state.items.find((job) => job.id === state.selectedId) ?? state.items[0],
    hasActive: (state): boolean => state.items.some((job) => job.status === 'queued' || job.status === 'running'),
  },
  actions: {
    async load(tableId?: number) {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchJobs(tableId)
        this.items = result.items
        if (this.selectedId === null && result.items.length > 0) {
          this.selectedId = result.items[0].id
        }
        return result.items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '任务加载失败'
        return []
      } finally {
        this.loading = false
      }
    },
    select(jobId: number) {
      this.selectedId = jobId
    },
    async retry(jobId: number) {
      const result = await retryJob(jobId)
      await this.load()
      this.selectedId = result.job.id
      return result.job
    },
  },
})
