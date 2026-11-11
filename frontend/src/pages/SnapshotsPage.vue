<template>
  <div>
    <PageHeader
      figure="FIG.05"
      section="snapshot audit"
      :title="'快照 diff 与守恒校验'"
      description="两版 manifest 逐路径对比：合并只允许新增产物 + 移除小文件，changed 必须为 0，Σrows 必须前后一致。"
    >
      <template #actions>
        <select v-model.number="tableId" class="bp-select w-[172px]" data-test="snapshot-table-select">
          <option v-for="item in tableStore.items" :key="item.id" :value="item.id">
            {{ item.db_name }}.{{ item.table_name }}
          </option>
        </select>
        <button
          v-if="auth.canWrite"
          class="bp-btn"
          :disabled="!tableId"
          data-test="create-snapshot"
          @click="createSnapshot"
        >
          创建快照
        </button>
      </template>
    </PageHeader>

    <ErrorNotice :error="snapshotStore.error" />

    <div class="mt-4 grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
      <section class="bp-frame">
        <div class="bp-frame__head">
          <span class="label">快照清单</span>
          <span class="num text-[10.5px]">{{ snapshotStore.items.length }} 版</span>
        </div>
        <div class="max-h-[300px] overflow-auto">
          <div
            v-for="snapshot in snapshotStore.items"
            :key="snapshot.id"
            class="border-b border-[var(--rule-soft)] px-3 py-2.5 last:border-b-0"
            :data-test="`snapshot-row-${snapshot.version}`"
          >
            <div class="flex items-center gap-2.5">
              <span class="font-display text-[12.5px]">v{{ snapshot.version }}</span>
              <span class="num text-[10.5px] text-[var(--ink-soft)]">{{ snapshot.file_count }} 文件 / {{ snapshot.total_rows.toLocaleString() }} 行</span>
              <span
                v-if="snapshot.verification?.row_conserved !== undefined"
                class="bp-tag ml-auto"
                :class="snapshot.verification.row_conserved ? 'bp-tag--ok' : 'bp-tag--hot'"
              >
                {{ snapshot.verification.row_conserved ? '守恒' : '不守恒' }}
              </span>
            </div>
            <div class="mt-1 flex items-center justify-between text-[10px] text-[var(--ink-faint)]">
              <span class="font-mono">sha {{ snapshot.checksum.slice(0, 12) }}</span>
              <span>{{ snapshot.created_at }}</span>
            </div>
            <div class="mt-1 text-[10.5px] text-[var(--ink-soft)]">{{ snapshot.note }}</div>
          </div>
          <div v-if="!snapshotStore.items.length" class="px-4 py-10 text-center text-[11.5px] text-[var(--ink-faint)]">
            该湖表还没有快照。
          </div>
        </div>
        <div class="bp-frame__body border-t border-[var(--rule-soft)] !py-2.5">
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="label block mb-1">基线</label>
              <select v-model.number="snapshotStore.leftId" class="bp-select" data-test="snapshot-left">
                <option :value="null" disabled>选择</option>
                <option v-for="item in snapshotStore.items" :key="item.id" :value="item.id">v{{ item.version }}</option>
              </select>
            </div>
            <div>
              <label class="label block mb-1">对比</label>
              <select v-model.number="snapshotStore.rightId" class="bp-select" data-test="snapshot-right">
                <option :value="null" disabled>选择</option>
                <option v-for="item in snapshotStore.items" :key="item.id" :value="item.id">v{{ item.version }}</option>
              </select>
            </div>
          </div>
          <button
            class="bp-btn mt-2.5 w-full justify-center"
            :disabled="snapshotStore.leftId === null || snapshotStore.rightId === null || snapshotStore.diffing"
            data-test="snapshot-diff-btn"
            @click="compare"
          >
            {{ snapshotStore.diffing ? '对比中…' : '计算 diff' }}
          </button>
        </div>
      </section>

      <main class="min-w-0" data-test="snapshot-diff-panel">
        <SnapshotDiffTable v-if="snapshotStore.diff" :result="snapshotStore.diff" />
        <EmptyState
          v-else
          title="等待选择快照"
          description="默认对比「上一版 → 最新版」。第一次合并由 worker 自动生成快照，之后即可看到 added / removed / changed 与行数守恒结论。"
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
import SnapshotDiffTable from '../components/common/SnapshotDiffTable.vue'
import { useSnapshotStore } from '../stores/snapshotStore'
import { useTableStore } from '../stores/tableStore'
import { useAuthStore } from '../stores/authStore'

const route = useRoute()
const router = useRouter()
const tableStore = useTableStore()
const snapshotStore = useSnapshotStore()
const auth = useAuthStore()

const tableId = computed({
  get: () => Number(route.query.table) || defaultTableId(),
  set: (value: number) => {
    router.replace({ path: '/snapshots', query: { ...route.query, table: String(value) } })
  },
})

function defaultTableId(): number {
  const ods = tableStore.items.find((item) => item.db_name === 'ods')
  return ods?.id ?? tableStore.items[0]?.id ?? 0
}

async function loadSnapshots(value: number) {
  if (!value) return
  await snapshotStore.load(value)
  if (snapshotStore.items.length >= 2) {
    await snapshotStore.compare()
  }
}

async function compare() {
  await snapshotStore.compare()
}

async function createSnapshot() {
  if (!tableId.value) return
  await snapshotStore.create(tableId.value, '手工创建快照（UI）')
  if (snapshotStore.items.length >= 2) await snapshotStore.compare()
}

onMounted(async () => {
  if (!tableStore.items.length) await tableStore.load()
  const queryId = Number(route.query.table)
  const target = queryId || defaultTableId()
  if (target) {
    await loadSnapshots(target)
  }
})

watch(
  () => route.query.table,
  (value) => {
    const id = Number(value)
    if (id && !snapshotStore.loading) loadSnapshots(id)
  },
)
</script>
