<script lang="ts">
export default { name: 'SearchView' }
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Filter,
  Globe,
  Lightbulb,
  MapPin,
  MessageSquare,
  Search,
  Sparkles,
  X,
} from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useSemanticSearch } from '@/composables/useSearch'
import { useCategories } from '@/composables/useProviders'
import type { SearchRecommendation, WebSearchResult } from '@/types/provider'
import AppCard from '@/components/ui/AppCard.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import DirectorySearchResultCard from '@/components/search/DirectorySearchResultCard.vue'
import WebProviderImportModal from '@/components/search/WebProviderImportModal.vue'

const EXAMPLE_QUERIES = [
  'empresa de desarrollo de apps moviles',
  'consultoria en transformacion digital',
  'servicios de ciberseguridad',
  'analisis de datos con machine learning',
  'desarrollo web con React o Vue en Peru',
  'imagenes satelitales para agricultura',
]

const {
  query,
  response,
  directoryResults,
  webResults,
  analysis,
  resultCount,
  sessionId,
  meta,
  isLoading,
  isSearchingWeb,
  isAsking,
  followupAnswer,
  search,
  setFilters,
  expandWeb,
  askFollowup,
  reset,
} = useSemanticSearch()

const { data: categories } = useCategories()
const { user, loading: authLoading } = useAuth()

const inputValue = ref('')
const selectedCategory = ref('')
const selectedCountry = ref('')
const includeAnalysis = ref(false)
const showFilters = ref(false)
const showAssistantPanel = ref(false)
const followupInput = ref('')
const isImportModalOpen = ref(false)
const selectedWebResult = ref<WebSearchResult | null>(null)

const isWebExpanded = computed(() => meta.value?.used_web_search ?? false)
const canImportFromWeb = computed(() => !!user.value && !authLoading.value)
const hasSearched = computed(() => query.value.trim().length >= 2)
const hasDirectoryResults = computed(() => directoryResults.value.length > 0)
const hasWebResults = computed(() => webResults.value.length > 0)
const hasActiveFilters = computed(() => !!(selectedCategory.value || selectedCountry.value))
const primarySearchLabel = computed(() =>
  hasSearched.value ? 'Actualizar resultados' : 'Buscar en el directorio',
)
const interpretationModeLabel = computed(() =>
  meta.value?.used_llm_parser ? 'Interpretacion automatica' : 'Interpretacion basica',
)
const interpretationModeCopy = computed(() =>
  meta.value?.used_llm_parser
    ? 'Refinamos la necesidad a partir de lo que escribiste para priorizar proveedores mas cercanos.'
    : 'Usamos tu texto tal como fue escrito para encontrar coincidencias en el directorio.',
)
const assistantPreview = computed(() => analysis.value?.summary ?? '')
const canSubmitFollowup = computed(() => !!sessionId.value && followupInput.value.trim().length >= 2)
const followupPlaceholder = computed(() =>
  hasDirectoryResults.value
    ? 'Ej: cual parece mas fuerte para un proyecto regional?'
    : 'Ej: hay alguna alternativa cercana aunque no sea exacta?',
)

const categoryOptions = computed(() => [
  { label: 'Todas las categorias', value: '', description: 'Sin filtro aplicado' },
  ...(
    categories.value?.map((category) => ({
      label: category.name,
      value: category.id,
    })) ?? []
  ),
])

const countryOptions = [
  { label: 'Todos los paises', value: '', description: 'Sin restriccion geografica' },
  { label: 'Argentina', value: 'Argentina' },
  { label: 'Colombia', value: 'Colombia' },
  { label: 'Mexico', value: 'Mexico' },
  { label: 'Chile', value: 'Chile' },
  { label: 'Peru', value: 'Peru' },
  { label: 'Uruguay', value: 'Uruguay' },
  { label: 'Brasil', value: 'Brasil' },
  { label: 'Ecuador', value: 'Ecuador' },
]

watch(inputValue, (value) => {
  if (value.trim().length === 0 && response.value) {
    reset()
    includeAnalysis.value = false
    selectedCategory.value = ''
    selectedCountry.value = ''
    showFilters.value = false
    showAssistantPanel.value = false
  }
})

