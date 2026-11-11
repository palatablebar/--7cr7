<template>
  <div class="space-y-4">
    <div class="grid gap-4 md:grid-cols-[1.15fr_1fr]">
      <div class="bp-frame">
        <div class="bp-frame__head">
          <span class="label">manifest diff</span>
          <span class="label">v{{ result.left.version }} → v{{ result.right.version }}</span>
        </div>
        <div class="bp-frame__body">
          <div class="grid grid-cols-3 gap-3">
            <div>
              <div class="label">added</div>
              <div class="num text-[24px] leading-tight text-[var(--sea)]">+{{ data.added_count }}</div>
            </div>
            <div>
              <div class="label">removed</div>
              <div class="num text-[24px] leading-tight text-[var(--rust)]">−{{ data.removed_count }}</div>
            </div>
            <div>
              <div class="label">changed</div>
              <div class="num text-[24px] leading-tight">{{ data.changed_count }}</div>
            </div>
          </div>
          <div class="mt-3 hr"></div>
          <div class="mt-3 space-y-2 text-[11.5px]">
            <div class="flex items-center justify-between">
              <span class="text-[var(--ink-soft)]">文件数</span>
              <span class="num">{{ data.file_count_before }} → {{ data.file_count_after }} ({{ signed(data.file_count_delta) }})</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-[var(--ink-soft)]">总大小</span>
              <span class="num">{{ formatBytes(data.size_before_bytes) }} → {{ formatBytes(data.size_after_bytes) }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-[var(--ink-soft)]">Σrows</span>
              <span class="num">{{ formatCount(data.rows_before) }} → {{ formatCount(data.rows_after) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="bp-frame">
        <div class="bp-frame__head"><span class="label">守恒校验 / conservation</span></div>
        <div class="bp-frame__body">
          <div class="space-y-2.5">
            <div class="flex items-center justify-between border-b border-dotted border-[var(--rule-soft)] pb-2">
              <span class="text-[11.5px]">行数守恒</span>
              <span class="bp-tag" :class="data.row_conserved ? 'bp-tag--ok' : 'bp-tag--hot'">
                {{ data.row_conserved ? 'OK' : `Δ ${signed(data.row_delta)}` }}
              </span>
            </div>
            <div class="flex items-center justify-between border-b border-dotted border-[var(--rule-soft)] pb-2">
              <span class="text-[11.5px]">checksum 一致</span>
              <span class="bp-tag" :class="data.checksum_ok ? 'bp-tag--ok' : 'bp-tag--hot'">
                {{ data.checksum_ok ? 'OK' : `${data.checksum_mismatches.length} 处不一致` }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-[11.5px]">总体结论</span>
              <span class="bp-tag" :class="data.conservation_ok ? 'bp-tag--ok' : 'bp-tag--hot'">
                {{ data.conservation_ok ? '可审计' : '需人工复核' }}
              </span>
            </div>
          </div>
          <div class="leader-note mt-4">
            合并只改变文件组织方式：新增合并产物、移除原始小文件；行数 Σrows 必须前后一致，
            同路径 checksum 不允许变化。changed 应恒为 0。
          </div>
        </div>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-2">
      <div class="bp-frame">
        <div class="bp-frame__head">
          <span class="label">added · 合并产物</span>
          <span class="num text-[10.5px]">{{ data.added_count }}</span>
        </div>
        <div class="max-h-[240px] overflow-auto p-3">
          <div v-for="item in data.added.slice(0, 12)" :key="item.path" class="mb-1.5 flex items-baseline gap-2 text-[10.5px]">
            <span class="w-9 shrink-0 text-[var(--sea)]">+</span>
            <span class="truncate font-mono text-[var(--ink)]">{{ shortPath(item.path) }}</span>
            <span class="ml-auto num shrink-0 text-[var(--ink-soft)]">{{ formatBytes(item.size_bytes) }}</span>
          </div>
          <div v-if="!data.added.length" class="text-[11px] text-[var(--ink-faint)]">无新增文件</div>
        </div>
      </div>
      <div class="bp-frame">
        <div class="bp-frame__head">
          <span class="label">removed · 原始小文件</span>
          <span class="num text-[10.5px]">{{ data.removed_count }}</span>
        </div>
        <div class="max-h-[240px] overflow-auto p-3">
          <div v-for="item in data.removed.slice(0, 12)" :key="item.path" class="mb-1.5 flex items-baseline gap-2 text-[10.5px]">
            <span class="w-9 shrink-0 text-[var(--rust)]">−</span>
            <span class="truncate font-mono text-[var(--ink)]">{{ shortPath(item.path) }}</span>
            <span class="ml-auto num shrink-0 text-[var(--ink-soft)]">{{ formatBytes(item.size_bytes) }}</span>
          </div>
          <div v-if="!data.removed.length" class="text-[11px] text-[var(--ink-faint)]">无移除文件</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SnapshotDiffResult } from '../../types/snapshot'
import { formatBytes, formatCount } from '../../utils/formatBytes'

const props = defineProps<{ result: SnapshotDiffResult }>()
const data = computed(() => props.result.diff)

function shortPath(path: string): string {
  const parts = path.split('/')
  return parts.slice(-2).join('/')
}

function signed(value: number): string {
  if (value > 0) return `+${value}`
  return `${value}`
}
</script>
