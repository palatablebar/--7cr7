<template>
  <div class="app-shell grid min-h-screen" :class="collapsed ? 'grid-cols-[72px_1fr]' : 'grid-cols-[252px_1fr]'">
    <aside class="app-rail border-r border-[var(--rule-soft)] bg-[var(--paper-2)] min-h-screen flex flex-col">
      <div class="px-4 pt-5 pb-4">
        <div v-if="!collapsed" class="flex items-start justify-between">
          <div>
            <div class="display-sm tracking-[0.03em]">LAKEPACK</div>
            <div class="eyebrow mt-1.5">lake compaction workshop</div>
          </div>
          <div class="label !text-[9px]">FIG.00</div>
        </div>
        <div v-else class="display-sm text-center">LP</div>
        <div v-if="!collapsed" class="mt-3 text-[10.5px] leading-relaxed text-[var(--ink-soft)]">
          数据湖小文件合并<br />与分区整理工坊
        </div>
      </div>

      <div class="hr mx-4"></div>

      <nav class="mt-2 flex-1">
        <template v-if="!collapsed">
          <div class="eyebrow px-4 py-2">workspace</div>
          <RouterLink to="/tables" class="rail-link" active-class="active">
            <span class="flex items-baseline gap-2">
              <span class="rail-link__index">§01</span>
              <span>湖表总览</span>
            </span>
            <span class="text-[10.5px] num">{{ tableStore.items.length }}</span>
          </RouterLink>
          <RouterLink to="/jobs" class="rail-link" active-class="active">
            <span class="flex items-baseline gap-2">
              <span class="rail-link__index">§02</span>
              <span>任务执行监控</span>
            </span>
          </RouterLink>
          <RouterLink to="/snapshots" class="rail-link" active-class="active">
            <span class="flex items-baseline gap-2">
              <span class="rail-link__index">§03</span>
              <span>快照 diff 与校验</span>
            </span>
          </RouterLink>

          <div class="eyebrow px-4 py-2 mt-4">context</div>
          <div class="px-4 py-1 text-[10.5px] leading-relaxed text-[var(--ink-soft)]">
            S3 兼容对象存储<br />
            40TB · Parquet 表 60 张
          </div>
          <div v-if="tableStore.summary" class="mx-4 mt-3 border border-[var(--rule-soft)] px-3 py-2">
            <div class="label">小文件 / 可回收</div>
            <div class="mt-1 flex items-baseline gap-2">
              <span class="num text-[19px] leading-none">{{ tableStore.summary.small_file_count }}</span>
              <span class="text-[10.5px] text-[var(--ink-faint)]">→ 省 {{ tableStore.summary.reclaimable_file_count }}</span>
            </div>
            <div class="mt-2 flex items-center gap-2 text-[10.5px] text-[var(--ink-soft)]">
              <span class="label !text-[9px]">待整理分区</span>
              <span class="num">{{ tableStore.summary.pending_partition_count }}</span>
            </div>
          </div>
        </template>
        <template v-else>
          <RouterLink to="/tables" class="rail-link !justify-center !px-0" active-class="active" title="湖表总览">§1</RouterLink>
          <RouterLink to="/jobs" class="rail-link !justify-center !px-0" active-class="active" title="任务监控">§2</RouterLink>
          <RouterLink to="/snapshots" class="rail-link !justify-center !px-0" active-class="active" title="快照校验">§3</RouterLink>
        </template>
      </nav>

      <div class="px-4 pb-4">
        <div class="hr-ink mb-3"></div>
        <template v-if="!collapsed">
          <div class="text-[12px]">{{ auth.displayName || '未登录' }}</div>
          <div class="text-[10.5px] text-[var(--ink-soft)] mt-0.5">{{ roleLabel }}</div>
          <div class="mt-3">
            <div class="flex items-center justify-between">
              <span class="label">今日计划配额</span>
              <span class="num text-[10.5px]">{{ auth.quotaRemaining }} / {{ quotaTotal }}</span>
            </div>
            <div class="meter mt-1.5">
              <div class="meter__fill" :style="{ width: quotaWidth }"></div>
            </div>
          </div>
        </template>
        <div class="flex items-center justify-between mt-3">
          <button class="bp-btn bp-btn--quiet !px-2 !py-1" @click="collapsed = !collapsed">
            {{ collapsed ? '»' : '«' }}
          </button>
          <button class="bp-btn bp-btn--quiet !px-2 !py-1" data-test="logout" @click="logout">退出</button>
        </div>
      </div>
    </aside>

    <main class="min-w-0 flex flex-col">
      <header class="border-b border-[var(--rule-soft)] bg-[var(--paper-2)] px-6 py-2.5 flex items-center justify-between">
        <div class="flex items-center gap-3 text-[10.5px] text-[var(--ink-soft)]">
          <span class="label">拾光内容平台 · 离线数仓小队</span>
          <span class="text-[var(--ink-faint)]">/</span>
          <span>{{ route.meta.title ?? '工作台' }}</span>
        </div>
        <div class="flex items-center gap-4 text-[10px] text-[var(--ink-faint)] uppercase tracking-label">
          <span>rev. 2026-11-10</span>
          <span class="hidden md:inline">sheet 1 / 1</span>
        </div>
      </header>
      <div class="app-body px-6 py-6 flex-1">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ROLE_LABELS } from '../../types/user'
import { useAuthStore } from '../../stores/authStore'
import { useTableStore } from '../../stores/tableStore'

const collapsed = ref(false)
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tableStore = useTableStore()

const roleLabel = computed(() => ROLE_LABELS[auth.role] ?? auth.role)
const quotaTotal = computed(() => auth.quota?.daily_plan_quota ?? auth.user?.daily_plan_quota ?? 0)
const quotaWidth = computed(() => {
  const total = quotaTotal.value
  if (!total) return '0%'
  const used = auth.quota?.plan_used ?? auth.user?.plan_used ?? 0
  return `${Math.min(100, Math.round((used / total) * 100))}%`
})

onMounted(async () => {
  if (!auth.user) await auth.restore()
  if (!tableStore.items.length) await tableStore.load()
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>
