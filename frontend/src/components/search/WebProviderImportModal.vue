<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { AlertCircle, LoaderCircle, RefreshCcw, Sparkles, X } from 'lucide-vue-next'
import { useMutation } from '@tanstack/vue-query'
import { api } from '@/lib/api'
import { useProviders } from '@/composables/useProviders'
import type {
  Category,
  ProviderCreate,
  ProviderDraftForm,
  WebProviderImportPreviewResponse,
  WebSearchResult,
} from '@/types/provider'
import AppButton from '@/components/ui/AppButton.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import ProviderFormFields from '@/components/providers/ProviderFormFields.vue'

const props = defineProps<{
  open: boolean
  sessionId: string
  result: WebSearchResult | null
  categories?: Category[]
}>()

const emit = defineEmits<{
  close: []
  created: [providerId: string]
}>()

const router = useRouter()
const { createMutation, enrichMutation } = useProviders()

const form = ref<ProviderDraftForm>(createEmptyForm())
const previewState = ref<'loading' | 'ready' | 'duplicate' | 'error'>('loading')
const warnings = ref<string[]>([])
const provenance = ref('')
const sourceUrl = ref('')
const duplicateProvider = ref<WebProviderImportPreviewResponse['duplicate_provider']>(null)
const lastPreviewKey = ref('')

function createEmptyForm(): ProviderDraftForm {
  return {
    name: '',
    description: '',
    contact_email: '',
    contact_phone: '',
    website: '',
    city: '',
    country: '',
    category_ids: [],
    tag_names: [],
  }
}

function applyPreviewResponse(response: WebProviderImportPreviewResponse) {
  previewState.value = response.status
  warnings.value = response.warnings ?? []
  provenance.value = response.provenance
  sourceUrl.value = response.source_url
  duplicateProvider.value = response.duplicate_provider ?? null

  if (response.draft) {
    const defaults = createEmptyForm()
    form.value = {
      name: response.draft.name ?? defaults.name,
      description: response.draft.description ?? defaults.description,
      contact_email: response.draft.contact_email ?? defaults.contact_email,
      contact_phone: response.draft.contact_phone ?? defaults.contact_phone,
      website: response.draft.website ?? defaults.website,
      city: response.draft.city ?? defaults.city,
      country: response.draft.country ?? defaults.country,
      category_ids: response.draft.category_ids ?? defaults.category_ids,
      tag_names: response.draft.tag_names ?? defaults.tag_names,
    }
  } else {
    form.value = createEmptyForm()
  }
}

const previewMutation = useMutation({
  mutationFn: ({ regenerate }: { regenerate: boolean }) =>
    api.post<WebProviderImportPreviewResponse>(
      `/search/sessions/${props.sessionId}/web-results/import-preview`,
      {
        url: props.result?.url ?? '',
        regenerate,
      },
    ),
  onSuccess: applyPreviewResponse,
  onError: (error: Error) => {
    previewState.value = 'error'
    warnings.value = [error.message || 'No se pudo completar el borrador desde la web.']
    provenance.value = 'No se pudo construir el borrador desde la fuente seleccionada.'
    duplicateProvider.value = null
  },
})

async function loadPreview(regenerate = false) {
  if (!props.open || !props.result || !props.sessionId) return
  previewState.value = 'loading'
  warnings.value = []
  provenance.value = ''
  duplicateProvider.value = null
  if (!regenerate) {
    form.value = createEmptyForm()
  }
  await previewMutation.mutateAsync({ regenerate })
}

watch(
  () => [props.open, props.sessionId, props.result?.url] as const,
  async ([open, sessionId, resultUrl]) => {
    if (!open || !sessionId || !resultUrl) return
    const previewKey = `${sessionId}:${resultUrl}`
    if (lastPreviewKey.value === previewKey) return
    lastPreviewKey.value = previewKey
    await loadPreview(false)
  },
  { immediate: false },
)

const isSaving = computed(
  () => createMutation.isPending.value || enrichMutation.isPending.value,
)
const canSave = computed(
  () => previewState.value === 'ready' && form.value.name.trim().length > 0 && form.value.description.trim().length > 0,
)

function closeModal() {
  if (isSaving.value) return
  lastPreviewKey.value = ''
  emit('close')
}

