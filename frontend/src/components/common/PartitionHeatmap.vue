<template>
  <div class="flex flex-wrap gap-1" :class="compact ? '' : 'gap-1.5'">
    <div
      v-for="item in partitions"
      :key="item.partition_value"
      class="heat-cell"
      :class="[`heat-cell--${item.health_band}`, compact ? 'heat-cell--compact' : '']"
      :title="`dt=${item.partition_value} · ${item.file_count} 文件 / ${item.small_file_count} 小文件 · 健康度 ${item.health_score}`"
      :data-test="`heat-${item.partition_value}`"
    >
      <span class="heat-cell__score num">{{ item.health_score }}</span>
      <span class="heat-cell__label">…{{ item.partition_value.slice(-4) }}</span>
    </div>
    <div v-if="!partitions.length" class="text-[11px] text-[var(--ink-faint)]">暂无分区</div>
  </div>
</template>

<script setup lang="ts">
import type { PartitionSpec } from '../../types/table'

withDefaults(defineProps<{ partitions: PartitionSpec[]; compact?: boolean }>(), { compact: false })
</script>

<style scoped>
.heat-cell {
  width: 46px;
  height: 38px;
  border: 1px solid var(--rule-soft);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  transition: transform 160ms var(--ease), border-color 160ms var(--ease);
}
.heat-cell:hover {
  transform: translateY(-1px);
  border-color: var(--rule);
}
.heat-cell--compact {
  width: 34px;
  height: 26px;
}
.heat-cell__score {
  font-size: 12px;
  line-height: 1;
  color: var(--ink);
}
.heat-cell--compact .heat-cell__score {
  font-size: 10px;
}
.heat-cell__label {
  font-size: 8.5px;
  letter-spacing: 0.04em;
  color: var(--ink-soft);
  line-height: 1;
}
.heat-cell--healthy {
  background: color-mix(in oklch, var(--sea) 16%, var(--paper-2));
  border-color: color-mix(in oklch, var(--sea) 46%, var(--rule-soft));
}
.heat-cell--watch {
  background: color-mix(in oklch, var(--ochre) 20%, var(--paper-2));
  border-color: color-mix(in oklch, var(--ochre) 52%, var(--rule-soft));
}
.heat-cell--degraded {
  background: color-mix(in oklch, var(--rust) 18%, var(--paper-2));
  border-color: color-mix(in oklch, var(--rust) 48%, var(--rule-soft));
}
</style>
