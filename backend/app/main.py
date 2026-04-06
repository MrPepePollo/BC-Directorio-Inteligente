from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.providers import router as providers_router
from app.api.categories import router as categories_router
from app.api.search import router as search_router
from app.api.ai import router as ai_router
from app.services.search import ensure_search_schema

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(providers_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(ai_router, prefix="/api")


@app.on_event("startup")
async def startup_tasks():
    await ensure_search_schema()


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}
