import { defineStore } from 'pinia'
import { createTable, fetchFiles, fetchPartitions, fetchTable, fetchTables } from '../api/table'
import type { DataFile, LakeTable, PartitionSpec, TableSummary } from '../types/table'

interface TableState {
  items: LakeTable[]
  summary: TableSummary | null
  current: LakeTable | null
  partitions: PartitionSpec[]
  files: DataFile[]
  loading: boolean
  error: string
}

export const useTableStore = defineStore('tables', {
  state: (): TableState => ({
    items: [],
    summary: null,
    current: null,
    partitions: [],
    files: [],
    loading: false,
    error: '',
  }),
  getters: {
    byId: (state) => (id: number): LakeTable | undefined => state.items.find((item) => item.id === id),
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchTables()
        this.items = result.items
        this.summary = result.summary
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '湖表加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadDetail(tableId: number) {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchTable(tableId)
        this.current = result.table
        this.partitions = result.partitions
        const files = await fetchFiles(tableId, { limit: 500, sort: 'size_desc' })
        this.files = files.items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '湖表明细加载失败'
      } finally {
        this.loading = false
      }
    },
    async refreshPartitions(tableId: number) {
      const result = await fetchPartitions(tableId)
      this.partitions = result.items
    },
    async register(payload: Parameters<typeof createTable>[0]) {
      const result = await createTable(payload)
      await this.load()
      return result
    },
  },
})
