<script setup lang="ts">
interface Props {
  hoverable?: boolean
}

withDefaults(defineProps<Props>(), {
  hoverable: false,
})
</script>

<template>
  <div
    :class="[
      'app-panel rounded-[1.4rem] p-5',
      hoverable &&
        'cursor-pointer transition-[transform,border-color,box-shadow,background-color] duration-200 hover:-translate-y-1 hover:border-primary-300 hover:shadow-[0_32px_72px_-38px_rgb(18_45_96_/_0.28)] dark:hover:shadow-[0_38px_90px_-42px_rgb(4_9_27_/_0.85)]',
    ]"
  >
    <slot />
  </div>
</template>
