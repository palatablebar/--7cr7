<template>
  <div>
    <PageHeader
      figure="FIG.03"
      section="compaction plan"
      :title="table ? `${table.db_name}.${table.table_name} · 合并计划` : '合并计划'"
      description="在单分区内做 first-fit-decreasing 装箱：低于阈值的文件按大小降序装进目标容量，只重写多文件箱。"
    >
      <template #actions>
        <RouterLink v-if="table" :to="`/tables/${table.id}`" class="bp-btn">← 分区明细</RouterLink>
        <button
          class="bp-btn bp-btn--solid"
          :disabled="!canCompute || planStore.computing"
          data-test="compute-plan"
          @click="compute"
        >
          {{ planStore.computing ? '计算中…' : '计算计划' }}
        </button>
      </template>
    </PageHeader>

    <ErrorNotice :error="planStore.error" />

    <div v-if="!table" class="py-16 text-center text-[12px] text-[var(--ink-soft)]">正在加载分区…</div>

    <div v-else class="mt-4 grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
      <aside class="space-y-4">
        <section class="bp-frame">
          <div class="bp-frame__head">
            <span class="label">选择分区</span>
            <span class="label">{{ draft.selected.value.length }} 已选</span>
          </div>
          <div class="max-h-[300px] overflow-auto">
            <label
              v-for="partition in tableStore.partitions"
              :key="partition.id"
              class="flex cursor-pointer items-center gap-2.5 border-b border-[var(--rule-soft)] px-3 py-2 last:border-b-0 hover:bg-[var(--paper)]"
              :data-test="`partition-option-${partition.partition_value}`"
            >
              <input
                type="checkbox"
                class="accent-[var(--blue)]"
                :checked="draft.selected.value.includes(partition.partition_value)"
                @change="draft.toggle(partition)"
              />
              <span class="font-mono text-[11.5px]">{{ table.partition_key }}={{ partition.partition_value }}</span>
              <span class="ml-auto flex items-center gap-1.5">
                <span class="num text-[10.5px] text-[var(--rust)]" v-if="partition.small_file_count">{{ partition.small_file_count }} 小</span>
                <span v-if="partition.risk === 'hot'" class="bp-tag bp-tag--hot !text-[8.5px] !px-1">HOT</span>
                <HealthBadge :band="partition.health_band" :score="partition.health_score" :show-score="false" />
              </span>
            </label>
          </div>
          <div class="bp-frame__body !py-2.5 border-t border-[var(--rule-soft)]">
            <div class="flex items-center justify-between text-[11px]">
              <span class="text-[var(--ink-soft)]">目标大小</span>
              <span class="num">{{ table.target_file_size_mb }} MB</span>
            </div>
            <div class="mt-1.5 flex items-center justify-between text-[11px]">
              <span class="text-[var(--ink-soft)]">小文件阈值</span>
              <span class="num">{{ table.small_file_threshold_mb }} MB</span>
            </div>
            <div class="mt-1.5 flex items-center justify-between text-[11px]">
              <span class="text-[var(--ink-soft)]">今日配额</span>
              <span class="num">{{ auth.quotaRemaining }} / {{ auth.quota?.daily_plan_quota ?? '—' }}</span>
            </div>
          </div>
        </section>

        <LeaderNote label="algorithm">
          {{ MESSAGES.strategyNote }} 热分区（最新 dt）照常计算，但会降权并建议延后执行。
        </LeaderNote>
      </aside>

      <main class="min-w-0 space-y-5">
        <div v-if="!planStore.result" class="bp-frame">
          <div class="bp-frame__head"><span class="label">preview</span><span class="label">FIG.03-A</span></div>
          <div class="px-6 py-14 text-center">
            <div class="display-sm">选择分区后点击「计算计划」</div>
            <p class="mx-auto mt-2 max-w-[420px] text-[12px] leading-relaxed text-[var(--ink-soft)]">
              计划会持久化为草稿，并返回幂等指纹：相同输入再次计算将得到同一 fingerprint，
              用于判断计划是否可重复执行。
            </p>
          </div>
        </div>

        <template v-else>
          <div class="rise">
            <div class="grid grid-cols-2 gap-px border border-[var(--rule)] bg-[var(--rule)] md:grid-cols-6">
              <div class="bg-[var(--paper-2)] px-3 py-2.5">
                <div class="label">候选文件</div>
                <div class="num mt-1 text-[19px] leading-none">{{ plan.candidate_file_count }}</div>
              </div>
              <div class="bg-[var(--paper-2)] px-3 py-2.5">
                <div class="label">分组</div>
                <div class="num mt-1 text-[19px] leading-none">{{ plan.group_count }}</div>
              </div>
              <div class="bg-[var(--paper-2)] px-3 py-2.5">
                <div class="label">预计产出</div>
                <div class="num mt-1 text-[19px] leading-none">{{ plan.expected_output_files }}</div>
              </div>
              <div class="bg-[var(--paper-2)] px-3 py-2.5">
                <div class="label">节省文件</div>
                <div class="num mt-1 text-[19px] leading-none">{{ plan.saved_files }}</div>
              </div>
              <div class="bg-[var(--paper-2)] px-3 py-2.5">
                <div class="label">节省率</div>
                <div class="num mt-1 text-[19px] leading-none">{{ plan.savings_pct }}%</div>
              </div>
              <div class="bg-[var(--paper-2)] px-3 py-2.5">
                <div class="label">预计耗时</div>
                <div class="num mt-1 text-[19px] leading-none">{{ plan.est_duration_seconds.toFixed(1) }}s</div>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <span
              class="bp-tag"
              :class="planStore.result.idempotent ? 'bp-tag--ok' : 'bp-tag--muted'"
              data-test="idempotent-badge"
            >
              {{ planStore.result.idempotent ? '幂等命中：同指纹计划已存在' : '新指纹 · 首次生成' }}
            </span>
            <span class="font-mono text-[10px] text-[var(--ink-faint)]">fp {{ plan.fingerprint }}</span>
            <span v-if="planStore.result.idempotent && planStore.result.previous_plan" class="text-[10.5px] text-[var(--ink-soft)]">
              上次生成 {{ planStore.result.previous_plan.created_at }} · 状态 {{ planStore.result.previous_plan.status }}
            </span>
            <span class="ml-auto text-[10.5px] text-[var(--ink-soft)]">计划 #{{ plan.id }} · {{ plan.created_by_name }}</span>
          </div>

          <div v-if="plan.risk_flags.length" class="space-y-2">
            <div
              v-for="flag in plan.risk_flags"
              :key="flag.partition_value"
              class="rise-2 border-l-2 border-[var(--ochre)] bg-[color-mix(in_oklch,var(--ochre)_10%,transparent)] px-3 py-2"
            >
              <span class="label text-[oklch(46%_0.11_70)]">risk · {{ flag.code }}</span>
              <div class="mt-1 text-[11.5px]">{{ flag.message }}</div>
            </div>
          </div>

          <div class="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
            <PlanGroupTree :groups="plan.groups ?? []" :partition-key="plan.partition_key" />
            <div class="space-y-4">
              <CostLedger :cost="plan.cost" :rewritten-bytes="plan.rewritten_bytes" :saved-files="plan.saved_files" />
              <div class="bp-frame">
                <div class="bp-frame__head"><span class="label">提交执行</span></div>
                <div class="bp-frame__body">
                  <p class="text-[11.5px] leading-relaxed text-[var(--ink-soft)]">
                    提交后由 Celery worker 执行重写：逐组替换 manifest、回报进度，完成后自动生成
                    快照并做行数守恒校验。同一湖表只允许一个任务在跑。
                  </p>
                  <button
                    class="bp-btn bp-btn--solid mt-3 w-full justify-center !py-2"
                    :disabled="!auth.canWrite || planStore.executing"
                    data-test="execute-plan"
                    @click="execute"
                  >
                    {{ planStore.executing ? '提交中…' : '提交执行' }}
                  </button>
                  <div v-if="auth.isAnalyst" class="leader-note mt-3">
                    分析师为只读角色，只能查看计划与快照 diff。
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import HealthBadge from '../components/common/HealthBadge.vue'
import LeaderNote from '../components/common/LeaderNote.vue'
import CostLedger from '../components/common/CostLedger.vue'
import PlanGroupTree from '../components/common/PlanGroupTree.vue'
import { useTableStore } from '../stores/tableStore'
import { usePlanStore } from '../stores/planStore'
import { useAuthStore } from '../stores/authStore'
import { usePlanDraft } from '../hooks/usePlanDraft'
import { MESSAGES } from '../constants/messages'

const route = useRoute()
const router = useRouter()
const tableStore = useTableStore()
const planStore = usePlanStore()
const auth = useAuthStore()
const draft = usePlanDraft()

const tableId = computed(() => Number(route.params.id))
const table = computed(() => tableStore.current)
const plan = computed(() => planStore.current!)
const canCompute = computed(() => auth.canWrite && draft.selected.value.length > 0)

onMounted(async () => {
  if (tableId.value) {
    await tableStore.loadDetail(tableId.value)
    if (!draft.selected.value.length) draft.selectDefaults(tableStore.partitions)
  }
})

async function compute() {
  if (!table.value) return
  try {
    await planStore.compute({
      table_id: table.value.id,
      partition_values: draft.selected.value,
      note: 'UI 计划预览',
    })
  } catch {
    /* surfaced through planStore.error */
  }
}

async function execute() {
  if (!planStore.current) return
  try {
    const job = await planStore.execute(planStore.current.id)
    router.push({ path: '/jobs', query: { job: String(job.id), table: String(planStore.current.table_id) } })
  } catch {
    /* surfaced through planStore.error */
  }
}
</script>
