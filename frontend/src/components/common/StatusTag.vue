<template>
  <span class="bp-tag" :class="tone">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { JOB_STATUS_LABELS } from '../../constants/jobStatus'
import { PLAN_STATUS_LABELS } from '../../constants/planStatus'

const props = defineProps<{ status: string; kind?: 'job' | 'plan' }>()
const label = computed(() => {
  if (props.kind === 'plan') return PLAN_STATUS_LABELS[props.status] ?? props.status
  return JOB_STATUS_LABELS[props.status as keyof typeof JOB_STATUS_LABELS] ?? props.status
})
const tone = computed(() => {
  if (props.status === 'succeeded' || props.status === 'completed') return 'bp-tag--ok'
  if (props.status === 'failed') return 'bp-tag--hot'
  if (props.status === 'running' || props.status === 'executing') return 'bp-tag--watch'
  return 'bp-tag--muted'
})
</script>
