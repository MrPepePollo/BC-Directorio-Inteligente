import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_auth
from app.models.provider import Provider, Category, ProviderCategory, ProviderTag, Tag
from app.services.ai import categorize_provider, extract_entities, generate_embedding
from app.services.search import refresh_provider_search_index

router = APIRouter(prefix="/ai", tags=["ai"])


def slugify(text_str: str) -> str:
    text_str = text_str.lower().strip()
    text_str = re.sub(r"[^\w\s-]", "", text_str)
    return re.sub(r"[\s_]+", "-", text_str)


@router.post("/enrich/{provider_id}")
async def enrich_provider(
    provider_id: UUID,
    user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Run all AI services on a provider: categorize, extract entities, generate embedding."""
    provider = await db.get(Provider, provider_id)

    if not provider or provider.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    description = provider.description
    try:
        # 1. Categorize
        categorization = await categorize_provider(db, provider_id, description)

        # Assign AI categories
        for cat_data in categorization.get("categories", []):
            category_name = cat_data["name"].strip()
            category_slug = slugify(category_name)
            cat_result = await db.execute(
                select(Category).where(
                    (Category.name == category_name) | (Category.slug == category_slug)
                )
            )
            category = cat_result.scalar_one_or_none()
            if category:
                # Check if already assigned
                existing = await db.execute(
                    select(ProviderCategory).where(
                        ProviderCategory.provider_id == provider_id,
                        ProviderCategory.category_id == category.id,
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(ProviderCategory(
                        provider_id=provider_id,
                        category_id=category.id,
                        source="ai",
                        confidence=cat_data.get("confidence"),
                    ))

        # Assign AI tags from categorization
        for tag_name in categorization.get("tags", []):
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            slug = slugify(tag_name)
            tag_result = await db.execute(select(Tag).where(Tag.slug == slug))
            tag = tag_result.scalar_one_or_none()
            if not tag:
                tag = Tag(name=tag_name, slug=slug)
                db.add(tag)
                await db.flush()

            existing_pt = await db.execute(
                select(ProviderTag).where(
                    ProviderTag.provider_id == provider_id,
                    ProviderTag.tag_id == tag.id,
                )
            )
            if not existing_pt.scalar_one_or_none():
                db.add(ProviderTag(
                    provider_id=provider_id,
                    tag_id=tag.id,
                    source="ai",
                ))

        # 2. Extract entities
        entities = await extract_entities(db, provider_id, description)

        # 3. Generate embedding
        embedding = await generate_embedding(db, provider_id, description)

        # Store embedding in provider
        await db.execute(
            text("UPDATE providers SET embedding = :embedding WHERE id = :id"),
            {"embedding": str(embedding), "id": str(provider_id)},
        )

        await refresh_provider_search_index(db, str(provider_id))
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"La IA devolvio una respuesta invalida: {exc}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo completar el enriquecimiento del proveedor: {exc}",
        ) from exc

    return {
        "provider_id": str(provider_id),
        "categorization": categorization,
        "entities": entities,
        "embedding_generated": True,
    }


@router.post("/categorize/{provider_id}")
async def categorize_only(
    provider_id: UUID,
    user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Run only categorization on a provider."""
    provider = await db.get(Provider, provider_id)
    if not provider or provider.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    result = await categorize_provider(db, provider_id, provider.description)
    await db.commit()
    return result


@router.post("/extract/{provider_id}")
async def extract_only(
    provider_id: UUID,
    user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Run only entity extraction on a provider."""
    provider = await db.get(Provider, provider_id)
    if not provider or provider.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    result = await extract_entities(db, provider_id, provider.description)
    await db.commit()
    return result
