from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AppliedFilters(BaseModel):
    country: str | None = None
    city: str | None = None
    categories: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)


class DirectorySearchResult(BaseModel):
    id: UUID
    name: str
    description: str
    city: str | None = None
    country: str | None = None
    score: float
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    metadata_score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)


class WebSearchResult(BaseModel):
    title: str
    snippet: str
    url: str
    source: str
    city: str | None = None
    country: str | None = None
    detected_categories: list[str] = Field(default_factory=list)
    detected_tags: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)


class SearchRecommendation(BaseModel):
    label: str
    target_type: str
    target_id: str
    reason: str


class SearchAnalysis(BaseModel):
    summary: str
    recommendations: list[SearchRecommendation] = Field(default_factory=list)


class SearchMeta(BaseModel):
    used_llm_parser: bool = False
    used_web_search: bool = False
    strategy: str
    web_provider: str | None = None
    warning: str | None = None


class SearchResponse(BaseModel):
    query: str
    interpreted_query: str
    applied_filters: AppliedFilters
    directory_results: list[DirectorySearchResult] = Field(default_factory=list)
    web_results: list[WebSearchResult] = Field(default_factory=list)
    analysis: SearchAnalysis | None = None
    session_id: UUID
    meta: SearchMeta


class SearchFollowupRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=500)


class SearchFollowupResponse(BaseModel):
    answer: str
    referenced_results: list[str] = Field(default_factory=list)
    warning: str | None = None


class SearchSessionMessageOut(BaseModel):
    id: UUID
    role: str
    message: str
    response_payload: dict
    created_at: datetime


class WebProviderImportPreviewRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)
    regenerate: bool = False


class WebProviderImportDraft(BaseModel):
    name: str = ""
    description: str = ""
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    city: str | None = None
    country: str | None = None
    category_ids: list[UUID] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)


class DuplicateProviderSummary(BaseModel):
    id: UUID
    name: str
    website: str | None = None


class WebProviderImportPreviewResponse(BaseModel):
    status: str
    draft: WebProviderImportDraft | None = None
    source_url: str
    warnings: list[str] = Field(default_factory=list)
    duplicate_provider: DuplicateProviderSummary | None = None
    provenance: str
