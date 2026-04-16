import logging
import math
import re
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db, async_session
from app.core.deps import require_auth
from app.models.provider import Provider, Category, ProviderCategory, Tag, ProviderTag
from app.schemas.provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderOut,
    ProviderListOut,
    PaginatedResponse,
)
from app.services.ai import generate_embedding
from app.services.search import refresh_provider_search_index_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


async def _generate_embedding_background(provider_id: UUID, description: str):
    """Generate and store embedding in background after create/update."""
    try:
        async with async_session() as db:
            embedding = await generate_embedding(db, provider_id, description)
            await db.execute(
                text("UPDATE providers SET search_embedding = :embedding WHERE id = :id"),
                {"embedding": str(embedding), "id": str(provider_id)},
            )
            await db.commit()
            logger.info(f"Embedding generated for provider {provider_id}")
        await refresh_provider_search_index_background(str(provider_id))
    except Exception as e:
        logger.error(f"Failed to generate embedding for provider {provider_id}: {e}")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)


async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    """Get existing tags or create new ones."""
    tags = []
    seen_slugs: set[str] = set()
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        slug = slugify(name)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        result = await db.execute(select(Tag).where(Tag.slug == slug))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.add(tag)
            await db.flush()
        tags.append(tag)
    return tags


def _dedupe_keep_order[T](items: list[T]) -> list[T]:
    seen: set[T] = set()
    result: list[T] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _provider_query():
    """Base query with eager loading of categories and tags."""
    return (
        select(Provider)
        .where(Provider.deleted_at.is_(None))
        .options(
            selectinload(Provider.categories).selectinload(ProviderCategory.category),
            selectinload(Provider.tags).selectinload(ProviderTag.tag),
        )
    )


# --- LIST ---

@router.get("", response_model=PaginatedResponse)
async def list_providers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    category_id: UUID | None = Query(None),
    country: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = _provider_query()

    # Text search filter
    if search:
        query = query.where(
            or_(
                Provider.name.ilike(f"%{search}%"),
                Provider.description.ilike(f"%{search}%"),
            )
        )

    # Category filter
    if category_id:
        query = query.where(
            Provider.id.in_(
                select(ProviderCategory.provider_id).where(
                    ProviderCategory.category_id == category_id
                )
            )
        )

    # Country filter
    if country:
        query = query.where(Provider.country.ilike(f"%{country}%"))

    # Count total
    count_query = select(func.count()).select_from(
        query.with_only_columns(Provider.id).subquery()
    )
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(Provider.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    providers = result.scalars().unique().all()

    return PaginatedResponse(
        items=[ProviderListOut.model_validate(p) for p in providers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# --- GET ONE ---

@router.get("/{provider_id}", response_model=ProviderOut)
async def get_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    query = _provider_query().where(Provider.id == provider_id)
    result = await db.execute(query)
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    return ProviderOut.model_validate(provider)


# --- CREATE ---

@router.post("", response_model=ProviderOut, status_code=201)
async def create_provider(
    data: ProviderCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    provider = Provider(
        name=data.name,
        description=data.description,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        website=data.website,
        logo_url=data.logo_url,
        city=data.city,
        country=data.country,
        created_by=user_id,
    )
    db.add(provider)
    await db.flush()

    # Assign categories
    for cat_id in _dedupe_keep_order(data.category_ids):
        cat = await db.get(Category, cat_id)
        if cat:
            db.add(ProviderCategory(
                provider_id=provider.id,
                category_id=cat_id,
                source="manual",
            ))

    # Create/assign tags
    if data.tag_names:
        tags = await _get_or_create_tags(db, _dedupe_keep_order(data.tag_names))
        for tag in tags:
            db.add(ProviderTag(
                provider_id=provider.id,
                tag_id=tag.id,
                source="manual",
            ))

    await db.commit()

    # Generate embedding in background
    background_tasks.add_task(
        _generate_embedding_background, provider.id, provider.description
    )

    # Reload with relationships
    query = _provider_query().where(Provider.id == provider.id)
    result = await db.execute(query)
    provider = result.scalar_one()

    return ProviderOut.model_validate(provider)


# --- UPDATE ---

@router.put("/{provider_id}", response_model=ProviderOut)
async def update_provider(
    provider_id: UUID,
    data: ProviderUpdate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(Provider, provider_id)

    if not provider or provider.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    if str(provider.created_by) != user_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    # Update scalar fields
    update_data = data.model_dump(exclude_unset=True, exclude={"category_ids", "tag_names"})
    for key, value in update_data.items():
        setattr(provider, key, value)

    # Update categories if provided
    if data.category_ids is not None:
        desired_category_ids = set(_dedupe_keep_order(data.category_ids))
        valid_category_ids: set[UUID] = set()
        if desired_category_ids:
            valid_result = await db.execute(
                select(Category.id).where(Category.id.in_(list(desired_category_ids)))
            )
            valid_category_ids = set(valid_result.scalars().all())

        existing_result = await db.execute(
            select(ProviderCategory).where(
                ProviderCategory.provider_id == provider_id
            )
        )
        existing_categories = existing_result.scalars().all()
        existing_by_category_id = {
            pc.category_id: pc
            for pc in existing_categories
        }

        for pc in existing_categories:
            if pc.category_id not in valid_category_ids:
                await db.delete(pc)
            else:
                pc.source = "manual"
                pc.confidence = None

        for cat_id in valid_category_ids:
            if cat_id not in existing_by_category_id:
                db.add(ProviderCategory(
                    provider_id=provider_id,
                    category_id=cat_id,
                    source="manual",
                ))

    # Update tags if provided
    if data.tag_names is not None:
        desired_tag_names_by_slug = {
            slugify(name.strip()): name.strip()
            for name in data.tag_names
            if name.strip()
        }
        tags = await _get_or_create_tags(
            db,
            list(desired_tag_names_by_slug.values()),
        )
        desired_tag_ids = {tag.id for tag in tags}

        existing_tags_result = await db.execute(
            select(ProviderTag).where(ProviderTag.provider_id == provider_id)
        )
        existing_tags = existing_tags_result.scalars().all()
        existing_by_tag_id = {
            pt.tag_id: pt
            for pt in existing_tags
        }

        for pt in existing_tags:
            if pt.tag_id not in desired_tag_ids:
                await db.delete(pt)
            else:
                pt.source = "manual"

        for tag in tags:
            if tag.id not in existing_by_tag_id:
                db.add(ProviderTag(
                    provider_id=provider_id,
                    tag_id=tag.id,
                    source="manual",
                ))

    await db.commit()

    # Regenerate embedding if description changed
    if data.description is not None:
        background_tasks.add_task(
            _generate_embedding_background, provider_id, data.description
        )

    query = _provider_query().where(Provider.id == provider_id)
    result = await db.execute(query)
    provider = result.scalar_one()

    return ProviderOut.model_validate(provider)


# --- DELETE (soft) ---

@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: UUID,
    user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(Provider, provider_id)

    if not provider or provider.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    if str(provider.created_by) != user_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    from datetime import datetime, timezone
    provider.deleted_at = datetime.now(timezone.utc)
    await db.commit()
