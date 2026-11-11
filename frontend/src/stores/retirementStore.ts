import { defineStore } from 'pinia'
import {
  createRetirement,
  executeRetirement,
  fetchReclaimManifest,
  fetchRetirements,
  restoreRetirement,
} from '../api/retirement'
import type { PartitionRetirement, ReclaimManifest } from '../types/retirement'

interface RetirementState {
  manifest: ReclaimManifest | null
  items: PartitionRetirement[]
  loading: boolean
  acting: boolean
  error: string
  notice: string
}

export const useRetirementStore = defineStore('retirement', {
  state: (): RetirementState => ({
    manifest: null,
    items: [],
    loading: false,
    acting: false,
    error: '',
    notice: '',
  }),
  actions: {
    async load(tableId: number) {
      this.loading = true
      this.error = ''
      try {
        const [manifest, retirements] = await Promise.all([fetchReclaimManifest(tableId), fetchRetirements(tableId)])
        this.manifest = manifest
        this.items = retirements.items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '回收清单加载失败'
      } finally {
        this.loading = false
      }
    },
    async create(tableId: number, partitionValues: string[]) {
      this.acting = true
      this.error = ''
      this.notice = ''
      try {
        const result = await createRetirement(tableId, {
          partition_values: partitionValues,
          note: '分区退役：先冻结停止新合并，再一次性和并清理',
        })
        this.notice = result.idempotent
          ? `命中相同指纹的退役单 #${result.retirement.id}，未重复冻结`
          : `退役单 #${result.retirement.id} 已生成，所选分区已停止新合并`
        await this.load(tableId)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '退役单生成失败'
        throw error
      } finally {
        this.acting = false
      }
    },
    async execute(tableId: number, retirementId: number, simulateFailure = false) {
      this.acting = true
      this.error = ''
      this.notice = ''
      try {
        const result = await executeRetirement(retirementId, { simulate_failure: simulateFailure })
        if (result.idempotent) {
          this.notice = `退役单 #${retirementId} 已完成过，重复执行不会重复清理`
        } else if (result.ok === false) {
          this.error = `退役执行失败：事务已整批回滚，分区文件保持原样，可恢复原分区`
        } else {
          const reclaimed = result.retirement.result?.reclaimed_file_count ?? 0
          this.notice = `退役完成：一次性回收 ${reclaimed} 个文件`
        }
        await this.load(tableId)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '退役执行失败'
        throw error
      } finally {
        this.acting = false
      }
    },
    async restore(tableId: number, retirementId: number) {
      this.acting = true
      this.error = ''
      this.notice = ''
      try {
        const result = await restoreRetirement(retirementId)
        this.notice = result.idempotent ? `退役单 #${retirementId} 已恢复过` : `分区已恢复为可合并状态`
        await this.load(tableId)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '恢复失败'
        throw error
      } finally {
        this.acting = false
      }
    },
  },
})
