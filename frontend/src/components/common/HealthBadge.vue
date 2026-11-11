<template>
  <span class="bp-tag" :class="HEALTH_BAND_TAG[band]">
    {{ showScore && score !== undefined ? `${HEALTH_BAND_LABELS[band]} ${score}` : HEALTH_BAND_LABELS[band] }}
  </span>
</template>

<script setup lang="ts">
import { HEALTH_BAND_LABELS, HEALTH_BAND_TAG } from '../../constants/healthBand'
import type { HealthBand } from '../../types/table'

withDefaults(defineProps<{ band: HealthBand; score?: number; showScore?: boolean }>(), {
  score: undefined,
  showScore: true,
})
</script>
