<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  Globe,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Sparkles,
  Trash2,
} from 'lucide-vue-next'
import { useAuth } from '@/composables/useAuth'
import { useProvider, useProviders } from '@/composables/useProviders'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCard from '@/components/ui/AppCard.vue'

const route = useRoute()
const router = useRouter()
const id = ref(route.params.id as string)

const { user, loading: authLoading } = useAuth()
const { data: provider, isLoading } = useProvider(id)
const { enrichMutation, deleteMutation } = useProviders()

const isAuthenticated = computed(() => !!user.value && !authLoading.value)
const isEnriching = computed(() => !!enrichMutation.isPending?.value)
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
              :loading="isEnriching"
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
