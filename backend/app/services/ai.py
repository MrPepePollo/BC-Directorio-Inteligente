import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Literal, TypeVar

import openai
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.provider import AiCache

settings = get_settings()
client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
logger = logging.getLogger(__name__)
CACHE_TTL = timedelta(days=30)
RESPONSE_TEXT_CONFIG = {"verbosity": "low"}
ModelT = TypeVar("ModelT", bound=BaseModel)

ALLOWED_CATEGORIES = (
    "Desarrollo Web",
    "Desarrollo Movil",
    "Diseno UI/UX",
    "Data Science",
    "Cloud & DevOps",
    "Ciberseguridad",
    "Marketing Digital",
    "Consultoria IT",
    "ERP & CRM",
    "Soporte & Mantenimiento",
)

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Desarrollo Web": (
        "desarrollo web",
        "sitio web",
        "portal web",
        "e-commerce",
        "ecommerce",
        "frontend",
        "backend",
        "full stack",
        "react",
        "vue",
        "angular",
        "wordpress",
        "django",
        "laravel",
        "api",
    ),
    "Desarrollo Movil": (
        "desarrollo movil",
        "mobile app",
        "mobile apps",
        "aplicacion movil",
        "aplicaciones moviles",
        "ios",
        "android",
        "react native",
        "flutter",
        "swift",
        "kotlin",
    ),
    "Diseno UI/UX": (
        "ui/ux",
        "ui ux",
        "ux",
        "user experience",
        "experiencia de usuario",
        "interfaz",
        "figma",
        "prototipo",
        "wireframe",
        "design system",
        "research",
    ),
    "Data Science": (
        "data science",
        "ciencia de datos",
        "analisis de datos",
        "analitica",
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch",
        "modelo predictivo",
        "vision por computador",
        "computer vision",
        "nlp",
        "mapas de calor",
        "imagenes satelitales",
        "geoespacial",
    ),
    "Cloud & DevOps": (
        "cloud",
        "devops",
        "aws",
        "azure",
        "gcp",
        "google cloud",
        "docker",
        "kubernetes",
        "terraform",
        "ci/cd",
        "observabilidad",
        "sre",
        "infraestructura",
    ),
    "Ciberseguridad": (
        "ciberseguridad",
        "cybersecurity",
        "seguridad",
        "pentest",
        "soc",
        "siem",
        "zero trust",
        "iam",
        "iso 27001",
        "vulnerabilidades",
    ),
    "Marketing Digital": (
        "marketing digital",
        "seo",
        "sem",
        "ads",
        "paid media",
        "social media",
        "growth",
        "campanas",
        "campañas",
        "lead generation",
        "contenido",
    ),
    "Consultoria IT": (
        "consultoria",
        "consultoría",
        "consulting",
        "transformacion digital",
        "transformación digital",
        "auditoria tecnologica",
        "auditoría tecnológica",
        "roadmap",
        "arquitectura de software",
        "gobierno de ti",
        "asesoria tecnologica",
        "asesoría tecnológica",
    ),
    "ERP & CRM": (
        "erp",
        "crm",
        "sap",
        "salesforce",
        "hubspot",
        "dynamics",
        "successfactors",
        "bamboohr",
        "nomina",
        "nómina",
        "rrhh",
        "talento humano",
        "reclutamiento",
        "facturacion",
        "facturación",
    ),
    "Soporte & Mantenimiento": (
        "soporte",
        "mantenimiento",
        "help desk",
        "mesa de ayuda",
        "monitoreo",
        "monitorizacion",
        "monitorización",
        "sla",
        "incidentes",
        "continuidad operativa",
    ),
}

