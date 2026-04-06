import html
import json
import logging
import re
import unicodedata
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
import openai
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session, engine
from app.models.provider import Category, Provider
from app.schemas.search import (
    AppliedFilters,
    DuplicateProviderSummary,
    DirectorySearchResult,
    SearchAnalysis,
    SearchFollowupResponse,
    WebProviderImportDraft,
    WebProviderImportPreviewResponse,
    SearchMeta,
    SearchRecommendation,
    SearchResponse,
    WebSearchResult,
)
from app.services.ai import CATEGORY_KEYWORDS, TAG_KEYWORDS, generate_embedding

settings = get_settings()
logger = logging.getLogger(__name__)
client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
RESPONSE_TEXT_CONFIG = {"verbosity": "low"}
QUERY_PARSER_MAX_OUTPUT_TOKENS = 5000
WEB_SEARCH_MAX_OUTPUT_TOKENS = 65000
WEB_SEARCH_FINAL_RESULT_LIMIT = 3
WEB_SEARCH_CANDIDATE_MULTIPLIER = 2
WEB_IMPORT_MAX_OUTPUT_TOKENS = 4000


def _describe_response_issue(response: Any) -> str:
    error = getattr(response, "error", None)
    if error and getattr(error, "message", None):
        return f"error del modelo: {error.message}"

    incomplete_details = getattr(response, "incomplete_details", None)
    if incomplete_details and getattr(incomplete_details, "reason", None):
        return f"respuesta incompleta: {incomplete_details.reason}"

    refusals: list[str] = []
    for output in getattr(response, "output", []) or []:
        if getattr(output, "type", None) != "message":
            continue
        for content in getattr(output, "content", []) or []:
            if getattr(content, "type", None) == "refusal":
                refusals.append(getattr(content, "refusal", "refusal sin detalle"))

    if refusals:
        return f"refusal: {' | '.join(refusals[:2])}"

    return "respuesta vacia o sin contenido estructurado"


class QueryInterpretation(BaseModel):
    semantic_query: str
    intent: str = "provider_search"
    categories: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    country: str | None = None
    city: str | None = None
    must_terms: list[str] = Field(default_factory=list)
    should_terms: list[str] = Field(default_factory=list)
    strict_filters: bool = False


class AnalysisPayload(BaseModel):
    summary: str
    recommendations: list[SearchRecommendation] = Field(default_factory=list)


class FollowupPayload(BaseModel):
    answer: str
    referenced_results: list[str] = Field(default_factory=list)
    warning: str | None = None


class WebImportDraftPayload(BaseModel):
    name: str = ""
    description: str = ""
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    city: str | None = None
    country: str | None = None
    category_names: list[str] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _clean_string_list(values: list[str], limit: int) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = _normalize_text(normalized)
        if not normalized or not key or key in seen:
            continue
        cleaned.append(normalized)
        seen.add(key)
        if len(cleaned) >= limit:
            break
    return cleaned


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip()


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _normalize_text(value)).strip("-")


def _tokenize(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", _normalize_text(value)) if len(token) >= 2]


async def _fetch_table_columns(conn: Any, table_name: str, schema: str = "public") -> set[str]:
    result = await conn.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table_name
        """),
        {"schema": schema, "table_name": table_name},
    )
    return {row[0] for row in result.fetchall()}


async def _table_exists(conn: Any, table_name: str, schema: str = "public") -> bool:
    result = await conn.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema
                  AND table_name = :table_name
            )
        """),
        {"schema": schema, "table_name": table_name},
    )
    return bool(result.scalar())


