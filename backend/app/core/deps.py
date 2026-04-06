from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings

import httpx

settings = get_settings()


async def get_current_user_id(authorization: str | None = Header(None)) -> str | None:
    """Extract user ID from Supabase JWT via Supabase Auth API.
    Returns None if no token provided (public access).
    Raises 401 if token is invalid.
    """
    if not authorization:
        return None

    token = authorization.replace("Bearer ", "")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_anon_key,
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Token invalido")

    user = response.json()
    return user["id"]


async def require_auth(user_id: str | None = Depends(get_current_user_id)) -> str:
    """Require authenticated user. Raises 401 if not authenticated."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Autenticacion requerida")
    return user_id
