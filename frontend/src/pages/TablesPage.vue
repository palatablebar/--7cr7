<template>
  <div>
    <PageHeader
      figure="FIG.01"
      section="lake inventory"
      title="湖表总览"
      description="40TB 对象存储里的 60 张 Parquet 表先挑这 3 张：按分区健康度定位碎片，再进入分区明细生成装箱计划。"
    >
      <template #actions>
        <RouterLink to="/jobs" class="bp-btn">任务台账</RouterLink>
        <RouterLink to="/snapshots" class="bp-btn">快照校验</RouterLink>
      </template>
    </PageHeader>

    <div class="mt-4 grid grid-cols-2 gap-px border border-[var(--rule-soft)] bg-[var(--rule-soft)] md:grid-cols-5">
      <div v-for="kpi in kpis" :key="kpi.label" class="bg-[var(--paper-2)] px-4 py-3">
        <div class="label">{{ kpi.label }}</div>
        <div class="mt-1 flex items-baseline gap-2">
          <span class="num text-[22px] leading-none">{{ kpi.value }}</span>
          <span class="text-[10.5px] text-[var(--ink-faint)]">{{ kpi.unit }}</span>
        </div>
      </div>
    </div>

    <ErrorNotice :error="tableStore.error" />

    <div class="mt-6">
      <div class="flex items-end justify-between border-b border-[var(--rule)] pb-2">
        <span class="label">table register / 按健康度排序</span>
        <span class="label">partition heatmap 0–100</span>
      </div>

      <div v-if="tableStore.loading && !tableStore.items.length" class="py-12 text-center text-[12px] text-[var(--ink-soft)]">
        正在读取 manifest 索引…
      </div>

      <div v-else class="divide-y divide-[var(--rule-soft)]">
        <article
          v-for="table in tableStore.items"
          :key="table.id"
          class="group grid gap-4 py-5 md:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)_minmax(0,1.1fr)]"
          :data-test="`table-row-${table.table_name}`"
        >
          <div class="min-w-0">
            <div class="flex items-center gap-3">
              <span class="font-display text-[11px] text-[var(--ink-faint)]">{{ String(table.id).padStart(2, '0') }}</span>
              <RouterLink :to="`/tables/${table.id}`" class="display-sm hover:!text-[var(--blue-deep)] hover:no-underline">
                {{ table.db_name }}.{{ table.table_name }}
              </RouterLink>
              <HealthBadge :band="table.avg_health_band" :score="table.avg_health_score" />
            </div>
            <div class="mt-1.5 text-[11px] leading-relaxed text-[var(--ink-soft)]">{{ table.description }}</div>
            <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10.5px] text-[var(--ink-soft)]">
              <span><span class="label">part</span> {{ table.partition_key }}</span>
              <span><span class="label">fmt</span> {{ table.file_format }}</span>
              <span><span class="label">target</span> {{ table.target_file_size_mb }} MB</span>
              <span><span class="label">threshold</span> {{ table.small_file_threshold_mb }} MB</span>
              <span v-if="table.owner_name"><span class="label">owner</span> {{ table.owner_name }}</span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 self-center text-[11px]">
            <div class="flex items-baseline justify-between border-b border-dotted border-[var(--rule-soft)] pb-1">
              <span class="text-[var(--ink-soft)]">文件</span><span class="num">{{ table.file_count }}</span>
            </div>
            <div class="flex items-baseline justify-between border-b border-dotted border-[var(--rule-soft)] pb-1">
              <span class="text-[var(--ink-soft)]">小文件</span>
              <span class="num" :class="table.small_file_count > 0 ? 'text-[var(--rust)]' : ''">{{ table.small_file_count }}</span>
            </div>
            <div class="flex items-baseline justify-between border-b border-dotted border-[var(--rule-soft)] pb-1">
              <span class="text-[var(--ink-soft)]">总大小</span><span class="num">{{ formatBytes(table.total_size_bytes) }}</span>
            </div>
            <div class="flex items-baseline justify-between border-b border-dotted border-[var(--rule-soft)] pb-1">
              <span class="text-[var(--ink-soft)]">平均文件</span><span class="num">{{ formatBytes(table.avg_file_size_bytes) }}</span>
            </div>
            <div class="flex items-baseline justify-between">
              <span class="text-[var(--ink-soft)]">待整理分区</span><span class="num">{{ table.pending_partition_count }}</span>
            </div>
            <div class="flex items-baseline justify-between">
              <span class="text-[var(--ink-soft)]">可回收</span><span class="num">{{ table.reclaimable_file_count }} 文件</span>
            </div>
          </div>

          <div class="self-center">
            <PartitionHeatmap :partitions="table.partitions" compact />
            <div class="mt-2 flex items-center justify-between">
              <span class="text-[10px] text-[var(--ink-faint)]">{{ table.partition_count }} 个分区 · HOT {{ table.hot_partition_count }}</span>
              <RouterLink :to="`/tables/${table.id}`" class="text-[11px] text-[var(--blue)] hover:underline">
                分区明细 →
              </RouterLink>
            </div>
          </div>
        </article>
      </div>
    </div>

    <div v-if="auth.isAdmin" class="mt-8 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
      <div class="leader-note">
        管理员可以登记新的湖表并调整目标文件大小；登记后分区健康度会立即按 manifest 计算。
      </div>
      <div class="bp-frame">
        <div class="bp-frame__head">
          <span class="label">登记湖表 / admin only</span>
          <span class="label">FIG.01-B</span>
        </div>
        <form class="bp-frame__body grid grid-cols-2 gap-3" @submit.prevent="register">
          <div>
            <label class="label block mb-1">库名</label>
            <input v-model="form.db_name" class="bp-input" data-test="new-db" />
          </div>
          <div>
            <label class="label block mb-1">表名</label>
            <input v-model="form.table_name" class="bp-input" data-test="new-table" />
          </div>
          <div>
            <label class="label block mb-1">分区键</label>
            <input v-model="form.partition_key" class="bp-input" />
          </div>
          <div>
            <label class="label block mb-1">目标大小 MB</label>
            <input v-model.number="form.target_file_size_mb" type="number" class="bp-input" />
          </div>
          <div class="col-span-2">
            <label class="label block mb-1">说明</label>
            <input v-model="form.description" class="bp-input" placeholder="上游写入方式 / 下游消费方" />
          </div>
          <div class="col-span-2 flex items-center justify-between">
            <ErrorNotice :error="registerError" />
            <button type="submit" class="bp-btn bp-btn--solid" data-test="register-table">登记</button>
          </div>
        </form>
      </div>
    </div>

    <div v-else-if="auth.isAnalyst" class="mt-8">
      <LeaderNote label="read-only role">
        当前为分析师（analyst）：可以浏览分区健康度、计划与快照 diff，但不能生成或执行合并计划。
      </LeaderNote>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import PartitionHeatmap from '../components/common/PartitionHeatmap.vue'