async function saveProvider() {
  if (!canSave.value) return

  const payload: ProviderCreate = {
    name: (form.value.name ?? '').trim(),
    description: (form.value.description ?? '').trim(),
    contact_email: (form.value.contact_email ?? '').trim() || undefined,
    contact_phone: (form.value.contact_phone ?? '').trim() || undefined,
    website: (form.value.website ?? '').trim() || undefined,
    city: (form.value.city ?? '').trim() || undefined,
    country: (form.value.country ?? '').trim() || undefined,
    category_ids: form.value.category_ids ?? [],
    tag_names: form.value.tag_names ?? [],
  }

  try {
    const provider = await createMutation.mutateAsync(payload)
    try {
      await enrichMutation.mutateAsync(provider.id)
    } catch {
      // The provider was created successfully; enrichment stays best-effort.
    }
    emit('created', provider.id)
    emit('close')
    await router.push(`/providers/${provider.id}`)
  } catch (error) {
    warnings.value = [(error as Error).message || 'No se pudo guardar el proveedor.']
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/50 p-4 md:p-8">
      <div class="w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl border border-border bg-surface shadow-2xl">
        <div class="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-border bg-surface/95 px-6 py-4 backdrop-blur">
          <div class="space-y-1">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">
              Importar desde web
            </p>
            <h2 class="text-xl font-semibold text-text-primary">
              {{ result?.title || 'Añadir proveedor desde resultado web' }}
            </h2>
            <p class="text-sm text-text-secondary">
              Revisa el borrador generado antes de guardarlo en el directorio.
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg border border-border p-2 text-text-muted transition-colors hover:text-text-primary"
            @click="closeModal"
          >
            <X class="h-5 w-5" />
          </button>
        </div>

        <div class="space-y-5 px-6 py-6">
          <div class="rounded-xl border border-border bg-surface-secondary px-4 py-3 text-sm text-text-secondary">
            <p class="font-medium text-text-primary">Fuente verificada</p>
            <a
              v-if="sourceUrl"
              :href="sourceUrl"
              target="_blank"
              rel="noopener"
              class="mt-1 block truncate text-primary-600 hover:underline"
            >
              {{ sourceUrl }}
            </a>
            <p v-if="provenance" class="mt-2">{{ provenance }}</p>
          </div>

          <div v-if="warnings.length" class="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <div class="flex items-start gap-2">
              <AlertCircle class="mt-0.5 h-4 w-4 shrink-0" />
              <div class="space-y-1">
                <p class="font-medium">Observaciones</p>
                <p v-for="warning in warnings" :key="warning">{{ warning }}</p>
              </div>
            </div>
          </div>

          <div v-if="previewState === 'loading'" class="flex min-h-[320px] flex-col items-center justify-center gap-4 rounded-2xl border border-border bg-surface-secondary px-6 py-16 text-center">
            <LoaderCircle class="h-10 w-10 animate-spin text-primary-600" />
            <div class="space-y-2">
              <p class="text-base font-semibold text-text-primary">Completando datos desde el sitio verificado...</p>
              <p class="max-w-xl text-sm text-text-secondary">
                La IA esta extrayendo la informacion relevante del proveedor para prellenar el formulario del directorio.
              </p>
            </div>
          </div>

          <div v-else-if="previewState === 'duplicate'" class="space-y-4 rounded-2xl border border-border bg-surface-secondary px-6 py-6">
            <div class="flex items-start gap-3">
              <AlertCircle class="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
              <div class="space-y-2">
                <p class="text-base font-semibold text-text-primary">Este proveedor ya existe en el directorio</p>
                <p class="text-sm text-text-secondary">
                  Se detecto un duplicado y se bloqueo el guardado para evitar registros repetidos.
                </p>
                <div v-if="duplicateProvider" class="flex flex-wrap items-center gap-3">
                  <AppBadge variant="warning">{{ duplicateProvider.name }}</AppBadge>
                  <RouterLink
                    :to="`/providers/${duplicateProvider.id}`"
                    class="text-sm font-medium text-primary-600 hover:underline"
                  >
                    Abrir proveedor existente
                  </RouterLink>
                </div>
              </div>
            </div>
            <div class="flex flex-wrap justify-end gap-3">
              <AppButton variant="secondary" @click="loadPreview(true)">
                <RefreshCcw class="h-4 w-4" />
                Volver a generar
              </AppButton>
              <AppButton variant="secondary" @click="closeModal">Cerrar</AppButton>
            </div>
          </div>

          <div v-else-if="previewState === 'error'" class="space-y-4 rounded-2xl border border-border bg-surface-secondary px-6 py-6">
            <div class="flex items-start gap-3">
              <AlertCircle class="mt-0.5 h-5 w-5 shrink-0 text-danger" />
              <div class="space-y-2">
                <p class="text-base font-semibold text-text-primary">No se pudo completar el borrador</p>
                <p class="text-sm text-text-secondary">
                  Reintenta la extracción o cierra el modal si prefieres seguir con otra búsqueda.
                </p>
              </div>
            </div>
            <div class="flex flex-wrap justify-end gap-3">
              <AppButton variant="secondary" @click="loadPreview(true)">
                <RefreshCcw class="h-4 w-4" />
                Reintentar
              </AppButton>
              <AppButton variant="secondary" @click="closeModal">Cancelar</AppButton>
            </div>
          </div>

          <div v-else class="space-y-5">
            <div class="flex flex-wrap items-center gap-3">
              <AppBadge variant="ai">
                <Sparkles class="h-3 w-3" />
                Borrador IA listo para revisar
              </AppBadge>
            </div>

            <ProviderFormFields
              v-model="form"
              :categories="categories"
              description-hint="La informacion fue completada a partir del sitio verificado. Ajustala antes de guardar si hace falta."
            />

            <div class="flex flex-wrap justify-end gap-3 border-t border-border pt-4">
              <AppButton variant="secondary" @click="closeModal">Cancelar</AppButton>
              <AppButton variant="secondary" :disabled="previewMutation.isPending.value || isSaving" @click="loadPreview(true)">
                <RefreshCcw class="h-4 w-4" />
                Volver a generar
              </AppButton>
              <AppButton :loading="isSaving" :disabled="!canSave" @click="saveProvider">
                Guardar en directorio
              </AppButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
