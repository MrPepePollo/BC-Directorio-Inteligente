<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { useProviders, useProvider, useCategories } from '@/composables/useProviders'
import AppButton from '@/components/ui/AppButton.vue'
import ProviderFormFields from '@/components/providers/ProviderFormFields.vue'
import type { ProviderDraftForm } from '@/types/provider'

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
const enrichResult = ref<Record<string, unknown> | null>(null)

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
  const data = {
    ...form.value,
    contact_email: form.value.contact_email || undefined,
    contact_phone: form.value.contact_phone || undefined,
    website: form.value.website || undefined,
    city: form.value.city || undefined,
    country: form.value.country || undefined,
  }

  if (isEdit.value) {
    await updateMutation.mutateAsync({ id: providerId.value, data })
    router.push(`/providers/${providerId.value}`)
  } else {
    const result = await createMutation.mutateAsync(data)
    // Auto-enrich after creation
    try {
      enrichResult.value = await enrichMutation.mutateAsync(result.id)
    } catch {
      // Enrich is optional, don't block
    }
    router.push(`/providers/${result.id}`)
  }
}

const isSubmitting = computed(
  () => createMutation.isPending?.value || updateMutation.isPending?.value,
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

    <form @submit.prevent="onSubmit" class="space-y-6">
      <ProviderFormFields v-model="form" :categories="categories" />

      <!-- Submit -->
      <div class="flex justify-end gap-3">
        <AppButton type="button" variant="secondary" @click="router.back()">Cancelar</AppButton>
        <AppButton type="submit" :loading="isSubmitting">
          {{ isEdit ? 'Guardar cambios' : 'Crear proveedor' }}
        </AppButton>
      </div>
    </form>
  </div>
</template>
