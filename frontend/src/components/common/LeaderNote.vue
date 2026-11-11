<template>
  <div class="leader-note">
    <div v-if="label" class="label mb-1">{{ label }}</div>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ label?: string }>()
</script>
