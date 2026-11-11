<template>
  <div class="bp-frame">
    <div class="bp-frame__head">
      <span class="label">成本模型 / cost ledger</span>
      <span class="label">FIG.03-B</span>
    </div>
    <div class="bp-frame__body">
      <dl class="grid grid-cols-2 gap-x-6 gap-y-2.5">
        <div v-for="row in rows" :key="row.label" class="flex items-baseline justify-between border-b border-dotted border-[var(--rule-soft)] pb-1.5">
          <dt class="text-[11px] text-[var(--ink-soft)]">{{ row.label }}</dt>
          <dd class="num text-[12.5px]" :class="row.emphasis ? 'text-[var(--blue-deep)]' : ''">{{ row.value }}</dd>
        </div>
      </dl>
      <div class="leader-note mt-4">
        重写吞吐 {{ cost.bandwidth_mb_per_s }} MB/s，每文件固定开销 {{ cost.per_file_overhead_s }}s；
        成本 = 重写 GB × ¥{{ cost.unit_cost_per_gb }}/GB；
        月度节省 = 减少文件数 × ¥{{ cost.cost_per_file_day }}/文件/天 × 30 天。
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CostLedger } from '../../types/plan'
import { formatBytes } from '../../utils/formatBytes'
import { secondsLabel } from '../../utils/formatTime'

const props = defineProps<{ cost: CostLedger; rewrittenBytes: number; savedFiles: number }>()

const rows = computed(() => [
  { label: '重写数据量', value: `${props.cost.rewrite_gb.toFixed(3)} GB` },
  { label: '预计耗时', value: secondsLabel(props.cost.est_duration_seconds), emphasis: true },
  { label: '传输 / 开销', value: `${props.cost.transfer_seconds.toFixed(1)}s + ${props.cost.overhead_seconds.toFixed(1)}s` },
  { label: '预计成本', value: `¥${props.cost.est_cost_yuan.toFixed(2)}`, emphasis: true },
  { label: '减少文件', value: `${props.savedFiles} 个` },
  { label: '月度节省', value: `¥${props.cost.monthly_saving_yuan.toFixed(2)}` },
  { label: '重写字节', value: formatBytes(props.rewrittenBytes) },
  { label: '回本周期', value: props.cost.payback_days === null ? '—' : `${props.cost.payback_days} 天` },
])
</script>
