<template>
  <div class="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--rule)] pb-3">
    <div class="min-w-0">
      <div class="flex items-center gap-3">
        <span class="label">{{ figure }}</span>
        <span class="h-px w-8 bg-[var(--rule)]"></span>
        <span class="eyebrow">{{ section }}</span>
      </div>
      <h1 class="display mt-1.5">{{ title }}</h1>
      <p v-if="description" class="mt-1.5 max-w-[720px] text-[12px] leading-relaxed text-[var(--ink-soft)]">
        {{ description }}
      </p>
    </div>
    <div class="flex items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ figure: string; section: string; title: string; description?: string }>()
</script>