TAG_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("inteligencia artificial", (" ia ", " ai ", "machine learning", "deep learning", "tensorflow", "pytorch")),
    ("python", ("python",)),
    ("react", ("react",)),
    ("vue", ("vue",)),
    ("docker", ("docker",)),
    ("kubernetes", ("kubernetes",)),
    ("aws", ("aws", "amazon web services")),
    ("azure", ("azure",)),
    ("gcp", (" gcp ", "google cloud")),
    ("sap", ("sap", "successfactors")),
    ("salesforce", ("salesforce",)),
    ("hubspot", ("hubspot",)),
    ("bamboohr", ("bamboohr",)),
    ("qgis", ("qgis",)),
    ("tensorflow", ("tensorflow",)),
    ("google earth engine", ("google earth engine",)),
    ("geoespacial", ("geoespacial", "imagenes satelitales", "imágenes satelitales", "ortomosaicos")),
    ("drones", ("drone", "drones")),
    ("reclutamiento", ("reclutamiento",)),
    ("nomina", ("nomina", "nómina")),
    ("rrhh", ("rrhh", "talento humano")),
    ("devops", ("devops", "ci/cd", "terraform")),
    ("cloud", ("cloud", "aws", "azure", "gcp")),
    ("ciberseguridad", ("ciberseguridad", "cybersecurity", "pentest", "soc", "siem")),
    ("marketing digital", ("marketing digital", "seo", "sem", "ads")),
]

CATEGORY_DEFAULT_TAGS: dict[str, tuple[str, ...]] = {
    "Desarrollo Web": ("desarrollo web", "frontend", "backend"),
    "Desarrollo Movil": ("desarrollo movil", "apps", "mobile"),
    "Diseno UI/UX": ("ui/ux", "experiencia de usuario", "prototipado"),
    "Data Science": ("analitica", "datos", "machine learning"),
    "Cloud & DevOps": ("cloud", "devops", "automatizacion"),
    "Ciberseguridad": ("ciberseguridad", "riesgo", "cumplimiento"),
    "Marketing Digital": ("marketing digital", "seo", "ads"),
    "Consultoria IT": ("consultoria", "transformacion digital", "arquitectura"),
    "ERP & CRM": ("erp", "crm", "automatizacion"),
    "Soporte & Mantenimiento": ("soporte", "mantenimiento", "operacion"),
}

SPECIALTY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("rrhh", ("rrhh", "talento humano", "reclutamiento", "nómina", "nomina")),
    ("geoespacial", ("geoespacial", "imagenes satelitales", "imágenes satelitales", "ortomosaicos")),
    ("agricultura de precision", ("agricultura de precision", "agricultura de precisión")),
    ("mineria", ("mineria", "minería")),
    ("construccion", ("construccion", "construcción")),
]

SERVICE_BY_CATEGORY: dict[str, str] = {
    "Desarrollo Web": "desarrollo web",
    "Desarrollo Movil": "desarrollo movil",
    "Diseno UI/UX": "diseno ui/ux",
    "Data Science": "analitica de datos",
    "Cloud & DevOps": "cloud y devops",
    "Ciberseguridad": "ciberseguridad",
    "Marketing Digital": "marketing digital",
    "Consultoria IT": "consultoria it",
    "ERP & CRM": "implementacion de erp y crm",
    "Soporte & Mantenimiento": "soporte y mantenimiento",
}

TECHNOLOGY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("python", ("python",)),
    ("react", ("react",)),
    ("vue", ("vue",)),
    ("angular", ("angular",)),
    ("flutter", ("flutter",)),
    ("swift", ("swift",)),
    ("kotlin", ("kotlin",)),
    ("docker", ("docker",)),
    ("kubernetes", ("kubernetes",)),
    ("terraform", ("terraform",)),
    ("aws", ("aws", "amazon web services")),
    ("azure", ("azure",)),
    ("gcp", (" gcp ", "google cloud")),
    ("tensorflow", ("tensorflow",)),
    ("pytorch", ("pytorch",)),
    ("qgis", ("qgis",)),
    ("google earth engine", ("google earth engine",)),
    ("sap", ("sap", "successfactors")),
    ("bamboohr", ("bamboohr",)),
    ("salesforce", ("salesforce",)),
    ("hubspot", ("hubspot",)),
]


class CategorizationCategory(BaseModel):
    name: Literal[
        "Desarrollo Web",
        "Desarrollo Movil",
        "Diseno UI/UX",
        "Data Science",
        "Cloud & DevOps",
        "Ciberseguridad",
        "Marketing Digital",
        "Consultoria IT",
        "ERP & CRM",
        "Soporte & Mantenimiento",
    ]
    confidence: float = Field(ge=0.0, le=1.0)


class CategorizationResult(BaseModel):
    categories: list[CategorizationCategory] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    services: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    suggested_city: str | None = None
    suggested_country: str | None = None


