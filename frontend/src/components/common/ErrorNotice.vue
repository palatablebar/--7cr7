<template>
  <div v-if="message" class="mt-3 flex items-start gap-2 border-l-2 border-[var(--rust)] bg-[color-mix(in_oklch,var(--rust)_7%,transparent)] px-3 py-2 text-[12px]">
    <span class="mt-0.5 text-[10px] uppercase tracking-label text-[var(--rust)]">ERR</span>
    <div class="text-[var(--ink)]">
      {{ message }}
      <span v-if="code" class="ml-2 text-[10.5px] text-[var(--ink-faint)]">{{ code }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ApiError } from '../../types/api'

const props = defineProps<{ error: ApiError | string | null }>()
const message = computed(() => {
  if (!props.error) return ''
  return typeof props.error === 'string' ? props.error : props.error.message
})
const code = computed(() => (typeof props.error === 'string' || !props.error ? '' : props.error.code))
</script>
