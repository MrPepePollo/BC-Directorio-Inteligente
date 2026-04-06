<script setup lang="ts">
import { computed, ref } from 'vue'
import { Search, Filter, ChevronLeft, ChevronRight, Download, Upload, Plus } from 'lucide-vue-next'
import { useProviders, useCategories } from '@/composables/useProviders'
import { useCsv } from '@/composables/useCsv'
import { useAuth } from '@/composables/useAuth'
import ProviderCard from '@/components/ProviderCard.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import { RouterLink } from 'vue-router'

const { exportProviders, parseImportCsv } = useCsv()
const { user } = useAuth()
const fileInput = ref<HTMLInputElement>()
const importLoading = ref(false)

const page = ref(1)
const search = ref('')
const categoryId = ref('')
const country = ref('')
const searchInput = ref('')
let debounceTimer: ReturnType<typeof setTimeout>

const { providersQuery, createMutation, enrichMutation } = useProviders({ page, search, categoryId, country })
const { data: categories } = useCategories()

const categoryOptions = computed(() => [
  { label: 'Todas las categorias', value: '', description: 'Sin filtro aplicado' },
  ...(
    categories.value?.map((category) => ({
      label: category.name,
      value: category.id,
    })) ?? []
  ),
])

function onSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    search.value = searchInput.value
    page.value = 1
  }, 300)
}

function clearFilters() {
  searchInput.value = ''
  search.value = ''
  categoryId.value = ''
  country.value = ''
  page.value = 1
}

function handleExport() {
  const items = providersQuery.data?.value?.items
  if (items?.length) exportProviders(items)
}

function resolveCategoryIds(categoryNames: string): string[] {
  if (!categoryNames || !categories.value) return []
  return categoryNames
    .split(';')
    .map((name) => name.trim())
    .filter(Boolean)
    .map((name) => categories.value!.find((c) => c.name === name)?.id)
    .filter((id): id is string => !!id)
}

async function handleImport(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  importLoading.value = true
  try {
    const rows = await parseImportCsv(file)
    for (const row of rows) {
      const provider = await createMutation.mutateAsync({
        name: row.nombre || row.name || '',
        description: row.descripcion || row.description || '',
        contact_email: row.email || row.contact_email || undefined,
        contact_phone: row.telefono || row.contact_phone || undefined,
        website: row.website || undefined,
        city: row.ciudad || row.city || undefined,
        country: row.pais || row.country || undefined,
        category_ids: resolveCategoryIds(row.categorias || row.categories || ''),
        tag_names: (row.tags || '').split(';').map((t: string) => t.trim()).filter(Boolean),
      })
      // Auto-enrich: categorize + generate embedding
      try {
        await enrichMutation.mutateAsync(provider.id)
      } catch {
        // Enrich is optional
      }
    }
  } catch (e) {
    alert('Error al importar: ' + (e as Error).message)
  } finally {
    importLoading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-2">
        <span class="inline-flex rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300">
          Red de proveedores
        </span>
        <h1 class="text-4xl font-bold text-text-primary">Directorio de Proveedores</h1>
        <p class="text-sm text-text-muted">
          {{ providersQuery.data?.value?.total ?? 0 }} proveedores registrados
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <RouterLink
          v-if="user"
          to="/providers/new"
          class="inline-flex items-center gap-2 rounded-xl border border-transparent bg-linear-to-b from-primary-500 to-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-[0_24px_60px_-28px_rgb(46_108_234_/_0.42)] transition-[transform,filter] duration-200 hover:-translate-y-0.5"
        >
          <Plus class="h-4 w-4" />
          Nuevo proveedor
        </RouterLink>
        <input ref="fileInput" type="file" accept=".csv" class="hidden" @change="handleImport" />
        <AppButton variant="secondary" size="sm" @click="fileInput?.click()" :loading="importLoading">
          <Upload class="w-4 h-4" />
          <span class="hidden sm:block">Importar</span>
        </AppButton>
        <AppButton variant="secondary" size="sm" @click="handleExport">
          <Download class="w-4 h-4" />
          <span class="hidden sm:block">Exportar</span>
        </AppButton>
      </div>
    </div>

    <!-- Filters -->
    <div class="app-panel rounded-[1.6rem] p-3 sm:p-4">
      <div class="flex flex-col gap-3 sm:flex-row">
        <div class="field-shell flex-1 px-4">
          <Search class="h-4 w-4 shrink-0 text-text-muted" />
          <input
            v-model="searchInput"
            @input="onSearch"
            placeholder="Buscar proveedores, especialidades o ciudades..."
            class="w-full bg-transparent py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
          />
        </div>
        <AppSelect
          v-model="categoryId"
          :options="categoryOptions"
          placeholder="Todas las categorias"
          @change="page = 1"
          class="sm:max-w-[18rem]"
        />
        <AppButton
          v-if="search || categoryId || country"
          variant="ghost"
          size="sm"
          @click="clearFilters"
        >
          <Filter class="w-4 h-4" />
          Limpiar
        </AppButton>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="providersQuery.isLoading?.value" class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <SkeletonCard v-for="i in 6" :key="i" />
    </div>

    <!-- Empty -->
    <EmptyState
      v-else-if="!providersQuery.data?.value?.items?.length"
      title="Sin proveedores"
      description="No se encontraron proveedores con los filtros actuales."
    >
      <AppButton variant="primary" @click="clearFilters">Limpiar filtros</AppButton>
    </EmptyState>

    <!-- Grid -->
    <div v-else class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <ProviderCard
        v-for="provider in providersQuery.data.value.items"
        :key="provider.id"
        :provider="provider"
      />
    </div>

    <!-- Pagination -->
    <div
      v-if="providersQuery.data?.value && providersQuery.data.value.total_pages > 1"
      class="flex items-center justify-center gap-2 pt-2"
    >
      <AppButton variant="secondary" size="sm" :disabled="page <= 1" @click="page--">
        <ChevronLeft class="w-4 h-4" />
      </AppButton>
      <span class="text-sm text-text-secondary px-3">
        {{ page }} / {{ providersQuery.data.value.total_pages }}
      </span>
      <AppButton
        variant="secondary"
        size="sm"
        :disabled="page >= providersQuery.data.value.total_pages"
        @click="page++"
      >
        <ChevronRight class="w-4 h-4" />
      </AppButton>
    </div>
  </div>
</template>
