import { defineStore } from 'pinia'
import { createSnapshot, diffSnapshots, fetchSnapshots } from '../api/snapshot'
import type { SnapshotDiffResult, TableSnapshot } from '../types/snapshot'

interface SnapshotState {
  items: TableSnapshot[]
  leftId: number | null
  rightId: number | null
  diff: SnapshotDiffResult | null
  loading: boolean
  diffing: boolean
  error: string
}

export const useSnapshotStore = defineStore('snapshots', {
  state: (): SnapshotState => ({
    items: [],
    leftId: null,
    rightId: null,
    diff: null,
    loading: false,
    diffing: false,
    error: '',
  }),
  getters: {
    latest: (state): TableSnapshot | undefined => state.items[0],
  },
  actions: {
    async load(tableId: number) {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchSnapshots(tableId)
        this.items = result.items
        // default comparison: previous version -> latest version
        if (result.items.length >= 2) {
          this.rightId = result.items[0].id
          this.leftId = result.items[1].id
        } else if (result.items.length === 1) {
          this.rightId = result.items[0].id
          this.leftId = null
        }
        this.diff = null
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '快照加载失败'
      } finally {
        this.loading = false
      }
    },
    async compare() {
      if (this.leftId === null || this.rightId === null) return null
      this.diffing = true
      this.error = ''
      try {
        this.diff = await diffSnapshots(this.leftId, this.rightId)
        return this.diff
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '快照对比失败'
        throw error
      } finally {
        this.diffing = false
      }
    },
    async create(tableId: number, note?: string) {
      const result = await createSnapshot(tableId, note)
      await this.load(tableId)
      return result.snapshot
    },
  },
})
