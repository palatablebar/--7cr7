<template>
  <div>
    <PageHeader
      figure="FIG.05"
      section="partition retirement"
      :title="table ? `${table.db_name}.${table.table_name} · 分区退役` : '分区退役'"
      description="回收清单按保留快照的引用划分：被引用的文件受保护不删除，其余文件随退役一次性回收。引用数 + 可回收数 = 分区文件总数。"
    >
      <template #actions>
        <RouterLink v-if="table" :to="`/tables/${table.id}`" class="bp-btn">← 分区明细</RouterLink>
        <button class="bp-btn" :disabled="retirementStore.loading" @click="reload">刷新</button>
      </template>
    </PageHeader>

    <ErrorNotice :error="retirementStore.error" />
    <div
      v-if="retirementStore.notice"
      class="mt-3 border-l-2 border-[var(--blue)] bg-[color-mix(in_oklch,var(--blue)_7%,transparent)] px-3 py-2 text-[12px]"
      data-test="retirement-notice"
    >
      {{ retirementStore.notice }}
    </div>

    <div v-if="!manifest" class="py-16 text-center text-[12px] text-[var(--ink-soft)]">正在计算回收清单…</div>

    <template v-else>
      <div class="mt-4 grid grid-cols-2 gap-px border border-[var(--rule-soft)] bg-[var(--rule-soft)] md:grid-cols-6">
        <div v-for="kpi in kpis" :key="kpi.label" class="bg-[var(--paper-2)] px-4 py-3">
          <div class="label">{{ kpi.label }}</div>
          <div class="mt-1 num text-[19px] leading-none">{{ kpi.value }}</div>
        </div>
      </div>

      <div class="mt-6 grid gap-5 xl:grid-cols-[1.15fr_1fr]">
        <!-- 回收清单 -->
        <section class="bp-frame" data-test="reclaim-manifest">
          <div class="bp-frame__head">
            <span class="label">回收清单 / {{ manifest.items.length }} partitions</span>
            <span class="label">保留快照 v{{ manifest.retained_snapshot_versions.join(' · v') || '—' }}</span>
          </div>
          <div class="max-h-[430px] overflow-auto">
            <table class="bp-table">
              <thead>
                <tr>
                  <th class="w-[28px]"></th>
                  <th>分区</th>
                  <th class="text-right">文件总数</th>
                  <th class="text-right">保护引用</th>
                  <th class="text-right">可回收</th>
                  <th class="text-right">可回收量</th>
                  <th>校验</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="item in manifest.items" :key="item.partition_value">
                  <tr :data-test="`reclaim-${item.partition_value}`">
                    <td>
                      <input
                        v-if="item.lifecycle === 'active' && item.reclaimable_count > 0"
                        type="checkbox"
                        class="accent-[var(--blue)]"
                        :checked="selected.includes(item.partition_value)"
                        :data-test="`select-${item.partition_value}`"
                        @change="toggle(item.partition_value)"
                      />
                      <span v-else-if="item.lifecycle !== 'active'" class="bp-tag bp-tag--watch !text-[8.5px] !px-1">
                        {{ lifecycleLabel(item.lifecycle) }}
                      </span>
                    </td>
                    <td class="font-mono text-[11.5px]">
                      <button class="hover:underline" @click="expand(item.partition_value)">
                        {{ manifest.partition_key }}={{ item.partition_value }}
                      </button>
                    </td>
                    <td class="num">{{ item.file_count }}</td>
                    <td class="num text-[var(--blue-deep)]">{{ item.protected_count }}</td>
                    <td class="num" :class="item.reclaimable_count > 0 ? 'text-[var(--rust)]' : ''">
                      {{ item.reclaimable_count }}
                    </td>
                    <td class="num">{{ formatBytes(item.reclaimable_bytes) }}</td>
                    <td>
                      <span v-if="item.invariant_ok" class="bp-tag bp-tag--ok !text-[8.5px]">
                        {{ item.protected_count }}+{{ item.reclaimable_count }}={{ item.file_count }}
                      </span>
                      <span v-else class="bp-tag bp-tag--hot !text-[8.5px]">不平衡</span>
                    </td>
                  </tr>
                  <tr v-if="expanded === item.partition_value">
                    <td colspan="7" class="!p-0">
                      <div class="grid gap-px bg-[var(--rule-soft)] md:grid-cols-2">
                        <div class="bg-[var(--paper)] px-3 py-2.5">
                          <div class="label mb-1.5">保护引用 / {{ item.protected_count }}（保留快照引用，不删）</div>
                          <div class="max-h-[150px] overflow-auto space-y-1">
                            <div v-for="file in item.protected_files" :key="file.path" class="font-mono text-[10px] leading-relaxed">
                              <span class="text-[var(--ink-soft)]">{{ fileName(file.path) }}</span>
                              <span class="ml-1.5 text-[var(--ink-faint)]">{{ formatBytes(file.size_bytes) }}</span>
                              <span class="ml-1.5 text-[var(--blue-deep)]">v{{ (file.snapshot_versions ?? []).join(',v') }}</span>
                            </div>
                            <div v-if="!item.protected_files.length" class="text-[10.5px] text-[var(--ink-faint)]">无保护引用</div>
                          </div>
                        </div>
                        <div class="bg-[var(--paper)] px-3 py-2.5">
                          <div class="label mb-1.5">可回收 / {{ item.reclaimable_count }}（未被快照引用）</div>
                          <div class="max-h-[150px] overflow-auto space-y-1">
                            <div v-for="file in item.reclaimable_files" :key="file.path" class="font-mono text-[10px] leading-relaxed">
                              <span class="text-[var(--ink-soft)]">{{ fileName(file.path) }}</span>
                              <span class="ml-1.5 text-[var(--ink-faint)]">{{ formatBytes(file.size_bytes) }}</span>
                            </div>
                            <div v-if="!item.reclaimable_files.length" class="text-[10.5px] text-[var(--ink-faint)]">无可回收文件</div>
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
          <div class="bp-frame__body border-t border-[var(--rule-soft)] !py-2.5">
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-[11px] text-[var(--ink-soft)]">已选 {{ selected.length }} 个分区</span>
              <span class="text-[10.5px] text-[var(--ink-faint)]">生成退役单后先冻结分区（停止新合并），再一次性执行退役</span>
              <button
                class="bp-btn bp-btn--solid ml-auto"
                :disabled="!auth.canWrite || !selected.length || retirementStore.acting"
                data-test="create-retirement"
                @click="create"
              >
                {{ retirementStore.acting ? '处理中…' : '生成退役单并冻结' }}
              </button>
            </div>
          </div>
        </section>

        <!-- 退役单与结果 -->
        <section class="bp-frame" data-test="retirement-list">
          <div class="bp-frame__head">
            <span class="label">退役单 / {{ retirementStore.items.length }} 单</span>
            <span class="label">一次性原子执行</span>
          </div>
          <div class="max-h-[500px] overflow-auto divide-y divide-[var(--rule-soft)]">
            <article v-for="retirement in retirementStore.items" :key="retirement.id" class="px-3 py-3" :data-test="`retirement-${retirement.id}`">
              <div class="flex items-center gap-2.5">
                <span class="font-display text-[12px]">#{{ retirement.id }}</span>
                <StatusTag :status="retirement.status" kind="retirement" />
                <span class="font-mono text-[10px] text-[var(--ink-faint)]">fp {{ retirement.fingerprint.slice(0, 10) }}</span>
                <span class="ml-auto text-[10px] text-[var(--ink-faint)]">{{ retirement.created_at }}</span>
              </div>
              <div class="mt-1.5 font-mono text-[11px] text-[var(--ink-soft)]">
                {{ manifest.partition_key }}={{ retirement.partition_values.join(` · ${manifest.partition_key}=`) }}
              </div>
              <div class="mt-2 grid grid-cols-3 gap-2 text-[11px]">
                <div class="border border-dotted border-[var(--rule-soft)] px-2 py-1.5">
                  <div class="label !text-[9px]">保护引用</div>
                  <div class="num mt-0.5">{{ retirement.protected_file_count }} 文件</div>
                </div>
                <div class="border border-dotted border-[var(--rule-soft)] px-2 py-1.5">
                  <div class="label !text-[9px]">可回收</div>
                  <div class="num mt-0.5 text-[var(--rust)]">{{ retirement.reclaimable_file_count }} 文件</div>
                </div>
                <div class="border border-dotted border-[var(--rule-soft)] px-2 py-1.5">
                  <div class="label !text-[9px]">可回收量</div>
                  <div class="num mt-0.5">{{ formatBytes(retirement.reclaimable_bytes) }}</div>
                </div>
              </div>

              <!-- 退役结果 -->
              <div v-if="retirement.status === 'retired' && retirement.result" class="mt-2 border-l-2 border-[var(--ok,var(--blue))] bg-[color-mix(in_oklch,var(--blue)_6%,transparent)] px-2.5 py-2" :data-test="`retirement-result-${retirement.id}`">
                <div class="label !text-[9px]">退役结果 · {{ retirement.result.executed_at }}</div>
                <div class="mt-1 text-[11px]">
                  一次性回收 <span class="num">{{ retirement.result.reclaimed_file_count }}</span> 个文件 /
                  <span class="num">{{ formatBytes(retirement.result.reclaimed_bytes) }}</span>
                </div>
                <div v-for="partition in retirement.result.partitions ?? []" :key="partition.partition_value" class="mt-1 flex items-center justify-between font-mono text-[10px] text-[var(--ink-soft)]">
                  <span>{{ manifest.partition_key }}={{ partition.partition_value }}</span>
                  <span>
                    回收 {{ partition.reclaimed_count }} · 保护留存 {{ partition.protected_remaining }}
                    <template v-if="partition.skipped_protected.length">· 新快照保护 {{ partition.skipped_protected.length }}</template>
                  </span>
                </div>
              </div>
              <div v-else-if="retirement.status === 'failed'" class="mt-2 border-l-2 border-[var(--rust)] bg-[color-mix(in_oklch,var(--rust)_7%,transparent)] px-2.5 py-2">
                <div class="label !text-[9px] text-[var(--rust)]">执行失败 · 事务已整批回滚</div>
                <div class="mt-1 text-[11px] leading-relaxed">{{ retirement.failure_reason }}</div>
                <div class="mt-1 text-[10.5px] text-[var(--ink-soft)]">分区文件保持原样，可恢复原分区后重试。</div>
              </div>
              <div v-else-if="retirement.status === 'restored' && retirement.result" class="mt-2 text-[10.5px] text-[var(--ink-soft)]">
                已于 {{ retirement.result.restored_at }} 恢复 {{ (retirement.result.restored_partitions ?? []).length }} 个分区为可合并状态。
              </div>

              <div class="mt-2.5 flex flex-wrap items-center gap-2">
                <template v-if="retirement.status === 'retiring'">
                  <button
                    class="bp-btn bp-btn--solid !px-2.5 !py-1"
                    :disabled="!auth.canWrite || retirementStore.acting"
                    :data-test="`execute-retirement-${retirement.id}`"
                    @click="execute(retirement.id)"
                  >
                    一次性执行退役
                  </button>
                  <label v-if="auth.canWrite" class="flex items-center gap-1.5 text-[10.5px] text-[var(--ink-soft)]">
                    <input v-model="simulateFailure" type="checkbox" class="accent-[var(--rust)]" :data-test="`simulate-failure-${retirement.id}`" />
                    演练：注入失败
                  </label>
                  <button
                    class="bp-btn bp-btn--quiet !px-2.5 !py-1"
                    :disabled="!auth.canWrite || retirementStore.acting"
                    :data-test="`restore-retirement-${retirement.id}`"
                    @click="restore(retirement.id)"
                  >
                    取消并恢复
                  </button>
                </template>
                <button
                  v-else-if="retirement.status === 'failed'"
                  class="bp-btn bp-btn--danger !px-2.5 !py-1"
                  :disabled="!auth.canWrite || retirementStore.acting"
                  :data-test="`restore-retirement-${retirement.id}`"
                  @click="restore(retirement.id)"
                >
                  恢复原分区
                </button>
                <button
                  v-else-if="retirement.status === 'retired'"
                  class="bp-btn bp-btn--quiet !px-2.5 !py-1"
                  :disabled="!auth.canWrite || retirementStore.acting"
                  :data-test="`reexecute-retirement-${retirement.id}`"
                  @click="execute(retirement.id)"
                >
                  重复执行（幂等）
                </button>
              </div>
            </article>
            <div v-if="!retirementStore.items.length" class="px-4 py-10 text-center text-[11.5px] text-[var(--ink-faint)]">
              还没有退役单。在左侧回收清单勾选分区，生成退役单并冻结。
            </div>
          </div>
          <div class="bp-frame__body border-t border-[var(--rule-soft)] !py-2.5">
            <div class="leader-note">
              执行在单个事务内完成：全部选中分区的可回收文件要么一起回收，要么整体回滚；
              失败后可恢复原分区，重复执行不会重复清理。
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import StatusTag from '../components/common/StatusTag.vue'
import { useRetirementStore } from '../stores/retirementStore'
import { useTableStore } from '../stores/tableStore'
import { useAuthStore } from '../stores/authStore'
import { PARTITION_LIFECYCLE_LABELS } from '../constants/partitionLifecycle'
import { formatBytes } from '../utils/formatBytes'