def _hash_input(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^\w\s/&+-]", " ", ascii_text)
    return f" {re.sub(r'\\s+', ' ', ascii_text).strip()} "


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _keyword_score(normalized_text: str, keywords: tuple[str, ...]) -> int:
    score = 0
    for keyword in keywords:
        if _normalize_text(keyword) in normalized_text:
            score += 2 if " " in keyword.strip() else 1
    return score


def _category_confidence(score: int, rank: int) -> float:
    base = min(0.94, 0.56 + (score * 0.09) - (rank * 0.04))
    return round(max(0.45, base), 2)


def _fallback_categorization(description: str) -> dict:
    normalized = _normalize_text(description)
    scored: list[tuple[str, int]] = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = _keyword_score(normalized, keywords)
        if score > 0:
            scored.append((category, score))

    if not scored and any(token in normalized for token in (" software ", " plataforma ", " sistema ", " integracion ", " integración ")):
        scored.append(("Consultoria IT", 1))

    scored.sort(key=lambda item: (-item[1], ALLOWED_CATEGORIES.index(item[0])))
    top_categories = scored[:3] or [("Consultoria IT", 1)]

    categories = [
        {"name": name, "confidence": _category_confidence(score, rank)}
        for rank, (name, score) in enumerate(top_categories)
    ]

    tags: list[str] = []
    for tag, keywords in TAG_KEYWORDS:
        if _keyword_score(normalized, keywords) > 0:
            tags.append(tag)

    for name, _score in top_categories:
        tags.extend(CATEGORY_DEFAULT_TAGS.get(name, ()))

    return {
        "categories": categories,
        "tags": _dedupe_keep_order([tag.lower() for tag in tags])[:6],
    }


def _fallback_extract_entities(description: str) -> dict:
    normalized = _normalize_text(description)
    categorization = _fallback_categorization(description)

    services = [
        SERVICE_BY_CATEGORY[category["name"]]
        for category in categorization["categories"]
        if category["name"] in SERVICE_BY_CATEGORY
    ][:5]

    technologies = [
        technology
        for technology, keywords in TECHNOLOGY_KEYWORDS
        if _keyword_score(normalized, keywords) > 0
    ][:8]

    specialties = [
        specialty
        for specialty, keywords in SPECIALTY_KEYWORDS
        if _keyword_score(normalized, keywords) > 0
    ][:3]

    return {
        "services": _dedupe_keep_order(services),
        "technologies": _dedupe_keep_order(technologies),
        "specialties": _dedupe_keep_order(specialties),
        "suggested_city": None,
        "suggested_country": None,
    }


async def _get_cached(
    db: AsyncSession, provider_id, operation: str, input_hash: str
) -> dict | None:
    """Check cache for a previous AI result."""
    result = await db.execute(
        select(AiCache).where(
            AiCache.provider_id == provider_id,
            AiCache.operation == operation,
            AiCache.input_hash == input_hash,
            AiCache.expires_at > datetime.now(timezone.utc),
        )
    )
    cached = result.scalar_one_or_none()
    if cached:
        return cached.result if isinstance(cached.result, dict) else json.loads(cached.result)
    return None


async def _set_cache(
    db: AsyncSession, provider_id, operation: str, input_hash: str, result: dict
):
    """Store AI result in cache."""
    cache_entry = AiCache(
        provider_id=provider_id,
        operation=operation,
        input_hash=input_hash,
        result=result,
        expires_at=datetime.now(timezone.utc) + CACHE_TTL,
    )
    db.add(cache_entry)


def _parse_json_content(content: str | None, operation: str) -> dict:
    """Parse JSON returned by the model, tolerating fenced code blocks."""
    if not content or not content.strip():
        raise ValueError(f"OpenAI devolvio una respuesta vacia para '{operation}'")

    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if "\n" in cleaned:
            cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("\n", 1)[0].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or start >= end:
            sample = cleaned[:200].replace("\n", " ")
            raise ValueError(
                f"OpenAI no devolvio JSON valido para '{operation}'. Respuesta: {sample}"
            ) from None
        parsed = json.loads(cleaned[start:end + 1])

    if not isinstance(parsed, dict):
        raise ValueError(f"OpenAI devolvio un JSON invalido para '{operation}'")

    return parsed


