from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Category ---

class CategoryOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None

    model_config = {"from_attributes": True}


# --- Tag ---

class TagOut(BaseModel):
    id: UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


# --- Provider Categories / Tags (with metadata) ---

class ProviderCategoryOut(BaseModel):
    category: CategoryOut
    source: str
    confidence: float | None = None

    model_config = {"from_attributes": True}


class ProviderTagOut(BaseModel):
    tag: TagOut
    source: str

    model_config = {"from_attributes": True}


# --- Provider ---

class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    city: str | None = None
    country: str | None = None
    category_ids: list[UUID] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)


class ProviderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    city: str | None = None
    country: str | None = None
    category_ids: list[UUID] | None = None
    tag_names: list[str] | None = None


class ProviderOut(BaseModel):
    id: UUID
    name: str
    description: str
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    city: str | None = None
    country: str | None = None
    created_at: datetime
    updated_at: datetime
    categories: list[ProviderCategoryOut] = []
    tags: list[ProviderTagOut] = []

    model_config = {"from_attributes": True}


class ProviderListOut(BaseModel):
    id: UUID
    name: str
    description: str
    city: str | None = None
    country: str | None = None
    created_at: datetime
    categories: list[ProviderCategoryOut] = []
    tags: list[ProviderTagOut] = []

    model_config = {"from_attributes": True}


# --- Pagination ---

class PaginatedResponse(BaseModel):
    items: list[ProviderListOut]
    total: int
    page: int
    page_size: int
    total_pages: int
