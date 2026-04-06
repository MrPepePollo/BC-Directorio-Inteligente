<script setup lang="ts">
interface Props {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
})
</script>

<template>
  <button
    :disabled="disabled || loading"
    :class="[
      'inline-flex items-center justify-center gap-2 rounded-xl border font-semibold tracking-[-0.01em] transition-[transform,background-color,border-color,box-shadow,color] duration-200 cursor-pointer',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:translate-y-0 disabled:shadow-none',
      {
        'border-transparent bg-linear-to-b from-primary-500 to-primary-600 text-white shadow-[0_24px_60px_-28px_rgb(46_108_234_/_0.42)] hover:-translate-y-0.5 hover:from-primary-400 hover:to-primary-600 active:translate-y-0': variant === 'primary',
        'border-border bg-surface-elevated text-text-primary shadow-[0_16px_36px_-24px_rgb(18_45_96_/_0.18)] hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-hover': variant === 'secondary',
        'border-transparent bg-transparent text-text-secondary hover:bg-surface-hover hover:text-text-primary': variant === 'ghost',
        'border-transparent bg-danger text-white shadow-[0_22px_44px_-26px_rgb(189_63_28_/_0.38)] hover:-translate-y-0.5 hover:brightness-105': variant === 'danger',
        'px-3.5 py-2 text-sm': size === 'sm',
        'px-4 py-2.5 text-sm': size === 'md',
        'px-6 py-3 text-base': size === 'lg',
      },
    ]"
  >
    <svg
      v-if="loading"
      class="animate-spin -ml-1 h-4 w-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
    <slot />
  </button>
</template>
