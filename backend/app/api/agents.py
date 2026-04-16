from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_auth
from app.models.provider import Provider, ProviderCategory, ProviderTag
from app.services.agent import run_enrichment_agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/enrich/{provider_id}")
async def agent_enrich_provider(
    provider_id: UUID,
    user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Run the ReAct enrichment agent on a provider.

    The agent autonomously decides which tools to use to complete
    the provider's profile: web search, contact extraction,
    categorization, entity extraction, and embedding generation.

    Returns a step-by-step trace of the agent's reasoning and actions.
    """
    from sqlalchemy import select

    query = (
        select(Provider)
        .where(Provider.id == provider_id, Provider.deleted_at.is_(None))
        .options(
            selectinload(Provider.categories).selectinload(ProviderCategory.category),
            selectinload(Provider.tags).selectinload(ProviderTag.tag),
        )
    )
    result = await db.execute(query)
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    try:
        agent_result = await run_enrichment_agent(db, provider)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando el agente de enriquecimiento: {exc}",
        ) from exc

    return agent_result.to_dict()
