<template>
  <div>
    <PageHeader
      figure="FIG.04"
      section="execution monitor"
      :title="'任务执行监控'"
      description="合并任务由 backend 投递给 Celery worker 执行。进度、重写文件数与快照校验都落在 MySQL，刷新页面不会丢状态。"
    >
      <template #actions>
        <button class="bp-btn" :disabled="jobStore.loading" @click="refresh">刷新</button>
        <RouterLink to="/snapshots" class="bp-btn">快照校验</RouterLink>
      </template>
    </PageHeader>

    <ErrorNotice :error="jobStore.error" />

    <div class="mt-4 grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <section class="bp-frame" data-test="job-list">
        <div class="bp-frame__head">
          <span class="label">任务台账</span>
          <span class="num text-[10.5px]">{{ jobStore.items.length }} 条</span>
        </div>
        <div class="max-h-[560px] overflow-auto">
          <button
            v-for="job in jobStore.items"
            :key="job.id"
            class="block w-full border-b border-[var(--rule-soft)] px-3 py-2.5 text-left transition-colors last:border-b-0 hover:bg-[var(--paper)]"
            :class="selectedId === job.id ? 'bg-[var(--paper)]' : ''"
            :data-test="`job-item-${job.id}`"
            @click="select(job.id)"
          >
            <div class="flex items-center gap-2.5">
              <span class="font-display text-[12px]">#{{ job.id }}</span>
              <StatusTag :status="job.status" kind="job" />
              <span class="ml-auto num text-[10.5px]">{{ job.progress }}%</span>
            </div>
            <div class="mt-1 truncate text-[11px] text-[var(--ink-soft)]">{{ job.table_fq_name }}</div>
            <div class="mt-1 flex items-center justify-between text-[10px] text-[var(--ink-faint)]">
              <span class="font-mono">{{ job.partition_values.join(' / ') }}</span>
              <span>{{ job.created_at }}</span>
            </div>
          </button>
          <div v-if="!jobStore.items.length" class="px-4 py-10 text-center text-[11.5px] text-[var(--ink-faint)]">
            还没有合并任务。先到湖表分区明细生成计划并提交执行。
          </div>
        </div>
      </section>

      <main class="min-w-0 space-y-4" data-test="job-detail">
        <template v-if="selected">
          <JobProgress :job="selected" />
          <div class="grid gap-4 md:grid-cols-2">
            <div class="bp-frame">
              <div class="bp-frame__head"><span class="label">关联计划</span></div>
              <div class="bp-frame__body space-y-1.5 text-[11.5px]">
                <div class="flex items-center justify-between">
                  <span class="text-[var(--ink-soft)]">计划 ID</span><span class="num">#{{ selected.plan_id }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-[var(--ink-soft)]">策略</span><span class="font-mono text-[11px]">{{ selected.strategy }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-[var(--ink-soft)]">分区</span><span class="font-mono text-[11px]">{{ selected.partition_values.join(', ') }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-[var(--ink-soft)]">指纹</span><span class="font-mono text-[10px]">{{ selected.fingerprint }}</span>
                </div>
              </div>
            </div>
            <div class="bp-frame">
              <div class="bp-frame__head"><span class="label">下一步</span></div>
              <div class="bp-frame__body">
                <div v-if="selected.snapshot_id" class="text-[11.5px]">
                  任务已生成快照 <span class="num">#{{ selected.snapshot_id }}</span>，
                  可以去快照校验页对比前后 manifest、确认行数守恒。
                </div>
                <div v-else-if="selected.status === 'failed'" class="text-[11.5px]">
                  任务失败，可查看失败原因后重试；同一湖表的并发任务会被锁拦截。
                </div>
                <div v-else class="text-[11.5px] text-[var(--ink-soft)]">
                  worker 正在逐组重写 manifest，完成后自动生成快照并做守恒校验。
                </div>
                <div class="mt-3 flex flex-wrap gap-2">
                  <RouterLink
                    v-if="selected.snapshot_id"
                    :to="{ path: '/snapshots', query: { table: String(selected.table_id) } }"
                    class="bp-btn bp-btn--solid"
                  >
                    查看快照 diff
                  </RouterLink>
                  <button
                    v-if="selected.status === 'failed' && auth.canWrite"
                    class="bp-btn bp-btn--danger"
                    data-test="retry-job"
                    @click="retry"
                  >
                    重试任务
                  </button>
                  <RouterLink
                    v-if="selected.table_id"
                    :to="`/tables/${selected.table_id}`"
                    class="bp-btn"
                  >
                    返回分区
                  </RouterLink>
                </div>
              </div>
            </div>
          </div>
        </template>
        <EmptyState
          v-else
          title="尚未选择任务"
          description="左侧任务台账会列出当前湖表的合并任务；提交计划后这里会自动出现执行进度。"
        />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import EmptyState from '../components/common/EmptyState.vue'
import StatusTag from '../components/common/StatusTag.vue'
import JobProgress from '../components/common/JobProgress.vue'
import { useJobStore } from '../stores/jobStore'
import { useAuthStore } from '../stores/authStore'
import { useJobPolling } from '../hooks/useJobPolling'

const route = useRoute()
const router = useRouter()
const jobStore = useJobStore()
const auth = useAuthStore()

const selected = computed(() => jobStore.selected)
const selectedId = computed(() => selected.value?.id ?? null)

const polling = useJobPolling(async () => jobStore.load(), 1200)

onMounted(async () => {
  await jobStore.load()
  const queryJob = Number(route.query.job)
  if (queryJob) jobStore.select(queryJob)
  if (jobStore.hasActive) polling.start()
})

watch(
  () => jobStore.hasActive,
  (active) => {
    if (active) polling.start()
    else polling.stop()
  },
)

function select(jobId: number) {
  jobStore.select(jobId)
  if (route.query.job !== String(jobId)) {
    router.replace({ path: '/jobs', query: { ...route.query, job: String(jobId) } })
  }
}

async function refresh() {
  await jobStore.load()
}

async function retry() {
  if (!selected.value) return
  await jobStore.retry(selected.value.id)
  polling.start()
}
</script>
