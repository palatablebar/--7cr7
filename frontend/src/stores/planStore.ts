import { defineStore } from 'pinia'
import { createPlan, executePlan, fetchPlan } from '../api/plan'
import type { CompactPlan, PlanCreateResult } from '../types/plan'
import { useAuthStore } from './authStore'

interface PlanState {
  current: CompactPlan | null
  result: PlanCreateResult | null
  computing: boolean
  executing: boolean
  error: string
}

export const usePlanStore = defineStore('plan', {
  state: (): PlanState => ({
    current: null,
    result: null,
    computing: false,
    executing: false,
    error: '',
  }),
  actions: {
    async compute(payload: { table_id: number; partition_values: string[]; note?: string }) {
      this.computing = true
      this.error = ''
      try {
        const result = await createPlan(payload)
        this.result = result
        this.current = result.plan
        useAuthStore().setQuota(result.quota)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '计划计算失败'
        throw error
      } finally {
        this.computing = false
      }
    },
    async load(planId: number) {
      const result = await fetchPlan(planId)
      this.current = result.plan
      return result.plan
    },
    async execute(planId: number) {
      this.executing = true
      this.error = ''
      try {
        const result = await executePlan(planId)
        return result.job
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '执行失败'
        throw error
      } finally {
        this.executing = false
      }
    },
  },
})
