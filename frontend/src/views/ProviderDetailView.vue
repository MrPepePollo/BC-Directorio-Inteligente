<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  Bot,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Globe,
  Loader2,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Sparkles,
  Trash2,
  Wrench,
} from 'lucide-vue-next'
import { useAuth } from '@/composables/useAuth'
import { useProvider, useProviders } from '@/composables/useProviders'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCard from '@/components/ui/AppCard.vue'
import type { AgentResult } from '@/types/provider'

const route = useRoute()
const router = useRouter()
const id = ref(route.params.id as string)

const { user, loading: authLoading } = useAuth()
const { data: provider, isLoading, refetch } = useProvider(id)
const { enrichMutation, deleteMutation, agentEnrichMutation } = useProviders()

const isAuthenticated = computed(() => !!user.value && !authLoading.value)
const isEnriching = computed(() => !!enrichMutation.isPending?.value)
const isAgentRunning = computed(() => !!agentEnrichMutation.isPending?.value)
const agentResult = ref<AgentResult | null>(null)
const showAgentPanel = ref(false)
const agentStepsExpanded = ref(true)
const providerLocation = computed(() =>
  [provider.value?.city, provider.value?.country].filter(Boolean).join(', '),
)
const categoryCount = computed(() => provider.value?.categories.length ?? 0)
const tagCount = computed(() => provider.value?.tags.length ?? 0)
const aiCategoryCount = computed(
  () => provider.value?.categories.filter((category) => category.source === 'ai').length ?? 0,
)
const aiTagCount = computed(
  () => provider.value?.tags.filter((tag) => tag.source === 'ai').length ?? 0,
)
const hasAiMetadata = computed(() => aiCategoryCount.value > 0 || aiTagCount.value > 0)
const contactCount = computed(() =>
  [provider.value?.contact_email, provider.value?.contact_phone, provider.value?.website].filter(Boolean)
    .length,
)
const createdAtLabel = computed(() =>
  provider.value
    ? new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium' }).format(new Date(provider.value.created_at))
    : '',
)
const updatedAtLabel = computed(() =>
  provider.value
    ? new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium' }).format(new Date(provider.value.updated_at))
    : '',
)

async function enrich() {
  if (!isAuthenticated.value) return
  await enrichMutation.mutateAsync(id.value)
}

async function runAgent() {
  if (!isAuthenticated.value) return
  agentResult.value = null
  showAgentPanel.value = true
  agentStepsExpanded.value = true
  try {
    const result = await agentEnrichMutation.mutateAsync(id.value)
    agentResult.value = result
    refetch()
  } catch (err) {
    agentResult.value = {
      provider_id: id.value,
      status: 'error',
      steps: [{ type: 'error', content: err instanceof Error ? err.message : 'Error desconocido' }],
      changes_applied: {},
      summary: 'El agente no pudo completar el enriquecimiento.',
      total_iterations: 0,
      total_duration_ms: 0,
    }
  }
}

function stepIcon(type: string) {
  switch (type) {
    case 'thought': return Brain
    case 'action': return Wrench
    case 'final': return CheckCircle2
    case 'error': return CircleAlert
    default: return Bot
  }
}

function stepColor(type: string) {
  switch (type) {
    case 'thought': return 'text-blue-500'
    case 'action': return 'text-amber-500'
    case 'final': return 'text-emerald-500'
    case 'error': return 'text-red-500'
    default: return 'text-text-muted'
  }
}

async function remove() {
  if (!confirm('Estas seguro de eliminar este proveedor?')) return
  await deleteMutation.mutateAsync(id.value)
  router.push('/')
}
</script>

