<template>
  <div class="border border-dashed border-[var(--rule)] px-6 py-10 text-center">
    <div class="mx-auto mb-3 h-8 w-8 border border-[var(--rule)] relative">
      <span class="absolute inset-0 flex items-center justify-center text-[var(--ink-faint)]">+</span>
    </div>
    <div class="display-sm">{{ title }}</div>
    <p class="mx-auto mt-2 max-w-[420px] text-[12px] text-[var(--ink-soft)]">{{ description }}</p>
    <div v-if="$slots.default" class="mt-4"><slot /></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; description: string }>()
</script>
