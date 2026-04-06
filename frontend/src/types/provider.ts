export interface Category {
  id: string
  name: string
  slug: string
  description?: string
  icon?: string
}

export interface Tag {
  id: string
  name: string
  slug: string
}

export interface ProviderCategory {
  category: Category
  source: 'manual' | 'ai'
  confidence?: number
}

export interface ProviderTag {
  tag: Tag
  source: 'manual' | 'ai'
}

export interface Provider {
  id: string
  name: string
  description: string
  contact_email?: string
  contact_phone?: string
  website?: string
  logo_url?: string
  city?: string
  country?: string
  created_at: string
  updated_at: string
  categories: ProviderCategory[]
  tags: ProviderTag[]
}

export interface ProviderCreate {
  name: string
  description: string
  contact_email?: string
  contact_phone?: string
  website?: string
  logo_url?: string
  city?: string
  country?: string
  category_ids: string[]
  tag_names: string[]
}

export type ProviderUpdate = Partial<ProviderCreate>

export interface ProviderDraftForm {
  name: string
  description: string
  contact_email: string
  contact_phone: string
  website: string
  city: string
  country: string
  category_ids: string[]
  tag_names: string[]
}

export interface PaginatedResponse {
  items: Provider[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AppliedFilters {
  country?: string
  city?: string
  categories: string[]
  technologies: string[]
  specialties: string[]
}

export interface DirectorySearchResult {
  id: string
  name: string
  description: string
  city?: string
  country?: string
  score: number
  semantic_score: number
  lexical_score: number
  metadata_score: number
  match_reasons: string[]
}

export interface WebSearchResult {
  title: string
  snippet: string
  url: string
  source: string
  city?: string
  country?: string
  detected_categories: string[]
  detected_tags: string[]
  match_reasons: string[]
}

export interface SearchRecommendation {
  label: string
  target_type: string
  target_id: string
  reason: string
}

export interface SearchAnalysis {
  summary: string
  recommendations: SearchRecommendation[]
}

export interface SearchMeta {
  used_llm_parser: boolean
  used_web_search: boolean
  strategy: string
  web_provider?: string | null
  warning?: string | null
}

export interface SearchResponse {
  query: string
  interpreted_query: string
  applied_filters: AppliedFilters
  directory_results: DirectorySearchResult[]
  web_results: WebSearchResult[]
  analysis?: SearchAnalysis | null
  session_id: string
  meta: SearchMeta
}

export interface SearchFollowupResponse {
  answer: string
  referenced_results: string[]
  warning?: string | null
}

export interface WebProviderImportPreviewRequest {
  url: string
  regenerate?: boolean
}

export interface WebProviderImportDuplicate {
  id: string
  name: string
  website?: string | null
}

export interface WebProviderImportPreviewResponse {
  status: 'ready' | 'duplicate' | 'error'
  draft: ProviderDraftForm | null
  source_url: string
  warnings: string[]
  duplicate_provider?: WebProviderImportDuplicate | null
  provenance: string
}

export interface EnrichResult {
  provider_id: string
  categorization: {
    categories: { name: string; confidence: number }[]
    tags: string[]
  }
  entities: {
    services: string[]
    technologies: string[]
    specialties: string[]
    suggested_city?: string
    suggested_country?: string
  }
  embedding_generated: boolean
}
