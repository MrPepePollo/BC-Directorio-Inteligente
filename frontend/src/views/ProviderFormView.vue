<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CheckCircle2, CircleAlert, Loader2 } from 'lucide-vue-next'
import { useProviders, useProvider, useCategories } from '@/composables/useProviders'
import AppButton from '@/components/ui/AppButton.vue'
import ProviderFormFields from '@/components/providers/ProviderFormFields.vue'
import type { ProviderDraftForm, EnrichResult } from '@/types/provider'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const providerId = ref(route.params.id as string)

const { data: categories } = useCategories()
const { createMutation, updateMutation, enrichMutation } = useProviders()

// Form state
const form = ref<ProviderDraftForm>({
  name: '',
  description: '',
  contact_email: '',
  contact_phone: '',
  website: '',
  city: '',
  country: '',
  category_ids: [] as string[],
  tag_names: [] as string[],
})
const enrichResult = ref<EnrichResult | null>(null)
const isRedirecting = ref(false)
const feedback = ref<{
  type: 'success' | 'error' | 'loading'
  title: string
  message: string
} | null>(null)

// Load existing data in edit mode
if (isEdit.value) {
  const { data: provider } = useProvider(providerId)
  onMounted(() => {
    // Watch for data to load
    const unwatch = setInterval(() => {
      if (provider.value) {
        form.value = {
          name: provider.value.name,
          description: provider.value.description,
          contact_email: provider.value.contact_email ?? '',
          contact_phone: provider.value.contact_phone ?? '',
          website: provider.value.website ?? '',
          city: provider.value.city ?? '',
          country: provider.value.country ?? '',
          category_ids: provider.value.categories.map((pc) => pc.category.id),
          tag_names: provider.value.tags.map((pt) => pt.tag.name),
        }
        clearInterval(unwatch)
      }
    }, 100)
    setTimeout(() => clearInterval(unwatch), 5000)
  })
}

async function onSubmit() {
  feedback.value = {
    type: 'loading',
    title: isEdit.value ? 'Guardando cambios' : 'Creando proveedor',
    message: 'Estamos actualizando la informacion del directorio.',
  }

  const data = {
    ...form.value,
    contact_email: form.value.contact_email || undefined,
    contact_phone: form.value.contact_phone || undefined,
    website: form.value.website || undefined,
    city: form.value.city || undefined,
    country: form.value.country || undefined,
  }

  try {
    if (isEdit.value) {
      await updateMutation.mutateAsync({ id: providerId.value, data })
      feedback.value = {
        type: 'success',
        title: 'Cambios guardados',
        message: 'Te llevamos de vuelta a la ficha del proveedor.',
      }
      isRedirecting.value = true
      window.setTimeout(() => router.push(`/providers/${providerId.value}`), 850)
    } else {
      const result = await createMutation.mutateAsync(data)
      feedback.value = {
        type: 'success',
        title: 'Proveedor creado',
        message: 'Te llevamos a la ficha. La IA puede seguir completando datos en segundo plano.',
      }
      isRedirecting.value = true
      void enrichMutation.mutateAsync(result.id).then((value) => {
        enrichResult.value = value
      }).catch(() => {
        // Enrichment is best-effort and must not block the saved provider flow.
      })
      window.setTimeout(() => router.push(`/providers/${result.id}`), 850)
    }
  } catch (error) {
    feedback.value = {
      type: 'error',
      title: 'No se pudo guardar',
      message: error instanceof Error ? error.message : 'Revisa los datos e intenta nuevamente.',
    }
  }
}

const isSubmitting = computed(
  () => createMutation.isPending?.value || updateMutation.isPending?.value || isRedirecting.value,
)
</script>

<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <!-- Back -->
    <button
      @click="router.back()"
      class="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
    >
      <ArrowLeft class="w-4 h-4" />
      Volver
    </button>

    <h1 class="text-2xl font-bold text-text-primary">
      {{ isEdit ? 'Editar proveedor' : 'Nuevo proveedor' }}
    </h1>

    <div
      v-if="feedback"
      role="status"
      aria-live="polite"
      :class="[
        'flex items-start gap-3 rounded-lg border px-4 py-3 text-sm',
        feedback.type === 'success'
          ? 'border-green-700/50 bg-green-950/45 text-green-100'
          : feedback.type === 'error'
            ? 'border-red-700/50 bg-red-950/45 text-red-100'
            : 'border-primary-700/50 bg-primary-950/35 text-primary-100',
      ]"
    >
      <CheckCircle2 v-if="feedback.type === 'success'" class="mt-0.5 h-4 w-4 shrink-0" />
      <CircleAlert v-else-if="feedback.type === 'error'" class="mt-0.5 h-4 w-4 shrink-0" />
      <Loader2 v-else class="mt-0.5 h-4 w-4 shrink-0 animate-spin" />
      <span>
        <span class="block font-semibold">{{ feedback.title }}</span>
        <span class="mt-0.5 block text-text-secondary">{{ feedback.message }}</span>
      </span>
    </div>

    <form @submit.prevent="onSubmit" class="space-y-6">
      <ProviderFormFields v-model="form" :categories="categories" :disabled="isSubmitting" />

      <!-- Submit -->
      <div class="flex justify-end gap-3">
        <AppButton type="button" variant="secondary" :disabled="isSubmitting" @click="router.back()">Cancelar</AppButton>
        <AppButton type="submit" :loading="isSubmitting">
          {{ isRedirecting ? 'Redirigiendo...' : isEdit ? 'Guardar cambios' : 'Crear proveedor' }}
        </AppButton>
      </div>
    </form>
  </div>
</template>
