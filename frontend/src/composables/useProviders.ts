import { computed, ref } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { api } from '@/lib/api'
import type {
  Provider,
  ProviderCreate,
  ProviderUpdate,
  PaginatedResponse,
  Category,
  EnrichResult,
} from '@/types/provider'

export function useProviders(params?: {
  page?: ReturnType<typeof ref<number>>
  search?: ReturnType<typeof ref<string>>
  categoryId?: ReturnType<typeof ref<string>>
  country?: ReturnType<typeof ref<string>>
}) {
  const queryClient = useQueryClient()

  const queryParams = computed(() => {
    const p = new URLSearchParams()
    if (params?.page?.value) p.set('page', String(params.page.value))
    if (params?.search?.value) p.set('search', params.search.value)
    if (params?.categoryId?.value) p.set('category_id', params.categoryId.value)
    if (params?.country?.value) p.set('country', params.country.value)
    return p.toString()
  })

  const providersQuery = useQuery({
    queryKey: ['providers', queryParams],
    queryFn: () => api.get<PaginatedResponse>(`/providers?${queryParams.value}`),
  })

  const createMutation = useMutation({
    mutationFn: (data: ProviderCreate) => api.post<Provider>('/providers', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['providers'] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProviderUpdate }) =>
      api.put<Provider>(`/providers/${id}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['providers'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/providers/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['providers'] }),
  })

  const enrichMutation = useMutation({
    mutationFn: (id: string) => api.post<EnrichResult>(`/ai/enrich/${id}`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['providers'] }),
  })

  return {
    providersQuery,
    createMutation,
    updateMutation,
    deleteMutation,
    enrichMutation,
  }
}

export function useProvider(id: ReturnType<typeof ref<string>>) {
  return useQuery({
    queryKey: ['provider', id],
    queryFn: () => api.get<Provider>(`/providers/${id.value}`),
    enabled: computed(() => !!id.value),
  })
}

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => api.get<Category[]>('/categories'),
    staleTime: 1000 * 60 * 10,
  })
}
