<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Sparkles, X } from 'lucide-vue-next'
import type { Category, ProviderDraftForm } from '@/types/provider'
import AppButton from '@/components/ui/AppButton.vue'
import AppCard from '@/components/ui/AppCard.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'

const props = defineProps<{
  modelValue: ProviderDraftForm
  categories?: Category[]
  disabled?: boolean
  descriptionHint?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ProviderDraftForm]
}>()

const newTag = ref('')

const form = computed({
  get: () => props.modelValue,
  set: (value: ProviderDraftForm) => emit('update:modelValue', value),
})

function updateField<K extends keyof ProviderDraftForm>(key: K, value: ProviderDraftForm[K]) {
  form.value = {
    ...form.value,
    [key]: value,
  }
}

function toggleCategory(catId: string) {
  const hasCategory = form.value.category_ids.includes(catId)
  updateField(
    'category_ids',
    hasCategory
      ? form.value.category_ids.filter((id) => id !== catId)
      : [...form.value.category_ids, catId],
  )
}

function addTag() {
  const tag = newTag.value.trim()
  if (!tag || form.value.tag_names.includes(tag)) {
    newTag.value = ''
    return
  }
  updateField('tag_names', [...form.value.tag_names, tag])
  newTag.value = ''
}

function removeTag(tag: string) {
  updateField(
    'tag_names',
    form.value.tag_names.filter((existingTag) => existingTag !== tag),
  )
}
</script>

<template>
  <div class="space-y-6">
    <AppCard>
      <h2 class="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-4">
        Informacion basica
      </h2>
      <div class="space-y-4">
        <AppInput
          :model-value="form.name"
          label="Nombre del proveedor"
          placeholder="Ej: TechSolutions S.A."
          required
          :disabled="disabled"
          @update:model-value="updateField('name', $event)"
        />
        <AppTextarea
          :model-value="form.description"
          label="Descripcion"
          placeholder="Describe los servicios, tecnologias y especialidades del proveedor..."
          :rows="5"
          required
          :disabled="disabled"
          @update:model-value="updateField('description', $event)"
        />
        <p class="text-xs text-text-muted flex items-center gap-1">
          <Sparkles class="w-3 h-3" />
          {{ descriptionHint || 'La IA analizara esta descripcion para categorizar y generar tags automaticamente.' }}
        </p>
      </div>
    </AppCard>

    <AppCard>
      <h2 class="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-4">
        Contacto
      </h2>
      <div class="grid gap-4 sm:grid-cols-2">
        <AppInput
          :model-value="form.contact_email"
          label="Email"
          type="email"
          placeholder="contacto@empresa.com"
          :disabled="disabled"
          @update:model-value="updateField('contact_email', $event)"
        />
        <AppInput
          :model-value="form.contact_phone"
          label="Telefono"
          placeholder="+52 55 1234 5678"
          :disabled="disabled"
          @update:model-value="updateField('contact_phone', $event)"
        />
        <AppInput
          :model-value="form.website"
          label="Sitio web"
          placeholder="https://empresa.com"
          :disabled="disabled"
          @update:model-value="updateField('website', $event)"
        />
        <AppInput
          :model-value="form.city"
          label="Ciudad"
          placeholder="Ciudad de Mexico"
          :disabled="disabled"
          @update:model-value="updateField('city', $event)"
        />
        <AppInput
          :model-value="form.country"
          label="Pais"
          placeholder="Mexico"
          :disabled="disabled"
          @update:model-value="updateField('country', $event)"
        />
      </div>
    </AppCard>

    <AppCard>
      <h2 class="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-4">
        Categorias
      </h2>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="cat in categories"
          :key="cat.id"
          type="button"
          :disabled="disabled"
          @click="toggleCategory(cat.id)"
          :class="[
            'px-3 py-1.5 text-sm rounded-full border transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
            form.category_ids.includes(cat.id)
              ? 'bg-primary-600 text-white border-primary-600'
              : 'bg-surface border-border text-text-secondary hover:border-primary-300',
          ]"
        >
          {{ cat.name }}
        </button>
      </div>
    </AppCard>

    <AppCard>
      <h2 class="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-4">
        Tags
      </h2>
      <div class="flex gap-2 mb-3">
        <input
          v-model="newTag"
          :disabled="disabled"
          @keydown.enter.prevent="addTag"
          placeholder="Agregar tag y presiona Enter..."
          class="flex-1 px-3 py-2 text-sm rounded-md border border-border bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <AppButton type="button" variant="secondary" size="sm" :disabled="disabled" @click="addTag">
          <Plus class="w-4 h-4" />
        </AppButton>
      </div>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="tag in form.tag_names"
          :key="tag"
          class="inline-flex items-center gap-1 px-2 py-1 text-sm bg-surface-secondary border border-border rounded-full"
        >
          {{ tag }}
          <button
            type="button"
            :disabled="disabled"
            @click="removeTag(tag)"
            class="text-text-muted hover:text-danger cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X class="w-3 h-3" />
          </button>
        </span>
      </div>
    </AppCard>
  </div>
</template>
