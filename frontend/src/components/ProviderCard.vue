<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { MapPin, Globe, Sparkles } from 'lucide-vue-next'
import AppBadge from '@/components/ui/AppBadge.vue'
import type { Provider } from '@/types/provider'

defineProps<{
  provider: Provider
}>()
</script>

<template>
  <RouterLink
    :to="`/providers/${provider.id}`"
    class="app-panel group block h-full rounded-[1.45rem] p-5 transition-[transform,border-color,box-shadow,background-color] duration-200 hover:-translate-y-1 hover:border-primary-300 hover:shadow-[0_32px_72px_-38px_rgb(18_45_96_/_0.28)] dark:hover:shadow-[0_38px_90px_-42px_rgb(4_9_27_/_0.85)]"
  >
    <!-- Header -->
    <div class="mb-4 flex items-start justify-between gap-3">
      <div class="space-y-2">
        <span class="inline-flex rounded-full border border-primary-200 bg-primary-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300">
          proveedor
        </span>
        <h3 class="line-clamp-1 text-lg font-semibold text-text-primary">{{ provider.name }}</h3>
      </div>
      <div
        v-if="provider.website"
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-border bg-surface-secondary text-text-muted transition-colors duration-200 group-hover:border-primary-200 group-hover:text-primary-500"
      >
        <Globe class="w-4 h-4" />
      </div>
    </div>

    <!-- Description -->
    <p class="mb-4 line-clamp-3 text-sm leading-6 text-text-secondary">
      {{ provider.description }}
    </p>

    <!-- Location -->
    <div
      v-if="provider.city || provider.country"
      class="mb-4 flex items-center gap-1.5 text-xs font-medium text-text-muted"
    >
      <MapPin class="w-3 h-3" />
      <span>{{ [provider.city, provider.country].filter(Boolean).join(', ') }}</span>
    </div>

    <!-- Categories -->
    <div v-if="provider.categories.length" class="mb-3 flex flex-wrap gap-2">
      <AppBadge
        v-for="pc in provider.categories.slice(0, 3)"
        :key="pc.category.id"
        :variant="pc.source === 'ai' ? 'ai' : 'primary'"
      >
        <Sparkles v-if="pc.source === 'ai'" class="w-3 h-3" />
        {{ pc.category.name }}
      </AppBadge>
    </div>

    <!-- Tags -->
    <div v-if="provider.tags.length" class="flex flex-wrap gap-2">
      <AppBadge
        v-for="pt in provider.tags.slice(0, 4)"
        :key="pt.tag.id"
      >
        {{ pt.tag.name }}
      </AppBadge>
    </div>
  </RouterLink>
</template>
