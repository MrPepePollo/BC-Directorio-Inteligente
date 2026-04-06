from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_auth
from app.schemas.search import (
    SearchFollowupRequest,
    SearchFollowupResponse,
    SearchResponse,
    WebProviderImportPreviewRequest,
    WebProviderImportPreviewResponse,
)
from app.services.search import answer_search_followup, generate_web_import_preview, run_search

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def intelligent_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
    category_id: UUID | None = Query(None),
    country: str | None = Query(None),
    include_web: bool = Query(False),
    analyze: bool = Query(True),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    return await run_search(
        db=db,
        query=q,
        limit=limit,
        category_id=str(category_id) if category_id else None,
        country=country,
        include_web=include_web,
        analyze=analyze,
    )


@router.post("/sessions/{session_id}/messages", response_model=SearchFollowupResponse)
async def search_followup(
    session_id: UUID,
    payload: SearchFollowupRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchFollowupResponse:
    try:
        return await answer_search_followup(db, str(session_id), payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/web-results/import-preview", response_model=WebProviderImportPreviewResponse)
async def preview_web_result_import(
    session_id: UUID,
    payload: WebProviderImportPreviewRequest,
    _user_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> WebProviderImportPreviewResponse:
    try:
        return await generate_web_import_preview(
            db,
            str(session_id),
            payload.url,
            regenerate=payload.regenerate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
