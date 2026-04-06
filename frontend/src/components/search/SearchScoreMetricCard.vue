<script setup lang="ts">
import { computed } from 'vue'
import AppBadge from '@/components/ui/AppBadge.vue'

interface Props {
  label: string
  score: number
  description: string
}

const props = defineProps<Props>()

const percentage = computed(() => `${Math.round(props.score * 100)}%`)

const strengthLabel = computed(() => {
  if (props.score >= 0.7) return 'Fuerte'
  if (props.score >= 0.45) return 'Clara'
  return 'Moderada'
})

const badgeVariant = computed(() => {
  if (props.score >= 0.7) return 'success' as const
  if (props.score >= 0.45) return 'primary' as const
  return 'info' as const
})

const surfaceClass = computed(() => {
  if (props.score >= 0.7) {
    return 'border-emerald-200/85 bg-[linear-gradient(180deg,rgba(240,253,244,0.96),rgba(220,252,231,0.92))] dark:border-emerald-900/80 dark:bg-[linear-gradient(180deg,rgba(6,28,20,0.98),rgba(8,44,31,0.95))]'
  }

  if (props.score >= 0.45) {
    return 'border-primary-200/85 bg-[linear-gradient(180deg,rgba(239,246,255,0.96),rgba(226,239,255,0.92))] dark:border-primary-900/80 dark:bg-[linear-gradient(180deg,rgba(10,22,42,0.98),rgba(13,31,58,0.95))]'
  }

  return 'border-sky-200/85 bg-[linear-gradient(180deg,rgba(240,249,255,0.96),rgba(224,242,254,0.92))] dark:border-sky-950/80 dark:bg-[linear-gradient(180deg,rgba(8,22,37,0.98),rgba(10,34,52,0.95))]'
})

const trackClass = computed(() => {
  if (props.score >= 0.7) {
    return 'bg-linear-to-r from-emerald-400 to-emerald-500 dark:from-emerald-300 dark:to-teal-300'
  }

  if (props.score >= 0.45) {
    return 'bg-linear-to-r from-primary-400 to-primary-600 dark:from-primary-300 dark:to-sky-300'
  }

  return 'bg-linear-to-r from-sky-400 to-sky-600 dark:from-sky-300 dark:to-cyan-300'
})
</script>

<template>
  <div
    :class="[
      'rounded-[1.25rem] border p-4 shadow-[0_18px_40px_-32px_rgb(18_45_96_/_0.2)] dark:shadow-[0_22px_54px_-36px_rgb(2_8_24_/_0.7)]',
      surfaceClass,
    ]"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
          {{ label }}
        </p>
        <p class="mt-2 text-2xl font-semibold text-text-primary">
          {{ percentage }}
        </p>
      </div>

      <AppBadge :variant="badgeVariant">
        {{ strengthLabel }}
      </AppBadge>
    </div>

    <div class="mt-4 h-2 overflow-hidden rounded-full bg-white/70 dark:bg-black/25">
      <div
        :class="['h-full rounded-full transition-[width] duration-300', trackClass]"
        :style="{ width: `${Math.max(8, Math.round(score * 100))}%` }"
      />
    </div>

    <p class="mt-3 text-sm leading-7 text-text-secondary">
      {{ description }}
    </p>
  </div>
</template>
