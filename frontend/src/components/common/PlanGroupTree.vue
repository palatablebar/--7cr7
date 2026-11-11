<template>
  <div class="bp-frame">
    <div class="bp-frame__head">
      <span class="label">分组树 / FFD packing groups</span>
      <span class="num text-[10.5px] text-[var(--ink-soft)]">{{ groups.length }} 组</span>
    </div>
    <div class="max-h-[520px] overflow-auto">
      <div v-for="group in groups" :key="group.group_id" class="border-b border-[var(--rule-soft)] last:border-b-0">
        <button
          class="w-full text-left px-3.5 py-2.5 hover:bg-[var(--paper)] transition-colors"
          :data-test="`group-${group.group_id}`"
          @click="toggle(group.group_id)"
        >
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span class="font-display text-[13px]">{{ group.group_id }}</span>
            <span class="label">{{ partitionKey }}={{ group.partition_value }}</span>
            <span class="bp-tag" :class="group.action === 'rewrite' ? 'bp-tag--watch' : 'bp-tag--muted'">
              {{ group.action === 'rewrite' ? '重写' : '保持' }}
            </span>
            <span v-if="group.risk === 'hot'" class="bp-tag bp-tag--hot">HOT</span>
            <span class="ml-auto num text-[11.5px]">
              {{ group.file_count }} → {{ group.action === 'rewrite' ? 1 : 1 }} 文件 · {{ group.packed_size_mb }} MB
            </span>
          </div>
          <div class="mt-1.5 flex items-center gap-3">
            <div class="meter flex-1">
              <div
                class="meter__fill"
                :class="group.fill_ratio > 0.93 ? 'meter__fill--watch' : ''"
                :style="{ width: `${Math.min(100, Math.round(group.fill_ratio * 100))}%` }"
              ></div>
            </div>
            <span class="label w-[64px] text-right">填充 {{ Math.round(group.fill_ratio * 100) }}%</span>
          </div>
        </button>
        <div v-if="expanded.has(group.group_id)" class="border-t border-dotted border-[var(--rule-soft)] bg-[var(--paper-2)] px-3.5 py-2">
          <div class="label mb-1.5">输入文件 · {{ group.file_count }}</div>
          <div class="space-y-1">
            <div
              v-for="file in group.files.slice(0, 12)"
              :key="file.path"
              class="flex items-baseline gap-2 text-[10.5px] text-[var(--ink-soft)]"
            >
              <span class="truncate flex-1 font-mono">{{ file.path.split('/').pop() }}</span>
              <span class="num w-[64px]">{{ file.size_mb }} MB</span>
              <span class="num w-[84px] text-[var(--ink-faint)]">{{ file.row_count.toLocaleString() }} 行</span>
            </div>
            <div v-if="group.files.length > 12" class="text-[10px] text-[var(--ink-faint)]">
              … 其余 {{ group.files.length - 12 }} 个文件
            </div>
          </div>
          <div class="mt-2 tick-top text-[10.5px] text-[var(--ink-soft)]">
            产出 → <span class="font-mono">{{ group.output_file.split('/').pop() }}</span>
            · {{ group.output_rows.toLocaleString() }} 行
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { PlanGroup } from '../../types/plan'

const props = defineProps<{ groups: PlanGroup[]; partitionKey: string }>()
const expanded = ref<Set<string>>(new Set(props.groups.filter((g) => g.action === 'rewrite').slice(0, 2).map((g) => g.group_id)))

function toggle(groupId: string) {
  const next = new Set(expanded.value)
  if (next.has(groupId)) next.delete(groupId)
  else next.add(groupId)
  expanded.value = next
}
</script>
