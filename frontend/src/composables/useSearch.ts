import { ref, computed } from 'vue'
import { useMutation, useQuery } from '@tanstack/vue-query'
import { api } from '@/lib/api'
import type { SearchFollowupResponse, SearchResponse } from '@/types/provider'

export interface SearchFilters {
  categoryId?: string
  country?: string
  analyze?: boolean
}

const DEFAULT_SEARCH_FILTERS: SearchFilters = {
  analyze: false,
}

function buildSearchParams(query: string, filters: SearchFilters, includeWeb = false) {
  const p = new URLSearchParams()
  p.set('q', query)
  if (filters.categoryId) p.set('category_id', filters.categoryId)
  if (filters.country) p.set('country', filters.country)
  if (includeWeb) p.set('include_web', 'true')
  if (typeof filters.analyze === 'boolean') p.set('analyze', String(filters.analyze))
  return p.toString()
}

export function useSemanticSearch() {
  const query = ref('')
  const filters = ref<SearchFilters>({ ...DEFAULT_SEARCH_FILTERS })
  const manualResponse = ref<SearchResponse | null>(null)
  const enabled = computed(() => query.value.trim().length >= 2)

  const queryParams = computed(() => buildSearchParams(query.value, filters.value))

  const searchQuery = useQuery({
    queryKey: ['search', queryParams],
    queryFn: () => api.get<SearchResponse>(`/search?${queryParams.value}`),
    enabled,
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  const followupAnswer = ref<SearchFollowupResponse | null>(null)
  const currentResponse = computed(() => manualResponse.value ?? searchQuery.data?.value ?? null)

  const webSearchMutation = useMutation({
    mutationFn: ({ q, searchFilters }: { q: string; searchFilters: SearchFilters }) =>
      api.get<SearchResponse>(`/search?${buildSearchParams(q, searchFilters, true)}`),
    onSuccess: (data) => {
      manualResponse.value = data
      followupAnswer.value = null
    },
  })

  const followupMutation = useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      api.post<SearchFollowupResponse>(`/search/sessions/${sessionId}/messages`, { message }),
    onSuccess: (data) => {
      followupAnswer.value = data
    },
  })

  return {
    query,
    filters,
    response: currentResponse,
    directoryResults: computed(() => currentResponse.value?.directory_results ?? []),
    webResults: computed(() => currentResponse.value?.web_results ?? []),
    analysis: computed(() => currentResponse.value?.analysis ?? null),
    resultCount: computed(() => currentResponse.value?.directory_results?.length ?? 0),
    sessionId: computed(() => currentResponse.value?.session_id ?? ''),
    meta: computed(() => currentResponse.value?.meta ?? null),
    isLoading: computed(() => !currentResponse.value && (searchQuery.isLoading.value || searchQuery.isFetching.value)),
    isSearchingWeb: webSearchMutation.isPending,
    isError: searchQuery.isError,
    isAsking: followupMutation.isPending,
    followupAnswer,
    search: (q: string) => {
      query.value = q
      manualResponse.value = null
      followupAnswer.value = null
    },
    setFilters: (f: SearchFilters) => {
      filters.value = f
      manualResponse.value = null
      followupAnswer.value = null
    },
    expandWeb: (q: string) => {
      const normalizedQuery = q.trim()
      if (query.value !== normalizedQuery) {
        manualResponse.value = null
      }
      query.value = normalizedQuery
      followupAnswer.value = null
      return webSearchMutation.mutateAsync({
        q: normalizedQuery,
        searchFilters: filters.value,
      })
    },
    askFollowup: (sessionId: string, message: string) =>
      followupMutation.mutateAsync({ sessionId, message }),
    reset: () => {
      query.value = ''
      manualResponse.value = null
      followupAnswer.value = null
      filters.value = { ...DEFAULT_SEARCH_FILTERS }
    },
  }
}