const route = useRoute()
const retirementStore = useRetirementStore()
const tableStore = useTableStore()
const auth = useAuthStore()

const tableId = computed(() => Number(route.params.id))
const table = computed(() => tableStore.current)
const manifest = computed(() => retirementStore.manifest)

const selected = ref<string[]>([])
const expanded = ref<string | null>(null)
const simulateFailure = ref(false)

const kpis = computed(() => {
  const totals = manifest.value?.totals
  return [
    { label: '保留快照', value: manifest.value?.snapshot_count ?? 0 },
    { label: '保护引用', value: `${totals?.protected_count ?? 0} 文件` },
    { label: '可回收', value: `${totals?.reclaimable_count ?? 0} 文件` },
    { label: '可回收量', value: formatBytes(totals?.reclaimable_bytes) },
    { label: '清单校验', value: totals?.invariant_ok ? '平衡' : '不平衡' },
    { label: '退役单', value: retirementStore.items.length },
  ]
})

function lifecycleLabel(lifecycle: string) {
  return PARTITION_LIFECYCLE_LABELS[lifecycle] ?? lifecycle
}

function fileName(path: string) {
  return path.split('/').pop() ?? path
}

function toggle(partitionValue: string) {
  selected.value = selected.value.includes(partitionValue)
    ? selected.value.filter((value) => value !== partitionValue)
    : [...selected.value, partitionValue]
}

function expand(partitionValue: string) {
  expanded.value = expanded.value === partitionValue ? null : partitionValue
}

async function reload() {
  await Promise.all([retirementStore.load(tableId.value), tableStore.loadDetail(tableId.value)])
}

async function create() {
  if (!selected.value.length) return
  try {
    await retirementStore.create(tableId.value, selected.value)
    selected.value = []
    await tableStore.loadDetail(tableId.value)
  } catch {
    /* surfaced through retirementStore.error */
  }
}

async function execute(retirementId: number) {
  try {
    await retirementStore.execute(tableId.value, retirementId, simulateFailure.value)
    simulateFailure.value = false
    await tableStore.loadDetail(tableId.value)
  } catch {
    /* surfaced through retirementStore.error */
  }
}

async function restore(retirementId: number) {
  try {
    await retirementStore.restore(tableId.value, retirementId)
    await tableStore.loadDetail(tableId.value)
  } catch {
    /* surfaced through retirementStore.error */
  }
}

onMounted(async () => {
  if (tableId.value) {
    await tableStore.loadDetail(tableId.value)
    await retirementStore.load(tableId.value)
  }
})
</script>