def _describe_structured_output_issue(response) -> str:
    if response.error:
        return f"error del modelo: {response.error.message}"

    if response.incomplete_details and response.incomplete_details.reason:
        return f"respuesta incompleta: {response.incomplete_details.reason}"

    refusals: list[str] = []
    for output in response.output:
        if getattr(output, "type", None) != "message":
            continue
        for content in getattr(output, "content", []):
            if getattr(content, "type", None) == "refusal":
                refusals.append(getattr(content, "refusal", "refusal sin detalle"))

    if refusals:
        return f"refusal: {' | '.join(refusals[:2])}"

    return "respuesta vacia o sin contenido estructurado"


async def _request_structured_output(
    system_prompt: str,
    description: str,
    operation: str,
    schema_model: type[ModelT],
) -> ModelT:
    """Request structured output from the Responses API, retrying once on failure."""
    prompts = [
        system_prompt,
        (
            f"{system_prompt}\n\nIMPORTANTE: responde usando estrictamente el esquema "
            "solicitado, sin texto adicional, sin markdown y sin campos extra."
        ),
    ]

    last_error: ValueError | None = None

    for attempt, prompt in enumerate(prompts, start=1):
        try:
            response = await client.responses.parse(
                model=settings.openai_model,
                instructions=prompt,
                input=description,
                text_format=schema_model,
                reasoning={"effort": "low"},
                max_output_tokens=500,
                text=RESPONSE_TEXT_CONFIG,
            )
        except Exception as exc:
            last_error = ValueError(f"fallo de API para '{operation}': {exc}")
            logger.warning(
                "Fallo llamando Responses API para '%s' en intento %s: %s",
                operation,
                attempt,
                exc,
            )
            continue

        parsed = response.output_parsed
        if parsed is not None:
            return parsed

        issue = _describe_structured_output_issue(response)
        last_error = ValueError(f"OpenAI no devolvio salida estructurada para '{operation}': {issue}")
        logger.warning(
            "Salida estructurada invalida para '%s' en intento %s: %s (response_id=%s, model=%s)",
            operation,
            attempt,
            issue,
            response.id,
            response.model,
        )

    raise last_error or ValueError(f"No se pudo obtener salida estructurada para '{operation}'")


def _merge_categorization_result(ai_result: CategorizationResult, description: str) -> dict:
    fallback = _fallback_categorization(description)
    categories = [
        {"name": category.name, "confidence": round(category.confidence, 2)}
        for category in ai_result.categories
    ]
    tags = _dedupe_keep_order([tag.lower() for tag in ai_result.tags])

    if not categories:
        categories = fallback["categories"]

    if len(tags) < 3:
        tags = _dedupe_keep_order(tags + fallback["tags"])

    return {
        "categories": categories[:3],
        "tags": tags[:6],
    }


def _merge_extraction_result(ai_result: ExtractionResult, description: str) -> dict:
    fallback = _fallback_extract_entities(description)

    services = _dedupe_keep_order(ai_result.services)
    technologies = _dedupe_keep_order(ai_result.technologies)
    specialties = _dedupe_keep_order(ai_result.specialties)

    if not services:
        services = fallback["services"]
    if not technologies:
        technologies = fallback["technologies"]
    if not specialties:
        specialties = fallback["specialties"]

    return {
        "services": services[:5],
        "technologies": technologies[:8],
        "specialties": specialties[:3],
        "suggested_city": ai_result.suggested_city or fallback["suggested_city"],
        "suggested_country": ai_result.suggested_country or fallback["suggested_country"],
    }


# --- CATEGORIZATION ---

