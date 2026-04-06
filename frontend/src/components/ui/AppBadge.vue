<script setup lang="ts">
interface Props {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'ai' | 'info'
}

withDefaults(defineProps<Props>(), {
  variant: 'default',
})
</script>

<template>
  <span
    :class="[
      'inline-flex whitespace-nowrap items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-[0.01em] shadow-[0_10px_24px_-20px_rgb(17_31_67_/_0.3)]',
      {
        'border-border bg-surface-secondary text-text-secondary': variant === 'default',
        'border-primary-200 bg-primary-100 text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300': variant === 'primary',
        'border-green-200 bg-green-100 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300': variant === 'success',
        'border-amber-200 bg-amber-100 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300': variant === 'warning',
        'border-ai-300 bg-ai-100 text-ai-700 dark:border-ai-900 dark:bg-ai-900 dark:text-ai-100': variant === 'ai',
        'border-sky-200 bg-sky-100 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-300': variant === 'info',
      },
    ]"
  >
    <slot />
  </span>
</template>