<template>
  <div v-if="isLoading" class="mx-auto max-w-6xl space-y-5">
    <div class="skeleton h-10 w-28 rounded-full" />
    <div class="app-panel rounded-[2rem] p-6 sm:p-8">
      <div class="space-y-4">
        <div class="skeleton h-6 w-40 rounded-full" />
        <div class="skeleton h-14 w-2/3 rounded-[1.25rem]" />
        <div class="skeleton h-5 w-56 rounded-full" />
        <div class="grid gap-4 md:grid-cols-3">
          <div class="skeleton h-24 rounded-[1.5rem]" />
          <div class="skeleton h-24 rounded-[1.5rem]" />
          <div class="skeleton h-24 rounded-[1.5rem]" />
        </div>
      </div>
    </div>

    <div class="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)]">
      <div class="space-y-5">
        <div class="skeleton h-48 rounded-[1.6rem]" />
        <div class="skeleton h-40 rounded-[1.6rem]" />
        <div class="skeleton h-44 rounded-[1.6rem]" />
      </div>
      <div class="space-y-5">
        <div class="skeleton h-64 rounded-[1.6rem]" />
        <div class="skeleton h-52 rounded-[1.6rem]" />
      </div>
    </div>
  </div>

  <div v-else-if="provider" class="mx-auto max-w-6xl space-y-8">
    <button
      @click="router.push('/')"
      class="inline-flex items-center gap-2 rounded-full border border-border bg-surface-elevated px-4 py-2 text-sm font-medium text-text-secondary shadow-[0_14px_34px_-24px_rgb(18_45_96_/_0.24)] transition-[transform,border-color,color,background-color] duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-hover hover:text-text-primary cursor-pointer"
    >
      <ArrowLeft class="h-4 w-4" />
      Volver
    </button>

    <section class="app-panel relative overflow-hidden rounded-[2rem] p-6 sm:p-8 lg:p-10">
      <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgb(74_140_255_/_0.16),_transparent_34%),radial-gradient(circle_at_85%_0,_rgb(61_196_226_/_0.12),_transparent_28%)]" />
      <div class="pointer-events-none absolute -right-16 top-8 h-40 w-40 rounded-full bg-primary-300/12 blur-3xl" />
      <div class="pointer-events-none absolute bottom-0 left-10 h-32 w-32 rounded-full bg-ai-300/12 blur-3xl" />

      <div class="relative space-y-8">
        <div class="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div class="max-w-3xl space-y-4">
            <div class="flex flex-wrap gap-2">
              <AppBadge variant="primary">Ficha del proveedor</AppBadge>
              <AppBadge v-if="hasAiMetadata" variant="ai">
                <Sparkles class="h-3 w-3" />
                Perfil enriquecido
              </AppBadge>
              <AppBadge v-if="provider.categories.length" variant="default">
                {{ provider.categories.length }} categorias
              </AppBadge>
              <AppBadge v-if="provider.tags.length" variant="default">
                {{ provider.tags.length }} tags
              </AppBadge>
            </div>

            <div class="space-y-3">
              <h1 class="max-w-3xl text-4xl font-bold tracking-[-0.05em] text-text-primary sm:text-5xl">
                {{ provider.name }}
              </h1>

              <div
                v-if="providerLocation"
                class="inline-flex items-center gap-2 rounded-full border border-border bg-surface-elevated/90 px-3.5 py-2 text-sm text-text-secondary"
              >
                <MapPin class="h-4 w-4 text-primary-500" />
                {{ providerLocation }}
              </div>

              <p class="max-w-3xl text-base leading-7 text-text-secondary sm:text-lg">
                {{ provider.description }}
              </p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2 xl:justify-end">
            <AppButton
              v-if="isAuthenticated"
              variant="secondary"
              size="sm"
              :loading="isAgentRunning"
              :disabled="isAgentRunning || isEnriching"
              @click="runAgent"
            >
              <Bot class="h-4 w-4" />
              Agente IA
            </AppButton>

            <AppButton
              v-if="isAuthenticated"
              variant="secondary"
              size="sm"
              :loading="isEnriching"
              :disabled="isAgentRunning || isEnriching"
              @click="enrich"
            >
              <Sparkles class="h-4 w-4" />
              Enriquecer con IA
            </AppButton>

            <AppButton
              variant="secondary"
              size="sm"
              @click="router.push(`/providers/${id}/edit`)"
            >
              <Pencil class="h-4 w-4" />
              Editar
            </AppButton>

            <AppButton variant="danger" size="sm" @click="remove">
              <Trash2 class="h-4 w-4" />
            </AppButton>
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-3">
          <div class="rounded-[1.5rem] border border-border bg-surface-elevated/85 p-4 shadow-[0_18px_40px_-30px_rgb(18_45_96_/_0.26)]">
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Cobertura
            </p>
            <p class="mt-3 text-2xl font-semibold text-text-primary">
              {{ categoryCount }}
            </p>
            <p class="mt-1 text-sm leading-6 text-text-secondary">
              categorias asociadas para entender mejor el tipo de servicio que ofrece.
            </p>
          </div>

          <div class="rounded-[1.5rem] border border-border bg-surface-elevated/85 p-4 shadow-[0_18px_40px_-30px_rgb(18_45_96_/_0.26)]">
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Senales
            </p>
            <p class="mt-3 text-2xl font-semibold text-text-primary">
              {{ tagCount }}
            </p>
            <p class="mt-1 text-sm leading-6 text-text-secondary">
              tags y temas que ayudan a comparar este proveedor con otras opciones del directorio.
            </p>
          </div>

          <div class="rounded-[1.5rem] border border-border bg-surface-elevated/85 p-4 shadow-[0_18px_40px_-30px_rgb(18_45_96_/_0.26)]">
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Contacto
            </p>
            <p class="mt-3 text-2xl font-semibold text-text-primary">
              {{ contactCount }}
            </p>
            <p class="mt-1 text-sm leading-6 text-text-secondary">
              canales disponibles para iniciar una conversacion comercial o tecnica.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Agent Panel -->
    <section v-if="showAgentPanel" class="app-panel relative overflow-hidden rounded-[2rem] p-6 sm:p-8">
      <div class="space-y-5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="rounded-full bg-ai-50 p-2.5 text-ai-600 dark:bg-ai-900/60 dark:text-ai-300">
              <Bot class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-text-primary">Agente de Enriquecimiento</h2>
              <p class="text-sm text-text-secondary">
                <template v-if="isAgentRunning">
                  <span class="inline-flex items-center gap-1.5">
                    <Loader2 class="h-3.5 w-3.5 animate-spin" />
                    Razonando y ejecutando herramientas...
                  </span>
                </template>
                <template v-else-if="agentResult">
                  {{ agentResult.status === 'completed' ? 'Completado' : agentResult.status === 'partial' ? 'Parcialmente completado' : 'Error' }}
                  en {{ agentResult.total_iterations }} iteraciones
                  ({{ (agentResult.total_duration_ms / 1000).toFixed(1) }}s)
                </template>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              v-if="agentResult"
              @click="agentStepsExpanded = !agentStepsExpanded"
              class="rounded-full p-2 text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary"
            >
              <ChevronUp v-if="agentStepsExpanded" class="h-4 w-4" />
              <ChevronDown v-else class="h-4 w-4" />
            </button>
          </div>
        </div>

        <!-- Agent Status Badge -->
        <div v-if="agentResult" class="flex flex-wrap items-center gap-2">
          <AppBadge :variant="agentResult.status === 'completed' ? 'primary' : agentResult.status === 'partial' ? 'default' : 'danger'">
            {{ agentResult.status === 'completed' ? 'Completado' : agentResult.status === 'partial' ? 'Parcial' : 'Error' }}
          </AppBadge>
          <AppBadge v-if="Object.keys(agentResult.changes_applied).length" variant="ai">
            {{ Object.keys(agentResult.changes_applied).length }} cambios aplicados
          </AppBadge>
        </div>

        <!-- Agent Summary -->
        <p v-if="agentResult?.summary" class="rounded-[1.2rem] border border-border bg-surface-secondary/65 px-4 py-3 text-sm leading-6 text-text-secondary">
          {{ agentResult.summary }}
        </p>

        <!-- Agent Steps Timeline -->
        <div v-if="agentResult && agentStepsExpanded" class="space-y-3">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Traza del agente ({{ agentResult.steps.length }} pasos)
          </p>

          <div class="relative space-y-0">
            <div class="absolute left-[18px] top-3 bottom-3 w-px bg-border" />

            <div
              v-for="(step, index) in agentResult.steps"
              :key="index"
              class="relative flex gap-3 py-2"
            >
              <div class="relative z-10 mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-surface-elevated">
                <component :is="stepIcon(step.type)" class="h-4 w-4" :class="stepColor(step.type)" />
              </div>

              <div class="min-w-0 flex-1 space-y-1">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold uppercase tracking-wider" :class="stepColor(step.type)">
                    {{ step.type === 'thought' ? 'Razonamiento' : step.type === 'action' ? 'Accion' : step.type === 'final' ? 'Conclusion' : 'Error' }}
                  </span>
                  <AppBadge v-if="step.tool" variant="default" class="text-[10px]">
                    {{ step.tool }}
                  </AppBadge>
                  <span v-if="step.duration_ms" class="text-[10px] text-text-muted">
                    {{ step.duration_ms }}ms
                  </span>
                </div>

                <p class="text-sm leading-6 text-text-secondary">
                  {{ step.content }}
                </p>

                <details v-if="step.tool_output" class="group">
                  <summary class="cursor-pointer text-xs text-text-muted transition-colors hover:text-text-secondary">
                    Ver resultado de la herramienta
                  </summary>
                  <pre class="mt-1.5 max-h-40 overflow-auto rounded-xl border border-border bg-surface-secondary/80 p-3 text-xs leading-5 text-text-secondary">{{ JSON.stringify(step.tool_output, null, 2) }}</pre>
                </details>
              </div>
            </div>
          </div>
        </div>

        <!-- Changes Applied -->
        <div v-if="agentResult && Object.keys(agentResult.changes_applied).length" class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Cambios aplicados al proveedor
          </p>
          <div class="grid gap-2 sm:grid-cols-2">
            <div
              v-for="(value, key) in agentResult.changes_applied"
              :key="String(key)"
              class="rounded-[1.1rem] border border-border bg-surface-secondary/65 px-3 py-2"
            >
              <span class="text-xs font-medium text-text-muted">{{ key }}</span>
              <p class="mt-0.5 text-sm text-text-primary truncate">
                {{ Array.isArray(value) ? value.join(', ') : value }}
              </p>
            </div>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="isAgentRunning && !agentResult" class="flex flex-col items-center gap-3 py-8">
          <div class="relative">
            <div class="h-12 w-12 rounded-full border-2 border-ai-200 dark:border-ai-800" />
            <Loader2 class="absolute inset-0 h-12 w-12 animate-spin text-ai-500" />
          </div>
          <p class="text-sm text-text-secondary">
            El agente esta analizando al proveedor y ejecutando herramientas...
          </p>
          <p class="text-xs text-text-muted">Esto puede tomar entre 10 y 30 segundos</p>
        </div>
      </div>
    </section>

    <div class="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)]">
      <div class="space-y-5">
        <AppCard class="rounded-[1.7rem] p-6 sm:p-7">
          <div class="space-y-4">
            <div class="space-y-1">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Descripcion
              </p>
              <h2 class="text-2xl font-semibold text-text-primary">
                Que hace este proveedor
              </h2>
            </div>

            <p class="text-base leading-8 whitespace-pre-line text-text-secondary">
              {{ provider.description }}
            </p>
          </div>
        </AppCard>

        <AppCard v-if="provider.categories.length" class="rounded-[1.7rem] p-6 sm:p-7">
          <div class="space-y-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div class="space-y-1">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Categorias
                </p>
                <h2 class="text-2xl font-semibold text-text-primary">
                  Como se clasifica dentro del directorio
                </h2>
              </div>

              <p class="text-sm text-text-muted">
                {{ aiCategoryCount ? `${aiCategoryCount} sugeridas por IA` : 'Curacion manual' }}
              </p>
            </div>

            <div class="flex flex-wrap gap-2.5">
              <AppBadge
                v-for="pc in provider.categories"
                :key="pc.category.id"
                :variant="pc.source === 'ai' ? 'ai' : 'primary'"
                class="px-3 py-2"
              >
                <Sparkles v-if="pc.source === 'ai'" class="h-3.5 w-3.5" />
                {{ pc.category.name }}
                <span v-if="pc.confidence" class="text-xs opacity-75">
                  {{ Math.round(pc.confidence * 100) }}%
                </span>
              </AppBadge>
            </div>
          </div>
        </AppCard>

        <AppCard v-if="provider.tags.length" class="rounded-[1.7rem] p-6 sm:p-7">
          <div class="space-y-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div class="space-y-1">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Tags
                </p>
                <h2 class="text-2xl font-semibold text-text-primary">
                  Senales utiles para comparar y filtrar
                </h2>
              </div>

              <p class="text-sm text-text-muted">
                {{ aiTagCount ? `${aiTagCount} detectados por IA` : 'Etiquetas del directorio' }}
              </p>
            </div>

            <div class="flex flex-wrap gap-2.5">
              <AppBadge
                v-for="pt in provider.tags"
                :key="pt.tag.id"
                :variant="pt.source === 'ai' ? 'ai' : 'default'"
                class="px-3 py-2"
              >
                <Sparkles v-if="pt.source === 'ai'" class="h-3.5 w-3.5" />
                {{ pt.tag.name }}
              </AppBadge>
            </div>
          </div>
        </AppCard>
      </div>

      <div class="space-y-5">
        <AppCard class="rounded-[1.7rem] p-6 sm:p-7">
          <div class="space-y-5">
            <div class="space-y-1">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Contacto
              </p>
              <h2 class="text-2xl font-semibold text-text-primary">
                Canales disponibles
              </h2>
            </div>

            <div class="space-y-3">
              <a
                v-if="provider.contact_email"
                :href="`mailto:${provider.contact_email}`"
                class="flex items-start gap-3 rounded-[1.15rem] border border-border bg-surface-secondary/70 px-4 py-3 text-sm text-text-primary transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-primary-300 hover:bg-surface-hover hover:text-primary-700"
              >
                <span class="mt-0.5 rounded-full bg-primary-50 p-2 text-primary-600 dark:bg-primary-900/60 dark:text-primary-300">
                  <Mail class="h-4 w-4" />
                </span>
                <span class="min-w-0">
                  <span class="block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                    Email
                  </span>
                  <span class="mt-1 block break-all">{{ provider.contact_email }}</span>
                </span>
              </a>

              <a
                v-if="provider.contact_phone"
                :href="`tel:${provider.contact_phone}`"
                class="flex items-start gap-3 rounded-[1.15rem] border border-border bg-surface-secondary/70 px-4 py-3 text-sm text-text-primary transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-primary-300 hover:bg-surface-hover hover:text-primary-700"
              >
                <span class="mt-0.5 rounded-full bg-primary-50 p-2 text-primary-600 dark:bg-primary-900/60 dark:text-primary-300">
                  <Phone class="h-4 w-4" />
                </span>
                <span>
                  <span class="block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                    Telefono
                  </span>
                  <span class="mt-1 block">{{ provider.contact_phone }}</span>
                </span>
              </a>

              <a
                v-if="provider.website"
                :href="provider.website"
                target="_blank"
                rel="noopener"
                class="flex items-start gap-3 rounded-[1.15rem] border border-border bg-surface-secondary/70 px-4 py-3 text-sm text-text-primary transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-primary-300 hover:bg-surface-hover hover:text-primary-700"
              >
                <span class="mt-0.5 rounded-full bg-primary-50 p-2 text-primary-600 dark:bg-primary-900/60 dark:text-primary-300">
                  <Globe class="h-4 w-4" />
                </span>
                <span class="min-w-0">
                  <span class="block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                    Sitio web
                  </span>
                  <span class="mt-1 block break-all">{{ provider.website }}</span>
                </span>
              </a>

              <div
                v-if="!provider.contact_email && !provider.contact_phone && !provider.website"
                class="rounded-[1.2rem] border border-dashed border-border bg-surface-secondary/60 px-4 py-4 text-sm leading-6 text-text-muted"
              >
                Este proveedor aun no tiene canales de contacto cargados en el directorio.
              </div>
            </div>
          </div>
        </AppCard>

        <AppCard class="rounded-[1.7rem] p-6 sm:p-7">
          <div class="space-y-5">
            <div class="space-y-1">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Informacion
              </p>
              <h2 class="text-2xl font-semibold text-text-primary">
                Trazabilidad del registro
              </h2>
            </div>

            <dl class="space-y-3">
              <div class="flex items-center justify-between rounded-[1.1rem] border border-border bg-surface-secondary/65 px-4 py-3">
                <dt class="text-sm text-text-muted">Creado</dt>
                <dd class="text-sm font-medium text-text-primary">
                  {{ createdAtLabel }}
                </dd>
              </div>

              <div class="flex items-center justify-between rounded-[1.1rem] border border-border bg-surface-secondary/65 px-4 py-3">
                <dt class="text-sm text-text-muted">Actualizado</dt>
                <dd class="text-sm font-medium text-text-primary">
                  {{ updatedAtLabel }}
                </dd>
              </div>

              <div
                v-if="providerLocation"
                class="flex items-center justify-between rounded-[1.1rem] border border-border bg-surface-secondary/65 px-4 py-3"
              >
                <dt class="text-sm text-text-muted">Ubicacion</dt>
                <dd class="text-sm font-medium text-text-primary">
                  {{ providerLocation }}
                </dd>
              </div>
            </dl>
          </div>
        </AppCard>
      </div>
    </div>
  </div>
</template>