def _extract_result_names(session_payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in (session_payload.get("directory_results") or []) + (session_payload.get("web_results") or []):
        name = (item.get("name") or item.get("title") or "").strip()
        if name:
            names.append(name)
    return names


def _sanitize_followup_references(session_payload: dict[str, Any], references: list[str]) -> list[str]:
    allowed_names = _extract_result_names(session_payload)
    normalized_map = {_normalize_text(name): name for name in allowed_names}
    cleaned: list[str] = []
    seen: set[str] = set()

    for reference in references:
        normalized_reference = _normalize_text(reference)
        matched_name = normalized_map.get(normalized_reference)
        if matched_name is None:
            matched_name = next(
                (
                    name
                    for name in allowed_names
                    if _normalize_text(name) in normalized_reference
                    or normalized_reference in _normalize_text(name)
                ),
                None,
            )
        if not matched_name:
            continue

        key = _normalize_text(matched_name)
        if key in seen:
            continue
        cleaned.append(matched_name)
        seen.add(key)
        if len(cleaned) >= 4:
            break

    return cleaned


def _looks_complex_query(query: str) -> bool:
    lowered = _normalize_text(query)
    tokens = _tokenize(query)
    return len(tokens) >= 5 or any(term in lowered for term in (" con ", " para ", " en ", " que ", " y "))


def _keyword_matches(normalized_text: str, keywords: tuple[str, ...]) -> bool:
    return any(_normalize_text(keyword) in normalized_text for keyword in keywords)


def _extract_country(text_query: str) -> str | None:
    normalized = _normalize_text(text_query)
    for country in COUNTRY_ALIASES:
        if country in normalized:
            return COUNTRY_ALIASES[country]
    return None


COUNTRY_ALIASES: dict[str, str] = {
    "argentina": "Argentina",
    "colombia": "Colombia",
    "mexico": "Mexico",
    "chile": "Chile",
    "peru": "Peru",
    "uruguay": "Uruguay",
    "brasil": "Brasil",
    "ecuador": "Ecuador",
    "panama": "Panama",
}


def _canonicalize_country(value: str | None) -> str | None:
    if not value:
        return None
    normalized = _normalize_text(value)
    return COUNTRY_ALIASES.get(normalized, value.strip())


def _canonicalize_interpretation(interpretation: QueryInterpretation) -> QueryInterpretation:
    interpretation.country = _canonicalize_country(interpretation.country)
    if interpretation.city:
        interpretation.city = interpretation.city.strip()
    interpretation.semantic_query = interpretation.semantic_query.strip() or interpretation.semantic_query
    interpretation.intent = interpretation.intent.strip() or "provider_search"
    interpretation.categories = _clean_string_list(interpretation.categories, 3)
    interpretation.technologies = _clean_string_list(interpretation.technologies, 6)
    interpretation.specialties = _clean_string_list(interpretation.specialties, 4)
    interpretation.must_terms = _clean_string_list(interpretation.must_terms, 4)
    interpretation.should_terms = _clean_string_list(interpretation.should_terms, 6)
    return interpretation


def _normalize_provider_website(value: str | None) -> str | None:
    normalized_url = _normalize_web_url(value or "")
    if not normalized_url:
        return None

    parsed = urlparse(normalized_url)
    hostname = (parsed.netloc or "").casefold().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{hostname}{path}" if path else hostname


def _clean_html_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _extract_html_snippets(html_content: str, pattern: str, limit: int) -> list[str]:
    matches = re.findall(pattern, html_content, flags=re.IGNORECASE | re.DOTALL)
    snippets = [_clean_html_text(match) for match in matches]
    return _clean_string_list(snippets, limit)


def _fallback_interpret_query(query: str) -> QueryInterpretation:
    normalized = _normalize_text(query)
    categories = [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if _keyword_matches(normalized, keywords)
    ][:3]
    technologies = [tag for tag, keywords in TAG_KEYWORDS if _keyword_matches(normalized, keywords)][:6]
    tokens = _tokenize(query)
    must_terms = tokens[:2]
    should_terms = tokens[2:6]
    return QueryInterpretation(
        semantic_query=query.strip(),
        categories=categories,
        technologies=technologies,
        country=_extract_country(query),
        must_terms=must_terms,
        should_terms=should_terms,
        strict_filters=False,
    )


def _build_query_parser_prompts() -> list[str]:
    return [
        """Interpreta la query de un usuario que busca proveedores de servicios B2B tech.

Devuelve solo JSON estructurado con:
- semantic_query
- intent
- categories
- technologies
- specialties
- country
- city
- must_terms
- should_terms
- strict_filters

Reglas:
- No inventes datos no soportados por la query.
- Usa categories solo si se infieren claramente.
- strict_filters solo debe ser true si la query exige un filtro exacto.
- country debe usar nombres canonicos simples, por ejemplo Peru, Mexico, Colombia.
- categories maximo 3.
- technologies maximo 6.
- specialties maximo 4.
- must_terms maximo 4.
- should_terms maximo 6.
- Si un campo no aplica usa null o [].
- Responde en espanol.
""",
        """Devuelve un unico objeto JSON pequeno para interpretar una busqueda de proveedores B2B tech.

Campos requeridos:
semantic_query, intent, categories, technologies, specialties, country, city, must_terms, should_terms, strict_filters

Restricciones duras:
- Sin markdown.
- Sin comentarios.
- Sin texto extra.
- categories <= 3
- technologies <= 6
- specialties <= 4
- must_terms <= 4
- should_terms <= 6
- country canonico: Peru, Mexico, Colombia, Chile, Argentina, Uruguay, Brasil, Ecuador, Panama.
- Usa [] o null cuando no aplique.
""",
    ]


async def _parse_query_with_llm(query: str) -> QueryInterpretation:
    last_error: Exception | None = None

    for attempt, instructions in enumerate(_build_query_parser_prompts(), start=1):
        try:
            response = await client.responses.parse(
                model=settings.openai_model,
                instructions=instructions,
                input=query,
                text_format=QueryInterpretation,
                reasoning={"effort": "low"},
                max_output_tokens=QUERY_PARSER_MAX_OUTPUT_TOKENS,
                text=RESPONSE_TEXT_CONFIG,
            )
        except Exception as exc:
            last_error = exc
            logger.warning("Intento %s del parser LLM fallo: %s", attempt, exc)
            continue

        if response.output_parsed is None:
            issue = _describe_response_issue(response)
            last_error = ValueError(f"El parser de query no devolvio salida estructurada: {issue}")
            logger.warning("Intento %s del parser LLM no devolvio salida estructurada: %s", attempt, issue)
            continue

        return _canonicalize_interpretation(response.output_parsed)

    raise last_error or ValueError("El parser de query no devolvio salida estructurada")


async def interpret_query(query: str) -> tuple[QueryInterpretation, bool, str | None]:
    if not _looks_complex_query(query):
        return _canonicalize_interpretation(_fallback_interpret_query(query)), False, None

    try:
        parsed = await _parse_query_with_llm(query)
        return _canonicalize_interpretation(parsed), True, None
    except Exception as exc:
        logger.warning("Fallo el parser LLM de query: %s", exc)
        return (
            _canonicalize_interpretation(_fallback_interpret_query(query)),
            False,
            "Se uso interpretacion heuristica por fallback.",
        )


async def ensure_search_schema() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        provider_columns = await _fetch_table_columns(conn, "providers")
        provider_column_ddls = {
            "search_document": "ALTER TABLE providers ADD COLUMN search_document TEXT",
            "search_profile": "ALTER TABLE providers ADD COLUMN search_profile JSONB DEFAULT '{}'::jsonb",
            "search_embedding": "ALTER TABLE providers ADD COLUMN search_embedding VECTOR(1536)",
            "search_indexed_at": "ALTER TABLE providers ADD COLUMN search_indexed_at TIMESTAMPTZ",
        }
        for column_name, ddl in provider_column_ddls.items():
            if column_name not in provider_columns:
                await conn.execute(text(ddl))

        if not await _table_exists(conn, "search_sessions"):
            await conn.execute(text("""
                CREATE TABLE search_sessions (
                  id UUID PRIMARY KEY,
                  query TEXT NOT NULL,
                  interpreted_query TEXT NOT NULL,
                  applied_filters JSONB NOT NULL DEFAULT '{}'::jsonb,
                  directory_results JSONB NOT NULL DEFAULT '[]'::jsonb,
                  web_results JSONB NOT NULL DEFAULT '[]'::jsonb,
                  analysis JSONB,
                  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """))

        if not await _table_exists(conn, "search_session_messages"):
            await conn.execute(text("""
                CREATE TABLE search_session_messages (
                  id UUID PRIMARY KEY,
                  session_id UUID NOT NULL REFERENCES search_sessions(id) ON DELETE CASCADE,
                  role TEXT NOT NULL,
                  message TEXT NOT NULL,
                  response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """))

        if "search_indexed_at" in provider_columns or "search_indexed_at" in provider_column_ddls:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_providers_search_indexed_at ON providers(search_indexed_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_search_sessions_created_at ON search_sessions(created_at DESC)"))


async def _fetch_provider_index_data(db: AsyncSession, provider_id: str) -> dict[str, Any] | None:
    query = text("""
        SELECT
          p.id,
          p.name,
          p.description,
          p.city,
          p.country,
          COALESCE(
            json_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),
            '[]'::json
          ) AS categories,
          COALESCE(
            json_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL),
            '[]'::json
          ) AS tags
        FROM providers p
        LEFT JOIN provider_categories pc ON pc.provider_id = p.id
        LEFT JOIN categories c ON c.id = pc.category_id
        LEFT JOIN provider_tags pt ON pt.provider_id = p.id
        LEFT JOIN tags t ON t.id = pt.tag_id
        WHERE p.id = :provider_id AND p.deleted_at IS NULL
        GROUP BY p.id
    """)
    result = await db.execute(query, {"provider_id": provider_id})
    row = result.mappings().first()
    return dict(row) if row else None


async def _load_cached_structured_data(db: AsyncSession, provider_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    query = text("""
        SELECT operation, result
        FROM ai_cache
        WHERE provider_id = :provider_id
          AND operation IN ('categorize', 'extract')
          AND expires_at > now()
        ORDER BY created_at DESC
    """)
    rows = (await db.execute(query, {"provider_id": provider_id})).mappings().all()
    categorize: dict[str, Any] = {}
    extract: dict[str, Any] = {}
    for row in rows:
        payload = row["result"] if isinstance(row["result"], dict) else json.loads(row["result"])
        if row["operation"] == "categorize" and not categorize:
            categorize = payload
        if row["operation"] == "extract" and not extract:
            extract = payload
    return categorize, extract


def _build_search_profile(provider: dict[str, Any], categorize: dict[str, Any], extract: dict[str, Any]) -> dict[str, Any]:
    categories = provider.get("categories") or []
    tags = provider.get("tags") or []
    ai_categories = [item["name"] for item in categorize.get("categories", []) if item.get("name")]
    ai_tags = categorize.get("tags", [])
    profile = {
        "categories": sorted({*categories, *ai_categories}),
        "tags": sorted({*tags, *ai_tags}),
        "services": extract.get("services", []),
        "technologies": extract.get("technologies", []),
        "specialties": extract.get("specialties", []),
        "city": provider.get("city"),
        "country": provider.get("country"),
    }
    return profile


def _build_search_document(provider: dict[str, Any], profile: dict[str, Any]) -> str:
    sections = [
        provider.get("name") or "",
        provider.get("description") or "",
        f"Categorias: {', '.join(profile['categories'])}" if profile["categories"] else "",
        f"Tags: {', '.join(profile['tags'])}" if profile["tags"] else "",
        f"Servicios: {', '.join(profile['services'])}" if profile["services"] else "",
        f"Tecnologias: {', '.join(profile['technologies'])}" if profile["technologies"] else "",
        f"Especialidades: {', '.join(profile['specialties'])}" if profile["specialties"] else "",
        f"Ubicacion: {', '.join([value for value in (provider.get('city'), provider.get('country')) if value])}",
    ]
    return ". ".join(section for section in sections if section).strip()


async def refresh_provider_search_index(db: AsyncSession, provider_id: str) -> None:
    provider = await _fetch_provider_index_data(db, provider_id)
    if not provider:
        return

    categorize, extract = await _load_cached_structured_data(db, provider_id)
    profile = _build_search_profile(provider, categorize, extract)
    document = _build_search_document(provider, profile)
    embedding = await generate_embedding(db, provider_id, document)

    await db.execute(
        text("""
            UPDATE providers
            SET search_document = :document,
                search_profile = CAST(:profile AS JSONB),
                search_embedding = :embedding,
                search_indexed_at = now()
            WHERE id = :provider_id
        """),
        {
            "document": document,
            "profile": json.dumps(profile),
            "embedding": str(embedding),
            "provider_id": provider_id,
        },
    )
    await db.commit()


async def refresh_provider_search_index_background(provider_id: str) -> None:
    try:
        async with async_session() as db:
            await refresh_provider_search_index(db, provider_id)
    except Exception as exc:
        logger.error("No se pudo refrescar search index para provider %s: %s", provider_id, exc)


async def _fetch_directory_rows(
    db: AsyncSession,
    limit: int,
    category_id: str | None,
    country: str | None,
) -> list[dict[str, Any]]:
    filters = ["p.deleted_at IS NULL"]
    params: dict[str, Any] = {"limit": max(limit * 6, 40)}
    if category_id:
        filters.append(
            "p.id IN (SELECT provider_id FROM provider_categories WHERE category_id = :category_id)"
        )
        params["category_id"] = category_id
    if country:
        filters.append("p.country ILIKE :country")
        params["country"] = f"%{country}%"
    query = text(f"""
        SELECT
          p.id,
          p.name,
          p.description,
          p.city,
          p.country,
          p.search_document,
          p.search_profile,
          p.search_indexed_at,
          COALESCE(
            json_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),
            '[]'::json
          ) AS categories,
          COALESCE(
            json_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL),
            '[]'::json
          ) AS tags
        FROM providers p
        LEFT JOIN provider_categories pc ON pc.provider_id = p.id
        LEFT JOIN categories c ON c.id = pc.category_id
        LEFT JOIN provider_tags pt ON pt.provider_id = p.id
        LEFT JOIN tags t ON t.id = pt.tag_id
        WHERE {" AND ".join(filters)}
        GROUP BY p.id
        ORDER BY p.updated_at DESC
        LIMIT :limit
    """)
    result = await db.execute(query, params)
    return [dict(row) for row in result.mappings().all()]


async def _fetch_semantic_scores(
    db: AsyncSession,
    query_text: str,
    limit: int,
    category_id: str | None,
    country: str | None,
) -> dict[str, float]:
    try:
        embedding_response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=query_text,
        )
        query_embedding = embedding_response.data[0].embedding
    except Exception as exc:
        logger.warning("No se pudo generar embedding de query: %s", exc)
        return {}

    filters = [
        "p.deleted_at IS NULL",
        "COALESCE(p.search_embedding, p.embedding) IS NOT NULL",
    ]
    params: dict[str, Any] = {"embedding": str(query_embedding), "limit": max(limit * 4, 20)}
    if category_id:
        filters.append(
            "p.id IN (SELECT provider_id FROM provider_categories WHERE category_id = :category_id)"
        )
        params["category_id"] = category_id
    if country:
        filters.append("p.country ILIKE :country")
        params["country"] = f"%{country}%"

    query = text(f"""
        SELECT
          p.id,
          GREATEST(0, 1 - (COALESCE(p.search_embedding, p.embedding) <=> :embedding)) AS similarity
        FROM providers p
        WHERE {" AND ".join(filters)}
        ORDER BY COALESCE(p.search_embedding, p.embedding) <=> :embedding
        LIMIT :limit
    """)
    rows = (await db.execute(query, params)).mappings().all()
    return {str(row["id"]): round(float(row["similarity"]), 4) for row in rows}


def _profile_from_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_profile = row.get("search_profile")
    if isinstance(raw_profile, dict):
        return raw_profile
    if isinstance(raw_profile, str):
        try:
            return json.loads(raw_profile)
        except json.JSONDecodeError:
            pass
    return {
        "categories": row.get("categories") or [],
        "tags": row.get("tags") or [],
        "services": [],
        "technologies": [],
        "specialties": [],
        "city": row.get("city"),
        "country": row.get("country"),
    }


def _document_from_row(row: dict[str, Any]) -> str:
    if row.get("search_document"):
        return row["search_document"]
    profile = _profile_from_row(row)
    return _build_search_document(row, profile)


def _lexical_score(query: str, row: dict[str, Any], interpretation: QueryInterpretation) -> float:
    document = _normalize_text(_document_from_row(row))
    if not document:
        return 0.0

    query_phrase = _normalize_text(query)
    if query_phrase and query_phrase in document:
        return 1.0

    terms = interpretation.must_terms + interpretation.should_terms
    if not terms:
        terms = _tokenize(query)
    if not terms:
        return 0.0

    matched = sum(1 for term in dict.fromkeys(terms) if _normalize_text(term) in document)
    return round(min(1.0, matched / max(1, len(dict.fromkeys(terms)))), 4)


def _metadata_score(row: dict[str, Any], interpretation: QueryInterpretation) -> float:
    profile = _profile_from_row(row)
    score = 0.0

    normalized_categories = {_normalize_text(value) for value in profile.get("categories", [])}
    normalized_tags = {_normalize_text(value) for value in profile.get("tags", [])}
    normalized_tech = {_normalize_text(value) for value in profile.get("technologies", [])}
    normalized_specs = {_normalize_text(value) for value in profile.get("specialties", [])}

    if interpretation.categories:
        overlap = normalized_categories.intersection({_normalize_text(value) for value in interpretation.categories})
        score += 0.35 if overlap else 0.0
    if interpretation.technologies:
        overlap = (normalized_tags | normalized_tech).intersection(
            {_normalize_text(value) for value in interpretation.technologies}
        )
        score += min(0.35, 0.12 * len(overlap))
    if interpretation.specialties:
        overlap = normalized_specs.intersection({_normalize_text(value) for value in interpretation.specialties})
        score += min(0.2, 0.1 * len(overlap))
    if interpretation.country and row.get("country") and _normalize_text(interpretation.country) == _normalize_text(row["country"]):
        score += 0.1
    if interpretation.city and row.get("city") and _normalize_text(interpretation.city) == _normalize_text(row["city"]):
        score += 0.1
    return round(min(score, 1.0), 4)


def _build_match_reasons(
    row: dict[str, Any],
    interpretation: QueryInterpretation,
    semantic_score: float,
    lexical_score_value: float,
    metadata_score_value: float,
) -> list[str]:
    reasons: list[str] = []
    profile = _profile_from_row(row)

    if semantic_score >= 0.45:
        reasons.append("su propuesta se parece mucho a lo que estas buscando")
    if lexical_score_value >= 0.35:
        reasons.append("describe servicios con palabras muy cercanas a tu busqueda")
    if interpretation.categories:
        overlap = set(profile.get("categories", [])).intersection(set(interpretation.categories))
        if overlap:
            reasons.append(f"trabaja en la categoria {', '.join(sorted(overlap)[:2])}")
    if interpretation.technologies:
        overlap = (
            set(profile.get("tags", []))
            | set(profile.get("technologies", []))
        ).intersection(set(interpretation.technologies))
        if overlap:
            reasons.append(f"menciona tecnologias relevantes como {', '.join(sorted(overlap)[:2])}")
    if interpretation.country and row.get("country") and _normalize_text(interpretation.country) == _normalize_text(row["country"]):
        reasons.append(f"opera en {row['country']}")
    if metadata_score_value >= 0.25 and not reasons:
        reasons.append("muestra senales utiles dentro de su perfil y especialidades")
    return reasons[:3]


class _WebProviderResult(BaseModel):
    title: str
    snippet: str
    url: str
    country: str | None = None
    city: str | None = None
    detected_categories: list[str] = Field(default_factory=list)
    detected_tags: list[str] = Field(default_factory=list)
    relevance_reason: str = ""


class _WebProviderPayload(BaseModel):
    results: list[_WebProviderResult] = Field(default_factory=list)


def _normalize_web_url(url: str) -> str | None:
    raw = url.strip()
    if not raw:
        return None

    candidate = raw if raw.startswith(("http://", "https://")) else f"https://{raw}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


async def _verify_web_result_url(http_client: httpx.AsyncClient, url: str) -> str | None:
    normalized_url = _normalize_web_url(url)
    if not normalized_url:
        return None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        response = await http_client.head(normalized_url, headers=headers)
        if response.status_code == 405:
            response = await http_client.get(normalized_url, headers=headers)
    except Exception:
        try:
            response = await http_client.get(normalized_url, headers=headers)
        except Exception:
            return None

    if response.status_code < 400 or response.status_code in {401, 403}:
        return str(response.url)
    return None


async def _search_web_with_openai(
    query: str,
    interpretation: QueryInterpretation,
    limit: int,
) -> list[WebSearchResult]:
    candidate_limit = max(limit * WEB_SEARCH_CANDIDATE_MULTIPLIER, 6)
    country_hint = interpretation.country or "Latinoamerica"
    categories_hint = ", ".join(interpretation.categories[:3]) if interpretation.categories else "tecnologia"
    techs_hint = ", ".join(interpretation.technologies[:4]) if interpretation.technologies else ""

    search_prompt = (
        f"Busca empresas o proveedores reales de servicios B2B de tecnologia que ofrezcan: "
        f"{interpretation.semantic_query or query}.\n"
        f"Region preferida: {country_hint}.\n"
    )
    if techs_hint:
        search_prompt += f"Tecnologias relevantes: {techs_hint}.\n"

    instructions = (
        "Eres un investigador de proveedores B2B tech. "
        "Usa la herramienta de busqueda web para encontrar empresas REALES que coincidan con la necesidad del usuario. "
        "Devuelve solo empresas/proveedores verificables con sitio web real. "
        "NO inventes empresas ni URLs. Solo incluye resultados que hayas encontrado en la web. "
        "Prioriza el sitio oficial del proveedor o una landing propia y canonica del proveedor. "
        "Evita URLs rotas, rutas profundas dudosas, paginas de error o dominios que no parezcan oficiales. "
        f"Devuelve maximo {candidate_limit} candidatos en JSON estructurado.\n"
        "Para cada resultado incluye:\n"
        "- title: nombre de la empresa\n"
        "- snippet: descripcion breve de por que es relevante\n"
        "- url: sitio web real de la empresa\n"
        "- country: pais donde opera (si se identifica)\n"
        "- city: ciudad (si se identifica)\n"
        f"- detected_categories: categorias aplicables de [{categories_hint}]\n"
        "- detected_tags: tecnologias o tags detectados\n"
        "- relevance_reason: razon concisa de por que es relevante para la busqueda\n"
    )

    response = await client.responses.parse(
        model=settings.openai_model,
        instructions=instructions,
        input=search_prompt,
        tools=[{"type": "web_search"}],
        text_format=_WebProviderPayload,
        max_output_tokens=WEB_SEARCH_MAX_OUTPUT_TOKENS,
        text=RESPONSE_TEXT_CONFIG,
    )

    parsed = response.output_parsed
    if parsed is None:
        logger.warning("web_search de OpenAI no devolvio salida estructurada: %s", _describe_response_issue(response))
        return []

    results: list[WebSearchResult] = []
    seen_urls: set[str] = set()
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as http_client:
        for item in parsed.results[:candidate_limit]:
            verified_url = await _verify_web_result_url(http_client, item.url)
            if not verified_url:
                logger.info("Resultado web descartado por URL no verificable: %s", item.url)
                continue
            if verified_url in seen_urls:
                continue

            results.append(
                WebSearchResult(
                    title=item.title,
                    snippet=item.snippet,
                    url=verified_url,
                    source="openai-web-search",
                    country=item.country,
                    city=item.city,
                    detected_categories=item.detected_categories,
                    detected_tags=item.detected_tags,
                    match_reasons=(
                        [item.relevance_reason, "url verificada"]
                        if item.relevance_reason
                        else ["resultado web verificado", "url verificada"]
                    ),
                )
            )
            seen_urls.add(verified_url)
            if len(results) >= limit:
                break
    return results


async def _search_web_results(
    query: str,
    interpretation: QueryInterpretation,
    limit: int,
) -> tuple[list[WebSearchResult], str | None]:
    provider = settings.web_search_provider.casefold().strip()
    if provider in {"", "none", "disabled"}:
        return [], "Busqueda web desactivada por configuracion."

    if provider == "openai":
        try:
            results = await _search_web_with_openai(query, interpretation, limit)
            return results, None
        except Exception as exc:
            logger.warning("Fallo la busqueda web con OpenAI: %s", exc)
            return [], "Fallo la busqueda web con OpenAI; se mantuvo solo el directorio."

    endpoint = settings.web_search_endpoint
    api_key = settings.web_search_api_key
    if not endpoint or not api_key:
        return [], "Busqueda web no configurada; se omitieron resultados externos."

    try:
        async with httpx.AsyncClient(timeout=10) as http_client:
            response = await http_client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"query": interpretation.semantic_query or query, "limit": limit},
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Fallo la busqueda web externa: %s", exc)
        return [], "Fallo la busqueda web externa; se mantuvo solo el directorio."

    payload = response.json()
    items = payload.get("results", [])
    results = [
        WebSearchResult(
            title=item.get("title", "Resultado externo"),
            snippet=item.get("snippet", ""),
            url=item.get("url", ""),
            source=item.get("source", provider),
            city=item.get("city"),
            country=item.get("country"),
            detected_categories=item.get("detected_categories", []),
            detected_tags=item.get("detected_tags", []),
            match_reasons=item.get("match_reasons", ["resultado externo recuperado"]),
        )
        for item in items[:limit]
    ]
    return results, None


def _default_analysis(
    query: str,
    interpretation: QueryInterpretation,
    directory_results: list[DirectorySearchResult],
    web_results: list[WebSearchResult],
) -> SearchAnalysis:
    top_names = ", ".join(result.name for result in directory_results[:3]) or "sin coincidencias claras"
    if directory_results:
        summary = (
            f"Para la busqueda '{query}', el directorio encontro {len(directory_results)} opcion(es). "
            f"Las senales mas fuertes favorecen a {top_names}. "
            f"Revisa primero los resultados mejor alineados y usa el resto como alternativas comparables."
        )
    else:
        summary = (
            f"Para la busqueda '{query}', no encontramos coincidencias claras dentro del directorio. "
            f"Conviene reformular la necesidad, ajustar filtros o ampliar con referencias externas."
        )

    labels = ["Mejor alineado", "Alternativa cercana", "Vale revisar"]
    recommendations = [
        SearchRecommendation(
            label=labels[index - 1] if index <= len(labels) else "Vale revisar",
            target_type="directory",
            target_id=str(result.id),
            reason=result.match_reasons[0] if result.match_reasons else "aparece como una opcion razonable para continuar la evaluacion",
        )
        for index, result in enumerate(directory_results[:3], start=1)
    ]
    return SearchAnalysis(summary=summary, recommendations=recommendations)


async def _llm_analysis(
    query: str,
    interpretation: QueryInterpretation,
    directory_results: list[DirectorySearchResult],
    web_results: list[WebSearchResult],
) -> SearchAnalysis:
    payload = {
        "query": query,
        "interpreted_query": interpretation.semantic_query,
        "directory_results": [result.model_dump(mode="json") for result in directory_results[:6]],
        "web_results": [result.model_dump(mode="json") for result in web_results[:4]],
    }
    response = await client.responses.parse(
        model=settings.openai_model,
        instructions=(
            "Eres un analista de proveedores B2B para usuarios no tecnicos. "
            "Resume y recomienda solo con la evidencia entregada. "
            "No inventes datos ni agregues fuentes nuevas. "
            "Escribe en espanol claro, orientado a decision, y evita jerga tecnica del motor de busqueda. "
            "El summary debe explicar quienes parecen mas alineados, por que y que limitaciones tiene la evidencia. "
            "Las recomendaciones deben usar labels semanticos y cortos. "
            "Usa solo estos labels cuando apliquen: 'Mejor alineado', 'Alternativa cercana', 'Vale revisar'."
        ),
        input=json.dumps(payload, ensure_ascii=False),
        text_format=AnalysisPayload,
        reasoning={"effort": "low"},
        max_output_tokens=500,
        text=RESPONSE_TEXT_CONFIG,
    )
    if response.output_parsed is None:
        raise ValueError("Analisis sin salida estructurada")
    parsed = response.output_parsed
    return SearchAnalysis(summary=parsed.summary, recommendations=parsed.recommendations)


async def generate_search_analysis(
    query: str,
    interpretation: QueryInterpretation,
    directory_results: list[DirectorySearchResult],
    web_results: list[WebSearchResult],
) -> SearchAnalysis:
    if not directory_results and not web_results:
        return SearchAnalysis(summary="No se encontro evidencia suficiente para generar recomendaciones.", recommendations=[])

    try:
        return await _llm_analysis(query, interpretation, directory_results, web_results)
    except Exception as exc:
        logger.warning("Fallo el analisis LLM de busqueda: %s", exc)
        return _default_analysis(query, interpretation, directory_results, web_results)


async def _store_search_session(
    db: AsyncSession,
    query: str,
    interpretation: QueryInterpretation,
    directory_results: list[DirectorySearchResult],
    web_results: list[WebSearchResult],
    analysis: SearchAnalysis | None,
    meta: SearchMeta,
) -> uuid.UUID:
    session_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO search_sessions (
              id, query, interpreted_query, applied_filters,
              directory_results, web_results, analysis, meta
            ) VALUES (
              :id, :query, :interpreted_query, CAST(:applied_filters AS JSONB),
              CAST(:directory_results AS JSONB), CAST(:web_results AS JSONB),
              CAST(:analysis AS JSONB), CAST(:meta AS JSONB)
            )
        """),
        {
            "id": str(session_id),
            "query": query,
            "interpreted_query": interpretation.semantic_query,
            "applied_filters": json.dumps(
                AppliedFilters(
                    country=interpretation.country,
                    city=interpretation.city,
                    categories=interpretation.categories,
                    technologies=interpretation.technologies,
                    specialties=interpretation.specialties,
                ).model_dump()
            ),
            "directory_results": json.dumps([result.model_dump(mode="json") for result in directory_results]),
            "web_results": json.dumps([result.model_dump(mode="json") for result in web_results]),
            "analysis": json.dumps(analysis.model_dump(mode="json") if analysis else None),
            "meta": json.dumps(meta.model_dump()),
        },
    )
    await db.commit()
    return session_id


def _deserialize_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _find_session_web_result(session_payload: dict[str, Any], url: str) -> dict[str, Any] | None:
    normalized_target = _normalize_web_url(url)
    if not normalized_target:
        return None

    web_results = _deserialize_json_field(session_payload.get("web_results")) or []
    for result in web_results:
        candidate_url = _normalize_web_url((result or {}).get("url", ""))
        if candidate_url == normalized_target:
            return result
    return None


async def _fetch_verified_web_page_snapshot(url: str) -> dict[str, Any]:
    normalized_url = _normalize_web_url(url)
    if not normalized_url:
        raise ValueError("La URL del resultado web no es valida")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as http_client:
        response = await http_client.get(normalized_url, headers=headers)

    if response.status_code >= 400:
        raise ValueError(f"No se pudo leer la pagina fuente (HTTP {response.status_code})")

    html_content = response.text[:200_000]
    cleaned_page_text = _clean_html_text(
        re.sub(r"<(script|style)[^>]*>.*?</\\1>", " ", html_content, flags=re.IGNORECASE | re.DOTALL)
    )
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, flags=re.IGNORECASE | re.DOTALL)
    meta_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html_content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    title = _clean_html_text(title_match.group(1)) if title_match else ""
    meta_description = _clean_html_text(meta_match.group(1)) if meta_match else ""
    headings = _extract_html_snippets(html_content, r"<h[1-3][^>]*>(.*?)</h[1-3]>", 8)
    paragraphs = _extract_html_snippets(html_content, r"<p[^>]*>(.*?)</p>", 8)
    emails = _clean_string_list(
        re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", html_content, flags=re.IGNORECASE),
        5,
    )
    phones = _clean_string_list(
        re.findall(r"(?:\+\d[\d\s().-]{7,}\d)", cleaned_page_text),
        5,
    )

    if not any([title, meta_description, headings, paragraphs]):
        raise ValueError("La pagina fuente no ofrece contenido util para completar el proveedor")

    return {
        "final_url": str(response.url),
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "paragraphs": paragraphs,
        "emails": emails,
        "phones": phones,
    }


async def _load_category_catalog(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.name.asc()))
    return result.scalars().all()


def _map_category_names_to_ids(
    category_names: list[str],
    category_catalog: list[Category],
) -> tuple[list[uuid.UUID], list[str]]:
    by_key: dict[str, Category] = {}
    for category in category_catalog:
        by_key[_normalize_text(category.name)] = category
        by_key[_normalize_text(category.slug)] = category

    category_ids: list[uuid.UUID] = []
    warnings: list[str] = []
    seen: set[uuid.UUID] = set()
    for name in category_names:
        matched = by_key.get(_normalize_text(name))
        if not matched:
            warnings.append(f"No se pudo mapear la categoria sugerida '{name}' al catalogo actual.")
            continue
        if matched.id in seen:
            continue
        category_ids.append(matched.id)
        seen.add(matched.id)
    return category_ids, warnings


async def _find_duplicate_provider(
    db: AsyncSession,
    draft: WebProviderImportDraft,
) -> DuplicateProviderSummary | None:
    providers = (
        await db.execute(select(Provider).where(Provider.deleted_at.is_(None)))
    ).scalars().all()

    website_key = _normalize_provider_website(draft.website)
    if website_key:
        for provider in providers:
            if _normalize_provider_website(provider.website) == website_key:
                return DuplicateProviderSummary(
                    id=provider.id,
                    name=provider.name,
                    website=provider.website,
                )

    normalized_name = _normalize_text(draft.name)
    normalized_country = _normalize_text(draft.country or "")
    if normalized_name and normalized_country:
        for provider in providers:
            if (
                _normalize_text(provider.name) == normalized_name
                and _normalize_text(provider.country or "") == normalized_country
            ):
                return DuplicateProviderSummary(
                    id=provider.id,
                    name=provider.name,
                    website=provider.website,
                )

    return None


async def _generate_web_import_draft(
    web_result: dict[str, Any],
    page_snapshot: dict[str, Any],
    category_catalog: list[Category],
    regenerate: bool,
) -> tuple[WebProviderImportDraft, list[str], str]:
    category_names = [category.name for category in category_catalog]
    prompt = (
        "Completa un borrador de proveedor B2B tech usando SOLO evidencia de la pagina web verificada. "
        "No inventes datos. Si un campo no esta soportado por la evidencia, dejalo vacio o null. "
        "La descripcion debe ser breve, clara y util para registrar el proveedor en un directorio. "
        "Usa category_names solo con nombres exactos de este catalogo: "
        f"{', '.join(category_names)}. "
        "No generes mas de 6 tags y solo si hay evidencia suficiente. "
        "No copies bloques grandes literales del HTML."
    )
    if regenerate:
        prompt += " Genera una nueva redaccion del borrador manteniendo fidelidad a la evidencia."

    response = await client.responses.parse(
        model=settings.openai_model,
        instructions=prompt,
        input=json.dumps(
            {
                "web_result": web_result,
                "page_snapshot": page_snapshot,
                "allowed_categories": category_names,
                "regenerate": regenerate,
            },
            ensure_ascii=False,
        ),
        text_format=WebImportDraftPayload,
        reasoning={"effort": "low"},
        max_output_tokens=WEB_IMPORT_MAX_OUTPUT_TOKENS,
        text=RESPONSE_TEXT_CONFIG,
    )
    if response.output_parsed is None:
        raise ValueError(
            f"No se pudo generar el borrador estructurado del proveedor: {_describe_response_issue(response)}"
        )

    payload = response.output_parsed
    mapped_category_ids, mapping_warnings = _map_category_names_to_ids(payload.category_names, category_catalog)
    warnings = _clean_string_list(payload.warnings + mapping_warnings, 8)
    draft = WebProviderImportDraft(
        name=payload.name.strip() or web_result.get("title", "").strip(),
        description=payload.description.strip(),
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        website=_normalize_web_url(payload.website or page_snapshot["final_url"]),
        city=payload.city.strip() if payload.city else None,
        country=_canonicalize_country(payload.country) if payload.country else None,
        category_ids=mapped_category_ids,
        tag_names=_clean_string_list(payload.tag_names, 6),
    )
    provenance = (
        f"Borrador generado desde la URL verificada {page_snapshot['final_url']} usando contenido HTML fetchado del sitio."
    )
    return draft, warnings, provenance


async def generate_web_import_preview(
    db: AsyncSession,
    session_id: str,
    url: str,
    regenerate: bool = False,
) -> WebProviderImportPreviewResponse:
    session_payload = await _fetch_session_payload(db, session_id)
    if not session_payload:
        raise ValueError("La sesion de busqueda no existe")

    web_result = _find_session_web_result(session_payload, url)
    if not web_result:
        raise ValueError("La URL seleccionada no pertenece a los resultados web de esta sesion")

    source_url = _normalize_web_url(web_result.get("url", "") or url) or url
    try:
        page_snapshot = await _fetch_verified_web_page_snapshot(source_url)
    except Exception as exc:
        return WebProviderImportPreviewResponse(
            status="error",
            draft=None,
            source_url=source_url,
            warnings=[str(exc)],
            duplicate_provider=None,
            provenance="No se pudo verificar ni leer la pagina fuente seleccionada.",
        )

    category_catalog = await _load_category_catalog(db)
    draft, warnings, provenance = await _generate_web_import_draft(
        web_result,
        page_snapshot,
        category_catalog,
        regenerate=regenerate,
    )
    duplicate = await _find_duplicate_provider(db, draft)
    if duplicate:
        return WebProviderImportPreviewResponse(
            status="duplicate",
            draft=None,
            source_url=page_snapshot["final_url"],
            warnings=["Ya existe un proveedor equivalente en el directorio."],
            duplicate_provider=duplicate,
            provenance=provenance,
        )

    return WebProviderImportPreviewResponse(
        status="ready",
        draft=draft,
        source_url=page_snapshot["final_url"],
        warnings=warnings,
        duplicate_provider=None,
        provenance=provenance,
    )


async def run_search(
    db: AsyncSession,
    query: str,
    limit: int,
    category_id: str | None = None,
    country: str | None = None,
    include_web: bool = False,
    analyze: bool = True,
) -> SearchResponse:
    interpretation, used_llm_parser, warning = await interpret_query(query)
    if country and not interpretation.country:
        interpretation.country = _canonicalize_country(country)

    semantic_scores = await _fetch_semantic_scores(
        db,
        interpretation.semantic_query or query,
        limit=limit,
        category_id=category_id,
        country=country or interpretation.country,
    )
    rows = await _fetch_directory_rows(db, limit, category_id, country or interpretation.country)

    directory_results: list[DirectorySearchResult] = []
    for row in rows:
        row_id = str(row["id"])
        semantic_score = semantic_scores.get(row_id, 0.0)
        lexical_score_value = _lexical_score(query, row, interpretation)
        metadata_score_value = _metadata_score(row, interpretation)
        final_score = round((semantic_score * 0.5) + (lexical_score_value * 0.3) + (metadata_score_value * 0.2), 4)
        if final_score <= 0:
            continue
        directory_results.append(
            DirectorySearchResult(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                city=row["city"],
                country=row["country"],
                score=final_score,
                semantic_score=semantic_score,
                lexical_score=lexical_score_value,
                metadata_score=metadata_score_value,
                match_reasons=_build_match_reasons(
                    row, interpretation, semantic_score, lexical_score_value, metadata_score_value
                ),
            )
        )

    directory_results.sort(key=lambda result: result.score, reverse=True)
    directory_results = directory_results[:limit]

    web_results: list[WebSearchResult] = []
    web_warning: str | None = None
    if include_web:
        web_results, web_warning = await _search_web_results(
            query,
            interpretation,
            min(limit, WEB_SEARCH_FINAL_RESULT_LIMIT),
        )
        warning = warning or web_warning

    analysis = await generate_search_analysis(query, interpretation, directory_results, web_results) if analyze else None
    meta = SearchMeta(
        used_llm_parser=used_llm_parser,
        used_web_search=include_web,
        strategy="hybrid+analysis" if analyze else "hybrid",
        web_provider=settings.web_search_provider if include_web else None,
        warning=warning,
    )
    session_id = await _store_search_session(db, query, interpretation, directory_results, web_results, analysis, meta)
    return SearchResponse(
        query=query,
        interpreted_query=interpretation.semantic_query or query,
        applied_filters=AppliedFilters(
            country=interpretation.country,
            city=interpretation.city,
            categories=interpretation.categories,
            technologies=interpretation.technologies,
            specialties=interpretation.specialties,
        ),
        directory_results=directory_results,
        web_results=web_results,
        analysis=analysis,
        session_id=session_id,
        meta=meta,
    )


async def _fetch_session_payload(db: AsyncSession, session_id: str) -> dict[str, Any] | None:
    query = text("""
        SELECT id, query, interpreted_query, directory_results, web_results, analysis, meta
        FROM search_sessions
        WHERE id = :session_id
    """)
    row = (await db.execute(query, {"session_id": session_id})).mappings().first()
    return dict(row) if row else None


def _default_followup_answer(session_payload: dict[str, Any], message: str) -> SearchFollowupResponse:
    directory_results = session_payload.get("directory_results") or []
    web_results = session_payload.get("web_results") or []
    combined = directory_results + web_results
    normalized = _normalize_text(message)

    if "colombia" in normalized:
        matched = [item.get("name") or item.get("title") for item in combined if _normalize_text(item.get("country") or "") == "colombia"]
        if matched:
            return SearchFollowupResponse(
                answer=f"En esta sesion, los resultados ubicados en Colombia son: {', '.join(matched)}.",
                referenced_results=matched,
            )
    if "tensorflow" in normalized:
        matched = [
            item.get("name") or item.get("title")
            for item in directory_results
            if "tensorflow" in _normalize_text(json.dumps(item, ensure_ascii=False))
        ]
        if matched:
            return SearchFollowupResponse(
                answer=f"Los resultados con evidencia directa sobre TensorFlow en esta sesion son: {', '.join(matched)}.",
                referenced_results=matched,
            )

    top = [item.get("name") or item.get("title") for item in combined[:3]]
    warning = "La respuesta se limito a la evidencia disponible en esta sesion."
    return SearchFollowupResponse(
        answer=(
            f"No tengo evidencia suficiente para responder con precision total. "
            f"Lo mas fuerte en la sesion sigue siendo: {', '.join(top)}."
        ),
        referenced_results=top,
        warning=warning,
    )


async def answer_search_followup(db: AsyncSession, session_id: str, message: str) -> SearchFollowupResponse:
    session_payload = await _fetch_session_payload(db, session_id)
    if not session_payload:
        raise ValueError("La sesion de busqueda no existe")

    directory_results = session_payload["directory_results"] or []
    web_results = session_payload["web_results"] or []
    structured_payload = {
        "query": session_payload["query"],
        "interpreted_query": session_payload["interpreted_query"],
        "directory_results": [
            {
                "name": item.get("name"),
                "description": item.get("description"),
                "city": item.get("city"),
                "country": item.get("country"),
                "match_reasons": item.get("match_reasons", []),
                "score": item.get("score"),
            }
            for item in directory_results[:6]
        ],
        "web_results": [
            {
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "url": item.get("url"),
                "city": item.get("city"),
                "country": item.get("country"),
                "match_reasons": item.get("match_reasons", []),
            }
            for item in web_results[:4]
        ],
        "analysis": session_payload["analysis"],
        "question": message,
    }
    try:
        response = await client.responses.parse(
            model=settings.openai_model,
            instructions=(
                "Eres un analista de proveedores B2B que responde preguntas cortas sobre una sesion de busqueda. "
                "Usa solo la evidencia disponible en la sesion. No inventes datos, no cites campos internos del JSON "
                "y no copies texto crudo como 'match_reasons', 'score', claves o listas serializadas. "
                "Responde en espanol claro y util para decision. "
                "El campo answer debe tener entre 2 y 4 frases, comparando solo los resultados realmente relevantes para la pregunta. "
                "Si mencionas resultados, usa sus nombres visibles tal como aparecen en la sesion. "
                "El campo referenced_results debe incluir solo nombres de proveedores o titulos de resultados presentes en la sesion, "
                "sin descripciones adicionales, maximo 4 elementos. "
                "Si no hay evidencia suficiente para responder bien, dilo con honestidad en answer y resume la limitacion en warning."
            ),
            input=json.dumps(structured_payload, ensure_ascii=False),
            text_format=FollowupPayload,
            reasoning={"effort": "low"},
            max_output_tokens=400,
            text=RESPONSE_TEXT_CONFIG,
        )
        if response.output_parsed is None:
            raise ValueError("Followup sin salida estructurada")
        payload = response.output_parsed
        sanitized_references = _sanitize_followup_references(session_payload, payload.referenced_results)
        result = SearchFollowupResponse(
            answer=payload.answer,
            referenced_results=sanitized_references,
            warning=payload.warning,
        )
    except Exception as exc:
        logger.warning("Fallo el followup LLM: %s", exc)
        result = _default_followup_answer(session_payload, message)

    await db.execute(
        text("""
            INSERT INTO search_session_messages (id, session_id, role, message, response_payload)
            VALUES (:id, :session_id, 'user', :message, CAST(:payload AS JSONB))
        """),
        {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "message": message,
            "payload": json.dumps(result.model_dump()),
        },
    )
    await db.commit()
    return result