watch([selectedCategory, selectedCountry], () => {
  setFilters({
    categoryId: selectedCategory.value || undefined,
    country: selectedCountry.value || undefined,
    analyze: includeAnalysis.value,
  })
})

watch(includeAnalysis, () => {
  setFilters({
    categoryId: selectedCategory.value || undefined,
    country: selectedCountry.value || undefined,
    analyze: includeAnalysis.value,
  })
})

watch(
  () => response.value?.session_id,
  () => {
    showAssistantPanel.value = false
    followupInput.value = ''
  },
)

function searchNow(value = inputValue.value) {
  const normalized = value.trim()
  if (normalized.length < 2) return
  inputValue.value = normalized
  search(normalized)
}

function onSubmit() {
  searchNow()
}

function applyExample(example: string) {
  inputValue.value = example
  searchNow(example)
}

function applyCategory(categoryId: string, categoryName: string) {
  selectedCategory.value = categoryId
  showFilters.value = true
  inputValue.value = categoryName
  searchNow(categoryName)
}

function clearAllFilters() {
  selectedCategory.value = ''
  selectedCountry.value = ''
  setFilters({
    analyze: includeAnalysis.value,
  })
}

function getDomain(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function getSourceLabel(source: string) {
  if (source === 'openai-web-search') return 'Referencia encontrada en web'
  if (source === 'mock-web') return 'Referencia externa'
  return source
}

function getFriendlyRecommendationLabel(recommendation: SearchRecommendation, index: number) {
  const normalized = recommendation.label.trim().toLowerCase()
  if (normalized === 'mejor alineado') return 'Mejor alineado'
  if (normalized === 'alternativa cercana') return 'Alternativa cercana'
  if (normalized === 'vale revisar') return 'Vale revisar'
  if (normalized.startsWith('top 1')) return 'Mejor alineado'
  if (normalized.startsWith('top 2')) return 'Alternativa cercana'
  if (index === 0) return 'Mejor alineado'
  if (index === 1) return 'Alternativa cercana'
  return 'Vale revisar'
}

function getRecommendationName(recommendation: SearchRecommendation) {
  if (recommendation.target_type === 'directory') {
    const match = directoryResults.value.find((r) => r.id === recommendation.target_id)
    return match?.name ?? recommendation.target_id
  }
  return recommendation.target_id
}

function getRecommendationVariant(label: string) {
  if (label === 'Mejor alineado') return 'success' as const
  if (label === 'Alternativa cercana') return 'primary' as const
  return 'default' as const
}

function getAppliedFilterSummary() {
  const parts: string[] = []
  if (selectedCategory.value) {
    const category = categories.value?.find((item) => item.id === selectedCategory.value)
    if (category) parts.push(category.name)
  }
  if (selectedCountry.value) parts.push(selectedCountry.value)
  return parts.join(' · ')
}

function isExampleActive(example: string) {
  return inputValue.value.trim().toLowerCase() === example.toLowerCase()
}

function isCategoryActive(categoryId: string) {
  return selectedCategory.value === categoryId
}

async function submitFollowup() {
  const message = followupInput.value.trim()
  if (!sessionId.value || !message) return
  await askFollowup(sessionId.value, message)
  followupInput.value = ''
}

async function submitWebSearch() {
  const text = inputValue.value.trim()
  if (text.length < 2) return
  await expandWeb(text)
}

function openImportModal(result: WebSearchResult) {
  if (!canImportFromWeb.value || !sessionId.value) return
  selectedWebResult.value = result
  isImportModalOpen.value = true
}

function closeImportModal() {
  isImportModalOpen.value = false
  selectedWebResult.value = null
}
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-8">
    <section class="space-y-3 text-center">
      <div class="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300">
        <Sparkles class="h-3.5 w-3.5" />
        Busqueda inteligente
      </div>
      <h1 class="text-4xl font-bold text-text-primary sm:text-5xl">
        Encuentra proveedores con mas claridad
      </h1>
      <p class="mx-auto max-w-3xl text-base leading-7 text-text-secondary">
        Describe lo que necesitas y te mostraremos primero las opciones del directorio mejor alineadas. Despues, si hace falta, podras ampliar la busqueda con referencias externas y un resumen del asistente.
      </p>
    </section>

    <section class="app-panel rounded-[1.8rem] p-4 sm:p-5">
      <div class="space-y-5">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Describe la necesidad
          </p>
          <h2 class="text-2xl font-semibold text-text-primary">
            Busca primero dentro de tu directorio
          </h2>
          <p class="max-w-3xl text-sm leading-6 text-text-secondary">
            Usa una frase simple, como el tipo de servicio, tecnologia o pais que te interesa. La ampliacion con web aparece despues como apoyo opcional.
          </p>
        </div>

        <form class="space-y-4" @submit.prevent="onSubmit">
          <div class="field-shell rounded-[1.35rem] px-4">
            <Search class="h-5 w-5 shrink-0 text-text-muted" />
            <input
              v-model="inputValue"
              placeholder="Ej: empresa que haga aplicaciones moviles con inteligencia artificial"
              class="w-full bg-transparent py-3.5 text-base text-text-primary placeholder:text-text-muted focus:outline-none"
            />
          </div>

          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                @click="includeAnalysis = !includeAnalysis"
                :class="[
                  'rounded-full border px-3.5 py-2 text-sm font-medium transition-colors cursor-pointer',
                  includeAnalysis
                    ? 'border-primary-300 bg-primary-50 text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300'
                    : 'border-border bg-surface-secondary text-text-secondary hover:border-border-strong hover:text-text-primary',
                ]"
              >
                Resumen del asistente
              </button>

              <button
                type="button"
                @click="showFilters = !showFilters"
                :class="[
                  'inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-medium transition-colors cursor-pointer',
                  showFilters || hasActiveFilters
                    ? 'border-primary-300 bg-primary-50 text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300'
                    : 'border-border bg-surface-secondary text-text-secondary hover:border-border-strong hover:text-text-primary',
                ]"
              >
                <Filter class="h-4 w-4" />
                Refinar busqueda
              </button>
            </div>

            <AppButton
              type="submit"
              size="lg"
              :disabled="inputValue.trim().length < 2"
            >
              {{ primarySearchLabel }}
            </AppButton>
          </div>
        </form>

        <div v-if="showFilters" class="rounded-[1.45rem] border border-border bg-surface-secondary/70 p-4">
          <div class="mb-4 space-y-1">
            <p class="text-sm font-semibold text-text-primary">Refinar busqueda</p>
            <p class="text-sm text-text-muted">
              Ajusta categoria o pais si ya tienes una idea mas concreta del proveedor que buscas.
            </p>
          </div>

          <div class="flex flex-wrap gap-3">
            <div class="min-w-[220px] flex-1">
              <AppSelect
                v-model="selectedCategory"
                label="Categoria"
                :options="categoryOptions"
                placeholder="Todas las categorias"
              />
            </div>

            <div class="min-w-[220px] flex-1">
              <AppSelect
                v-model="selectedCountry"
                label="Pais"
                :options="countryOptions"
                placeholder="Todos los paises"
              />
            </div>

            <div class="flex items-end">
              <AppButton
                v-if="hasActiveFilters"
                variant="ghost"
                size="sm"
                @click="clearAllFilters"
              >
                <X class="h-4 w-4" />
                Limpiar
              </AppButton>
            </div>
          </div>
        </div>

        <div v-if="hasActiveFilters" class="flex flex-wrap gap-2">
          <AppBadge v-if="selectedCategory" variant="primary">
            {{ categories?.find((item) => item.id === selectedCategory)?.name }}
            <button class="ml-1 cursor-pointer" @click="selectedCategory = ''">
              <X class="h-3 w-3" />
            </button>
          </AppBadge>
          <AppBadge v-if="selectedCountry" variant="primary">
            {{ selectedCountry }}
            <button class="ml-1 cursor-pointer" @click="selectedCountry = ''">
              <X class="h-3 w-3" />
            </button>
          </AppBadge>
        </div>
      </div>
    </section>

    <div v-if="isLoading" class="space-y-4">
      <div class="flex flex-col items-center gap-3 py-6">
        <svg class="h-8 w-8 animate-spin text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p class="text-sm font-medium text-text-secondary">Buscando proveedores en el directorio...</p>
      </div>
      <div v-for="item in 3" :key="item" class="skeleton h-32 w-full rounded-[1.45rem]" />
    </div>

    <section v-else-if="response" class="space-y-6">
      <AppCard class="rounded-[1.65rem]">
        <div class="space-y-5">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div class="space-y-2">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Lo que entendimos
              </p>
              <h2 class="text-2xl font-semibold text-text-primary">
                Buscas {{ response.interpreted_query }}
              </h2>
              <p class="max-w-3xl text-sm leading-6 text-text-secondary">
                {{ interpretationModeCopy }}
              </p>
            </div>

            <div class="flex flex-wrap gap-2">
              <AppBadge :variant="meta?.used_llm_parser ? 'ai' : 'default'">
                {{ interpretationModeLabel }}
              </AppBadge>
              <AppBadge v-if="hasActiveFilters" variant="default">
                {{ getAppliedFilterSummary() }}
              </AppBadge>
              <AppBadge v-if="isWebExpanded" variant="ai">
                Incluye referencias externas
              </AppBadge>
            </div>
          </div>

          <p
            v-if="meta?.warning"
            class="rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-700 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300"
          >
            {{ meta.warning }}
          </p>

          <div
            v-if="!isWebExpanded"
            class="rounded-[1.3rem] border border-border bg-surface-secondary/70 px-4 py-4"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div class="space-y-1">
                <p class="text-sm font-semibold text-text-primary">Quieres abrir mas opciones?</p>
                <p class="text-sm text-text-muted">
                  Amplia la busqueda con referencias externas si quieres comparar el directorio con proveedores encontrados en web.
                </p>
              </div>

              <div class="flex flex-col items-end gap-2">
                <AppButton
                  variant="secondary"
                  :loading="isSearchingWeb"
                  @click="submitWebSearch"
                >
                  <Globe class="h-4 w-4" />
                  Ampliar con web
                </AppButton>
                <p v-if="isSearchingWeb" class="text-xs text-text-muted">
                  La busqueda web puede tomar uno o dos minutos.
                </p>
              </div>
            </div>
          </div>
        </div>
      </AppCard>

      <section class="space-y-4">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Resultados del directorio
            </p>
            <h3 class="text-2xl font-semibold text-text-primary">
              {{ resultCount }} opcion{{ resultCount !== 1 ? 'es' : '' }} para revisar
            </h3>
          </div>
          <p class="text-sm text-text-muted">
            Empezamos por las coincidencias mas fuertes para que puedas decidir mas rapido.
          </p>
        </div>

        <div v-if="hasDirectoryResults" class="space-y-4">
          <DirectorySearchResultCard
            v-for="result in directoryResults"
            :key="result.id"
            :result="result"
          />
        </div>

        <EmptyState
          v-else
          title="No encontramos coincidencias claras en tu directorio"
          description="Prueba otra formulacion, ajusta filtros o amplia con referencias externas para abrir opciones."
        >
          <div v-if="!isWebExpanded" class="flex flex-col items-center gap-2">
            <AppButton
              variant="secondary"
              :loading="isSearchingWeb"
              @click="submitWebSearch"
            >
              <Globe class="h-4 w-4" />
              Ampliar con web
            </AppButton>
            <p v-if="isSearchingWeb" class="text-xs text-text-muted">
              La busqueda web puede tomar uno o dos minutos.
            </p>
          </div>
        </EmptyState>
      </section>

      <section v-if="isWebExpanded" class="space-y-4">
        <div class="flex items-center gap-2">
          <Globe class="h-4 w-4 text-text-muted" />
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Referencias externas
            </p>
            <h3 class="text-xl font-semibold text-text-primary">
              Opciones para ampliar la comparacion
            </h3>
          </div>
        </div>

        <AppCard v-if="!hasWebResults" class="rounded-[1.55rem]">
          <p class="text-sm leading-6 text-text-muted">
            No encontramos referencias externas confiables para esta busqueda. Puedes ajustar la necesidad o seguir con los resultados del directorio.
          </p>
        </AppCard>

        <div
          v-for="result in webResults"
          v-else
          :key="result.url"
          class="block"
        >
          <AppCard hoverable class="rounded-[1.55rem]">
            <div class="space-y-4">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0 flex-1 space-y-3">
                  <div class="flex flex-wrap items-center gap-2">
                    <h4 class="text-lg font-semibold text-text-primary">{{ result.title }}</h4>
                    <AppBadge variant="warning">Referencia externa</AppBadge>
                  </div>

                  <p class="text-sm font-medium text-text-primary">
                    {{ result.match_reasons[0] || 'Puede servir para comparar opciones fuera del directorio.' }}
                  </p>

                  <p class="text-sm leading-7 text-text-secondary">
                    {{ result.snippet }}
                  </p>

                  <div class="flex flex-wrap items-center gap-3">
                    <span class="truncate text-xs font-medium text-primary-600 dark:text-primary-400">
                      {{ getDomain(result.url) }}
                    </span>
                    <AppBadge variant="default">{{ getSourceLabel(result.source) }}</AppBadge>
                    <p
                      v-if="result.city || result.country"
                      class="flex items-center gap-1 text-xs text-text-muted"
                    >
                      <MapPin class="h-3 w-3" />
                      {{ [result.city, result.country].filter(Boolean).join(', ') }}
                    </p>
                  </div>

                  <div v-if="result.detected_tags?.length" class="flex flex-wrap gap-2">
                    <AppBadge
                      v-for="tag in result.detected_tags.slice(0, 4)"
                      :key="tag"
                      variant="default"
                    >
                      {{ tag }}
                    </AppBadge>
                  </div>
                </div>

                <ExternalLink class="mt-1 h-4 w-4 shrink-0 text-text-muted" />
              </div>

              <div class="flex flex-wrap justify-end gap-3 border-t border-border pt-4">
                <AppButton
                  variant="secondary"
                  size="sm"
                  :disabled="!canImportFromWeb || !sessionId"
                  :title="!canImportFromWeb ? 'Inicia sesion para añadir proveedores' : undefined"
                  @click="openImportModal(result)"
                >
                  Añadir al directorio
                </AppButton>
                <a
                  :href="result.url"
                  target="_blank"
                  rel="noopener"
                  class="inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-surface-elevated px-3.5 py-2 text-sm font-semibold text-text-primary transition-colors hover:bg-surface-hover"
                >
                  <ExternalLink class="h-4 w-4" />
                  Abrir sitio
                </a>
              </div>
            </div>
          </AppCard>
        </div>
      </section>

      <section v-if="analysis" class="space-y-4">
        <AppCard class="rounded-[1.6rem]">
          <div class="space-y-4">
            <button
              class="flex w-full items-start justify-between gap-4 text-left"
              @click="showAssistantPanel = !showAssistantPanel"
            >
              <div class="flex min-w-0 items-start gap-3">
                <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300">
                  <Lightbulb class="h-5 w-5" />
                </div>
                <div class="min-w-0 space-y-2">
                  <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                    Resumen del asistente
                  </p>
                  <p
                    v-if="!showAssistantPanel"
                    class="line-clamp-2 text-sm leading-6 text-text-secondary"
                  >
                    {{ assistantPreview }}
                  </p>
                  <p v-else class="text-sm font-medium text-text-primary">
                    Te ayudamos a comparar los resultados y decidir por donde seguir.
                  </p>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <AppBadge variant="default">Opcional</AppBadge>
                <ChevronUp v-if="showAssistantPanel" class="h-4 w-4 text-text-muted" />
                <ChevronDown v-else class="h-4 w-4 text-text-muted" />
              </div>
            </button>

            <div v-if="showAssistantPanel" class="space-y-5 border-t border-border pt-5">
              <p class="text-sm leading-7 text-text-primary whitespace-pre-line break-words [overflow-wrap:anywhere]">
                {{ analysis.summary }}
              </p>

              <div v-if="analysis.recommendations.length" class="space-y-3">
                <p class="text-sm font-semibold text-text-primary">
                  Recomendaciones para continuar
                </p>

                <div class="space-y-3">
                  <div
                    v-for="(recommendation, index) in analysis.recommendations"
                    :key="`${recommendation.target_type}-${recommendation.target_id}-${recommendation.label}`"
                    class="rounded-[1.3rem] border border-border bg-surface-secondary/70 p-4"
                  >
                    <div class="flex flex-wrap items-center gap-2">
                      <AppBadge
                        :variant="getRecommendationVariant(getFriendlyRecommendationLabel(recommendation, index))"
                      >
                        {{ getFriendlyRecommendationLabel(recommendation, index) }}
                      </AppBadge>

                      <span class="text-sm font-semibold text-text-primary">
                        {{ getRecommendationName(recommendation) }}
                      </span>

                      <RouterLink
                        v-if="recommendation.target_type === 'directory'"
                        :to="`/providers/${recommendation.target_id}`"
                        class="text-xs font-medium text-primary-600 transition-colors hover:text-primary-500"
                      >
                        Ver proveedor
                      </RouterLink>
                    </div>

                    <p class="mt-3 text-sm leading-6 text-text-secondary break-words [overflow-wrap:anywhere]">
                      {{ recommendation.reason }}
                    </p>
                  </div>
                </div>
              </div>

              <div class="space-y-3">
                <p class="text-sm font-semibold text-text-primary">
                  Haz una pregunta sobre estos resultados
                </p>

                <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="submitFollowup">
                  <div class="field-shell field-shell--compact flex-1 px-4">
                    <MessageSquare class="h-4 w-4 shrink-0 text-text-muted" />
                    <input
                      v-model="followupInput"
                      :placeholder="followupPlaceholder"
                      class="w-full bg-transparent py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
                    />
                  </div>

                  <AppButton
                    type="submit"
                    :loading="isAsking"
                    :disabled="!canSubmitFollowup"
                  >
                    Preguntar
                  </AppButton>
                </form>

                <div
                  v-if="followupAnswer"
                  class="rounded-[1.3rem] border border-border bg-surface-secondary/70 p-4"
                >
                  <div class="space-y-3">
                    <p class="text-sm leading-7 text-text-primary whitespace-pre-line break-words [overflow-wrap:anywhere]">
                      {{ followupAnswer.answer }}
                    </p>

                    <p
                      v-if="followupAnswer.warning"
                      class="text-xs text-amber-700 dark:text-amber-300"
                    >
                      {{ followupAnswer.warning }}
                    </p>

                    <div v-if="followupAnswer.referenced_results.length" class="flex flex-wrap gap-2">
                      <span
                        v-for="reference in followupAnswer.referenced_results"
                        :key="reference"
                        class="max-w-full rounded-full border border-border bg-surface-elevated px-3 py-1.5 text-xs font-medium text-text-secondary break-words [overflow-wrap:anywhere]"
                      >
                        {{ reference }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </AppCard>
      </section>
    </section>

    <section v-else class="space-y-6">
      <div class="space-y-3">
        <p class="text-sm font-semibold text-text-primary">Prueba con estas ideas</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="example in EXAMPLE_QUERIES"
            :key="example"
            :class="[
              'cursor-pointer rounded-full border px-4 py-2 text-sm transition-all',
              isExampleActive(example)
                ? 'border-primary-300 bg-primary-100 text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300'
                : 'border-border bg-surface-secondary text-text-secondary hover:border-border-strong hover:bg-surface-hover hover:text-text-primary',
            ]"
            @click="applyExample(example)"
          >
            {{ example }}
          </button>
        </div>
      </div>

      <div v-if="categories?.length" class="app-panel rounded-[1.65rem] p-4 sm:p-5">
        <div class="space-y-4">
          <div class="space-y-1">
            <p class="text-sm font-semibold text-text-primary">Explora por categoria</p>
            <p class="text-sm text-text-muted">
              Si ya sabes el tipo de proveedor que necesitas, empieza por aqui.
            </p>
          </div>

          <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            <button
              v-for="category in categories"
              :key="category.id"
              :class="[
                'cursor-pointer rounded-[1rem] border px-3 py-3 text-sm font-medium transition-all',
                isCategoryActive(category.id)
                  ? 'border-primary-300 bg-primary-100 text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300'
                  : 'border-border bg-surface text-text-secondary hover:border-border-strong hover:bg-surface-hover hover:text-text-primary',
              ]"
              @click="applyCategory(category.id, category.name)"
            >
              {{ category.name }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <WebProviderImportModal
      :open="isImportModalOpen"
      :session-id="sessionId"
      :result="selectedWebResult"
      :categories="categories"
      @close="closeImportModal"
      @created="search(inputValue)"
    />
  </div>
</template>
