<template>
  <div class="bp-frame">
    <div class="bp-frame__head">
      <div class="flex items-center gap-3">
        <span class="label">任务 #{{ job.id }}</span>
        <StatusTag :status="job.status" kind="job" />
      </div>
      <span class="num text-[11px] text-[var(--ink-soft)]">{{ job.progress }}%</span>
    </div>
    <div class="bp-frame__body">
      <div class="meter h-[10px]">
        <div class="meter__fill" :class="job.status === 'failed' ? 'meter__fill--hot' : ''" :style="{ width: `${job.progress}%` }"></div>
      </div>
      <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] uppercase tracking-label text-[var(--ink-soft)]">
        <span :class="job.processed_groups > 0 ? 'text-[var(--ink)]' : ''">01 重写 {{ job.processed_groups }}/{{ job.groups_total }} 组</span>
        <span :class="job.progress >= 95 ? 'text-[var(--ink)]' : ''">02 快照</span>
        <span :class="job.progress >= 100 ? 'text-[var(--ink)]' : ''">03 守恒校验</span>
      </div>

      <dl class="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
        <div v-for="row in stats" :key="row.label" class="border-b border-dotted border-[var(--rule-soft)] pb-1.5">
          <dt class="label">{{ row.label }}</dt>
          <dd class="num mt-0.5 text-[13px]">{{ row.value }}</dd>
        </div>
      </dl>

      <div class="mt-4 flex items-center gap-3">
        <span class="bp-tag" :class="job.row_conserved ? 'bp-tag--ok' : 'bp-tag--hot'">
          {{ job.row_conserved ? '行数守恒 OK' : '行数不守恒' }}
        </span>
        <span class="text-[10.5px] text-[var(--ink-soft)]">
          Σrows {{ job.rows_before.toLocaleString() }} → {{ job.rows_after.toLocaleString() }}
        </span>
      </div>

      <div v-if="job.failure_reason" class="mt-3 border-l-2 border-[var(--rust)] px-3 py-2 text-[11.5px]">
        <span class="label text-[var(--rust)]">failure</span>
        <div class="mt-1">{{ job.failure_reason }}</div>
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1 tick-top pt-3 text-[10.5px] text-[var(--ink-soft)]">
        <span>触发：{{ job.triggered_by_name ?? '—' }}</span>
        <span>开始：{{ formatTime(job.started_at) }}</span>
        <span>结束：{{ formatTime(job.finished_at) }}</span>
        <span>Celery：{{ job.celery_task_id ? job.celery_task_id.slice(0, 8) : '—' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CompactJob } from '../../types/job'
import { formatBytes, formatCount } from '../../utils/formatBytes'
import { formatTime } from '../../utils/formatTime'
import StatusTag from './StatusTag.vue'

const props = defineProps<{ job: CompactJob }>()

const stats = computed(() => [
  { label: '重写输入文件', value: formatCount(props.job.rewritten_files) },
  { label: '产出文件', value: formatCount(props.job.produced_files) },
  { label: '写入字节', value: formatBytes(props.job.bytes_written) },
  { label: '处理分组', value: `${props.job.processed_groups} / ${props.job.groups_total}` },
  { label: '快照 ID', value: props.job.snapshot_id ? `#${props.job.snapshot_id}` : '—' },
  { label: '预计耗时', value: props.job.est_duration_seconds ? `${props.job.est_duration_seconds.toFixed(1)}s` : '—' },
])
</script>