CATEGORIZE_PROMPT = """Eres un clasificador experto de proveedores de servicios tecnologicos B2B.

Dada la descripcion de un proveedor, clasificalo usando EXCLUSIVAMENTE una o mas de estas categorias exactas:
- Desarrollo Web
- Desarrollo Movil
- Diseno UI/UX
- Data Science
- Cloud & DevOps
- Ciberseguridad
- Marketing Digital
- Consultoria IT
- ERP & CRM
- Soporte & Mantenimiento

Guia de decision:
- Desarrollo Web: sitios, portales, ecommerce, frontend, backend, APIs web.
- Desarrollo Movil: apps iOS/Android, Flutter, React Native.
- Diseno UI/UX: investigacion UX, wireframes, prototipos, Figma, sistemas de diseno.
- Data Science: analitica, ML, IA aplicada, vision por computador, NLP, modelos predictivos.
- Cloud & DevOps: AWS/Azure/GCP, Docker, Kubernetes, CI/CD, Terraform, infraestructura.
- Ciberseguridad: pentesting, SOC, IAM, compliance, gestion de vulnerabilidades.
- Marketing Digital: SEO, SEM, pauta, growth, social media, automatizacion marketing.
- Consultoria IT: transformacion digital, auditoria, estrategia, arquitectura, advisory.
- ERP & CRM: SAP, Salesforce, HubSpot, Dynamics, nomina, RRHH, facturacion, SuccessFactors.
- Soporte & Mantenimiento: help desk, soporte, monitoreo, mantenimiento continuo, SLA.

Reglas:
- Asigna entre 1 y 3 categorias, las mas relevantes
- Usa solo nombres exactos de la lista anterior
- confidence es un float entre 0.0 y 1.0
- Genera entre 3 y 6 tags descriptivos y concisos
- Los tags deben ser en espanol, en minusculas
- Prioriza categorias ligadas a productos/plataformas mencionadas explicitamente
- Si una solucion es de RRHH, nomina, SAP, CRM o ERP, prioriza ERP & CRM
- Si una solucion mezcla IA con analitica, geoespacial o modelos, prioriza Data Science
- No inventes categorias fuera de la lista"""


async def categorize_provider(
    db: AsyncSession, provider_id, description: str
) -> dict:
    """Categorize a provider using AI based on its description."""
    input_hash = _hash_input(description)

    # Check cache
    cached = await _get_cached(db, provider_id, "categorize", input_hash)
    if cached:
        return cached

    try:
        parsed = await _request_structured_output(
            CATEGORIZE_PROMPT,
            description,
            "categorize",
            CategorizationResult,
        )
        result = _merge_categorization_result(parsed, description)
    except ValueError as exc:
        logger.warning(
            "Fallo categorizacion AI para provider %s, usando fallback heuristico: %s",
            provider_id,
            exc,
        )
        result = _fallback_categorization(description)

    await _set_cache(db, provider_id, "categorize", input_hash, result)
    return result


# --- ENTITY EXTRACTION ---

EXTRACT_PROMPT = """Eres un extractor de entidades para un directorio de proveedores tecnologicos.

Dada la descripcion de un proveedor, extrae la informacion estructurada.

Reglas:
- services: los servicios principales que ofrece (max 5)
- technologies: tecnologias, frameworks o herramientas mencionadas (max 8)
- specialties: areas de especializacion o industrias (max 3)
- Si la descripcion menciona ubicacion, extrae ciudad y pais
- Si no hay ubicacion, pon null
- Todo en espanol y minusculas
- No incluyas explicaciones, solo el JSON"""


async def extract_entities(
    db: AsyncSession, provider_id, description: str
) -> dict:
    """Extract structured entities from provider description."""
    input_hash = _hash_input(description)

    cached = await _get_cached(db, provider_id, "extract", input_hash)
    if cached:
        return cached

    try:
        parsed = await _request_structured_output(
            EXTRACT_PROMPT,
            description,
            "extract",
            ExtractionResult,
        )
        result = _merge_extraction_result(parsed, description)
    except ValueError as exc:
        logger.warning(
            "Fallo extraccion AI para provider %s, usando fallback heuristico: %s",
            provider_id,
            exc,
        )
        result = _fallback_extract_entities(description)

    await _set_cache(db, provider_id, "extract", input_hash, result)
    return result


# --- EMBEDDINGS ---

async def generate_embedding(
    db: AsyncSession, provider_id, description: str
) -> list[float]:
    """Generate embedding vector for a provider description."""
    input_hash = _hash_input(description)

    cached = await _get_cached(db, provider_id, "embed", input_hash)
    if cached:
        return cached["embedding"]

    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=description,
    )

    embedding = response.data[0].embedding

    await _set_cache(db, provider_id, "embed", input_hash, {"embedding": embedding})
    logger.info("Embedding generado y almacenado en cache para provider %s", provider_id)
    return embedding
