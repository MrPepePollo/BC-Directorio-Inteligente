<script setup lang="ts">
import { SearchX } from 'lucide-vue-next'

interface Props {
  title?: string
  description?: string
}

withDefaults(defineProps<Props>(), {
  title: 'No se encontraron resultados',
  description: 'Intenta ajustar los filtros o crear un nuevo registro.',
})
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 text-center">
    <div class="w-12 h-12 rounded-full bg-surface-secondary flex items-center justify-center mb-4">
      <SearchX class="w-6 h-6 text-text-muted" />
    </div>
    <h3 class="text-lg font-medium text-text-primary mb-1">{{ title }}</h3>
    <p class="text-sm text-text-muted max-w-sm">{{ description }}</p>
    <div class="mt-4">
      <slot />
    </div>
  </div>
</template>
