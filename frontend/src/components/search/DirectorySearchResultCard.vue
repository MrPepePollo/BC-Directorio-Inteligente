<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight, ChevronDown, MapPin } from 'lucide-vue-next'
import type { DirectorySearchResult } from '@/types/provider'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppCard from '@/components/ui/AppCard.vue'
import SearchScoreMetricCard from '@/components/search/SearchScoreMetricCard.vue'

interface ScoreMetric {
  key: string
  label: string
  value: number
  description: string
}

const props = defineProps<{
  result: DirectorySearchResult
}>()

const isExpanded = ref(false)

const matchTier = computed(() => {
  if (props.result.score >= 0.55) {
    return {
      label: 'Muy alineado',
      variant: 'success' as const,
      description: 'Tiene varias senales claras de coincidencia con esta necesidad.',
    }
  }

  if (props.result.score >= 0.35) {
    return {
      label: 'Buena opcion',
      variant: 'primary' as const,
      description: 'Muestra una relacion clara con lo que estas buscando.',
    }
  }

  return {
    label: 'Posible alternativa',
    variant: 'info' as const,
    description: 'Puede servir para abrir opciones, aunque la coincidencia es menor.',
  }
})

const locationLabel = computed(() =>
  [props.result.city, props.result.country].filter(Boolean).join(', '),
)

const primaryReason = computed(() =>
  props.result.match_reasons[0] ?? matchTier.value.description,
)

const reasonChips = computed(() =>
  props.result.match_reasons.length
    ? props.result.match_reasons
    : ['Puede servir como una alternativa para ampliar la evaluacion.'],
)

const scoreDetails = computed<ScoreMetric[]>(() => [
  {
    key: 'overall',
    label: 'Coincidencia general',
    value: props.result.score,
    description: 'Balance final entre semantica, terminos y contexto.',
  },
  {
    key: 'semantic',
    label: 'Alineacion del significado',
    value: props.result.semantic_score,
    description: 'Que tan cerca esta la intencion del servicio que describiste.',
  },
  {
    key: 'lexical',
    label: 'Coincidencia de terminos',
    value: props.result.lexical_score,
    description: 'Palabras y expresiones que aparecen muy cerca de tu necesidad.',
  },
  {
    key: 'metadata',
    label: 'Contexto y filtros',
    value: props.result.metadata_score,
    description: 'Senales de categoria, ubicacion y estructura del directorio.',
  },
])

const strongestDetail = computed<ScoreMetric>(() =>
  scoreDetails.value
    .filter((metric) => metric.key !== 'overall')
    .sort((left, right) => right.value - left.value)[0] ?? {
    key: 'semantic',
    label: 'Alineacion del significado',
    value: props.result.semantic_score,
    description: 'Que tan cerca esta la intencion del servicio que describiste.',
  },
)

function formatScorePercentage(score: number) {
  return `${Math.round(score * 100)}%`
}
</script>

<template>
  <RouterLink
    :to="`/providers/${result.id}`"
    class="block"
  >
    <AppCard hoverable class="rounded-[1.55rem]">
      <div class="space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1 space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <h4 class="text-xl font-semibold text-text-primary">{{ result.name }}</h4>
              <AppBadge :variant="matchTier.variant">
                {{ matchTier.label }}
              </AppBadge>
            </div>

            <p class="text-sm font-medium text-text-primary">
              {{ primaryReason }}
            </p>

            <p class="line-clamp-3 text-sm leading-7 text-text-secondary">
              {{ result.description }}
            </p>
          </div>

          <ArrowRight class="mt-1 h-4 w-4 shrink-0 text-text-muted" />
        </div>

        <p
          v-if="locationLabel"
          class="flex items-center gap-1.5 text-xs font-medium text-text-muted"
        >
          <MapPin class="h-3 w-3" />
          {{ locationLabel }}
        </p>

        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Por que aparece
          </p>
          <div class="flex flex-wrap gap-2">
            <AppBadge
              v-for="reason in reasonChips"
              :key="reason"
              variant="default"
            >
              {{ reason }}
            </AppBadge>
          </div>
        </div>

        <div
          class="overflow-hidden rounded-[1.35rem] border border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(246,249,253,0.92))] shadow-[inset_0_1px_0_rgba(255,255,255,0.65)] dark:border-border dark:bg-[linear-gradient(180deg,rgba(17,24,37,0.98),rgba(12,18,29,0.96))] dark:shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
          @click.stop.prevent
        >
          <button
            type="button"
            class="flex w-full cursor-pointer items-start justify-between gap-4 px-4 py-4 text-left select-none sm:px-5"
            @click.stop.prevent="isExpanded = !isExpanded"
          >
            <div class="min-w-0 space-y-3">
              <div class="space-y-1">
                <p class="text-sm font-semibold text-text-primary">
                  Ver detalle de la coincidencia
                </p>
                <p class="text-xs leading-5 text-text-muted">
                  Un vistazo rapido para entender donde este proveedor se alinea mejor con tu necesidad.
                </p>
              </div>

              <div class="flex flex-wrap gap-2">
                <AppBadge :variant="matchTier.variant">
                  Score general {{ formatScorePercentage(result.score) }}
                </AppBadge>
                <AppBadge variant="default">
                  Fortaleza: {{ strongestDetail.label }}
                </AppBadge>
              </div>
            </div>

            <ChevronDown
              :class="[
                'mt-1 h-4 w-4 shrink-0 text-text-muted transition-transform duration-200',
                isExpanded ? 'rotate-180' : '',
              ]"
            />
          </button>

          <div
            v-if="isExpanded"
            class="space-y-4 border-t border-border/80 bg-white/45 px-4 py-4 sm:px-5 sm:py-5 dark:bg-black/10"
          >
            <div class="rounded-[1.2rem] border border-border bg-white/65 px-4 py-4 shadow-[0_12px_26px_-24px_rgb(18_45_96_/_0.24)] dark:border-border dark:bg-[linear-gradient(180deg,rgba(21,29,42,0.95),rgba(17,24,37,0.92))] dark:shadow-[0_18px_42px_-28px_rgb(0_0_0_/_0.45)]">
              <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm font-semibold text-text-primary">
                    Lectura general
                  </p>
                  <p class="text-sm leading-6 text-text-secondary">
                    La senal mas fuerte esta en <span class="font-medium text-text-primary">{{ strongestDetail.label.toLowerCase() }}</span>.
                  </p>
                </div>

                <AppBadge :variant="matchTier.variant">
                  {{ matchTier.label }}
                </AppBadge>
              </div>
            </div>

            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <SearchScoreMetricCard
                v-for="metric in scoreDetails"
                :key="metric.key"
                :label="metric.label"
                :score="metric.value"
                :description="metric.description"
              />
            </div>
          </div>
        </div>
      </div>
    </AppCard>
  </RouterLink>
</template>