import HealthBadge from '../components/common/HealthBadge.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import LeaderNote from '../components/common/LeaderNote.vue'
import { useTableStore } from '../stores/tableStore'
import { useAuthStore } from '../stores/authStore'
import type { LakeTable } from '../types/table'
import type { ApiError } from '../types/api'
import { formatBytes } from '../utils/formatBytes'

const tableStore = useTableStore()
const auth = useAuthStore()
const registerError = ref<ApiError | string | null>(null)

const form = reactive({
  db_name: 'dwd',
  table_name: 'payment',
  partition_key: 'dt',
  target_file_size_mb: 256,
  small_file_threshold_mb: 64,
  description: '支付流水明细，下游对账与风控消费',
})

const kpis = computed(() => {
  const summary = tableStore.summary
  return [
    { label: '湖表', value: summary?.table_count ?? 0, unit: '张' },
    { label: '小文件', value: summary?.small_file_count ?? 0, unit: '个' },
    { label: '待整理分区', value: summary?.pending_partition_count ?? 0, unit: '个' },
    { label: '可回收文件', value: summary?.reclaimable_file_count ?? 0, unit: '个' },
    { label: '平均健康度', value: summary?.avg_health_score ?? 0, unit: '/100' },
  ]
})

async function register() {
  registerError.value = null
  try {
    await tableStore.register({ ...form })
  } catch (error) {
    registerError.value = error as ApiError
  }
}

onMounted(() => {
  tableStore.load()
})
</script>
