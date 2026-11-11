<template>
  <div>
    <PageHeader
      figure="FIG.02"
      section="partition & files"
      :title="table ? `${table.db_name}.${table.table_name}` : '分区明细'"
      :description="table?.description ?? '选择分区、查看小文件分布，再进入合并计划预览。'"
    >
      <template #actions>
        <RouterLink to="/tables" class="bp-btn">← 返回总览</RouterLink>
        <RouterLink v-if="table" :to="`/tables/${table.id}/retire`" class="bp-btn" data-test="goto-retire">
          分区退役
        </RouterLink>
        <RouterLink
          v-if="table"
          :to="`/tables/${table.id}/plan`"
          class="bp-btn"
          :class="auth.canWrite ? 'bp-btn--solid' : 'opacity-40 pointer-events-none'"
          data-test="goto-plan"
        >
          生成合并计划
        </RouterLink>
      </template>
    </PageHeader>

    <ErrorNotice :error="tableStore.error" />

    <div v-if="!table" class="py-16 text-center text-[12px] text-[var(--ink-soft)]">正在读取分区索引…</div>

    <template v-else>
      <div class="mt-4 grid grid-cols-2 gap-px border border-[var(--rule-soft)] bg-[var(--rule-soft)] md:grid-cols-6">
        <div v-for="kpi in kpis" :key="kpi.label" class="bg-[var(--paper-2)] px-4 py-3">
          <div class="label">{{ kpi.label }}</div>
          <div class="mt-1 num text-[19px] leading-none">{{ kpi.value }}</div>
        </div>
      </div>

      <div class="mt-6 grid gap-5 xl:grid-cols-[1.05fr_1fr]">
        <section class="bp-frame" data-test="partition-table">
          <div class="bp-frame__head">
            <span class="label">分区清单 / {{ table.partitions.length || tableStore.partitions.length }} partitions</span>
            <span class="label">按分区值倒序</span>
          </div>
          <div class="max-h-[420px] overflow-auto">
            <table class="bp-table">
              <thead>
                <tr>
                  <th>分区</th>
                  <th class="text-right">文件</th>
                  <th class="text-right">小文件</th>
                  <th class="text-right">平均大小</th>
                  <th>健康度</th>
                  <th>风险</th>
                  <th>生命周期</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="partition in tableStore.partitions" :key="partition.id" :data-test="`partition-${partition.partition_value}`">
                  <td class="font-mono text-[11.5px]">{{ table.partition_key }}={{ partition.partition_value }}</td>
                  <td class="num">{{ partition.file_count }}</td>
                  <td class="num" :class="partition.small_file_count > 0 ? 'text-[var(--rust)]' : ''">{{ partition.small_file_count }}</td>
                  <td class="num">{{ formatMb(partition.avg_file_size_bytes) }}</td>
                  <td>
                    <div class="flex items-center gap-2">
                      <div class="meter w-[64px]">
                        <div
                          class="meter__fill"
                          :class="`meter__fill--${partition.health_band === 'healthy' ? 'ok' : partition.health_band === 'watch' ? 'watch' : 'hot'}`"
                          :style="{ width: `${partition.health_score}%` }"
                        ></div>
                      </div>
                      <span class="num text-[11px]">{{ partition.health_score }}</span>
                    </div>
                  </td>
                  <td>
                    <span v-if="partition.risk === 'hot'" class="bp-tag bp-tag--hot">HOT</span>
                    <span v-else class="bp-tag bp-tag--muted">normal</span>
                  </td>
                  <td>
                    <span
                      class="bp-tag"
                      :class="partition.lifecycle === 'active' ? 'bp-tag--muted' : partition.lifecycle === 'retiring' ? 'bp-tag--watch' : 'bp-tag--ok'"
                      :data-test="`lifecycle-${partition.partition_value}`"
                    >
                      {{ lifecycleLabel(partition.lifecycle) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="bp-frame__body border-t border-[var(--rule-soft)] !py-2.5">
            <div class="leader-note">
              健康度 = 100 × (0.65 × 平均文件大小 / 目标大小 + 0.35 × (1 − 文件数/60))，
              最新分区标记为 HOT，计划中建议延后执行。退役冻结中的分区停止新合并，可前往「分区退役」查看回收清单。
            </div>
          </div>
        </section>

        <section class="bp-frame" data-test="files-panel">
          <div class="bp-frame__head">
            <span class="label">文件明细 / {{ filters.filteredFiles.value.length }} of {{ tableStore.files.length }}</span>
            <span class="label">小文件阈值 {{ table.small_file_threshold_mb }} MB</span>
          </div>
          <div class="bp-frame__body !py-2.5 border-b border-[var(--rule-soft)]">
            <div class="grid grid-cols-2 gap-2 md:grid-cols-3">
              <div>
                <label class="label block mb-1">分区</label>
                <select v-model="filters.state.value.partition" class="bp-select" data-test="filter-partition">
                  <option value="">全部</option>
                  <option v-for="value in filters.partitionOptions.value" :key="value" :value="value">{{ value }}</option>
                </select>
              </div>
              <div>
                <label class="label block mb-1">大小</label>
                <select v-model="filters.state.value.sizeBand" class="bp-select">
                  <option value="all">全部</option>
                  <option value="small">小于阈值</option>
                  <option value="large">大于等于阈值</option>
                </select>
              </div>
              <div>
                <label class="label block mb-1">排序</label>
                <select v-model="filters.state.value.sort" class="bp-select">
                  <option value="size_desc">大小倒序</option>
                  <option value="size_asc">大小正序</option>
                  <option value="rows_desc">行数倒序</option>
                  <option value="path_asc">路径</option>
                </select>
              </div>
            </div>
          </div>
          <div class="max-h-[352px] overflow-auto">
            <table class="bp-table">
              <thead>
                <tr>
                  <th>文件</th>
                  <th class="text-right">大小</th>
                  <th class="text-right">行数</th>
                  <th>来源</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="file in filters.filteredFiles.value.slice(0, 40)" :key="file.id" :data-test="`file-${file.id}`">
                  <td class="max-w-[220px]">
                    <div class="truncate font-mono text-[10.5px]" :title="file.path">{{ file.file_name }}</div>
                    <div class="text-[9.5px] text-[var(--ink-faint)]">…{{ file.checksum.slice(0, 10) }}</div>
                  </td>
                  <td class="num" :class="file.is_small ? 'text-[var(--rust)]' : ''">{{ file.size_mb }} MB</td>
                  <td class="num">{{ file.row_count.toLocaleString() }}</td>
                  <td><span class="bp-tag bp-tag--muted">{{ file.write_source }}</span></td>
                </tr>
              </tbody>
            </table>
            <div v-if="!filters.filteredFiles.value.length" class="py-8 text-center text-[11.5px] text-[var(--ink-faint)]">
              当前筛选条件下没有文件
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useTableStore } from '../stores/tableStore'
import { useAuthStore } from '../stores/authStore'
import { useTableFilters } from '../hooks/useTableFilters'
import { PARTITION_LIFECYCLE_LABELS } from '../constants/partitionLifecycle'
import { formatMb } from '../utils/formatBytes'
import { formatBytes } from '../utils/formatBytes'

const route = useRoute()
const tableStore = useTableStore()
const auth = useAuthStore()

const tableId = computed(() => Number(route.params.id))
const table = computed(() => tableStore.current)

function lifecycleLabel(lifecycle: string) {
  return PARTITION_LIFECYCLE_LABELS[lifecycle] ?? lifecycle
}

const filters = useTableFilters(
  () => tableStore.partitions,
  () => tableStore.files,
)

const kpis = computed(() => [
  { label: '分区', value: table.value?.partition_count ?? 0 },
  { label: '文件', value: table.value?.file_count ?? 0 },
  { label: '小文件', value: table.value?.small_file_count ?? 0 },
  { label: '总大小', value: formatBytes(table.value?.total_size_bytes) },
  { label: '平均健康度', value: table.value?.avg_health_score ?? 0 },
  { label: '可回收', value: `${table.value?.reclaimable_file_count ?? 0} 文件` },
])

onMounted(() => {
  if (tableId.value) tableStore.loadDetail(tableId.value)
})

watch(tableId, (value) => {
  if (value) tableStore.loadDetail(value)
})
</script>
