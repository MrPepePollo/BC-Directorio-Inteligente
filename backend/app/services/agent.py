"""
Agente de enriquecimiento de proveedores con patron ReAct (Reason + Act).

El agente recibe un proveedor con informacion basica y autonomamente decide
que herramientas usar para completar su perfil: buscar en la web, extraer
datos de contacto, categorizar, generar tags y embeddings.

Patron ReAct:
1. THOUGHT: El agente razona sobre que informacion falta
2. ACTION: Elige y ejecuta una herramienta
3. OBSERVATION: Recibe el resultado
4. Repite hasta completar o alcanzar el limite de iteraciones

Herramientas disponibles:
- search_web: Busca informacion del proveedor en la web
- fetch_website: Obtiene y parsea contenido de un sitio web
- extract_contact: Extrae email y telefono de contenido HTML
- categorize: Categoriza al proveedor usando IA
- extract_entities: Extrae servicios, tecnologias y especialidades
- generate_embedding: Genera embedding vectorial para busqueda semantica
- update_provider: Aplica los cambios descubiertos al proveedor
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
import openai
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.provider import Category, Provider, ProviderCategory, ProviderTag, Tag
from app.services.ai import (
    categorize_provider,
    extract_entities,
    generate_embedding,
)

settings = get_settings()
client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8
AGENT_MODEL = settings.openai_model
BLOCKED_PROFILE_DOMAINS = (
    "signalhire.com",
    "rocketreach.co",
    "apollo.io",
    "zoominfo.com",
    "crunchbase.com",
    "linkedin.com",
)


class StepType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL = "final"
    ERROR = "error"


class AgentDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    thought: str = Field(min_length=1, max_length=500)
    action: str = Field(min_length=1, max_length=40)
    action_input: dict[str, Any] = Field(default_factory=dict)


@dataclass
class AgentStep:
    type: StepType
    content: str
    tool: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"type": self.type.value, "content": self.content}
        if self.tool:
            result["tool"] = self.tool
        if self.tool_input is not None:
            result["tool_input"] = self.tool_input
        if self.tool_output is not None:
            result["tool_output"] = self.tool_output
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        return result


@dataclass
class AgentResult:
    provider_id: str
    status: str  # "completed" | "partial" | "error"
    steps: list[AgentStep] = field(default_factory=list)
    changes_applied: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    total_iterations: int = 0
    total_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "changes_applied": self.changes_applied,
            "summary": self.summary,
            "total_iterations": self.total_iterations,
            "total_duration_ms": self.total_duration_ms,
        }


# --- TOOL IMPLEMENTATIONS ---


def _clean_html_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    import html

    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _slugify(text_str: str) -> str:
    text_str = text_str.lower().strip()
    text_str = re.sub(r"[^\w\s-]", "", text_str)
    return re.sub(r"[\s_]+", "-", text_str)


def _is_blocked_profile_url(url: str) -> bool:
    return any(domain in url.lower() for domain in BLOCKED_PROFILE_DOMAINS)


def _serialize_embedding(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    if not all(isinstance(item, int | float) for item in value):
        return None
    return "[" + ",".join(str(float(item)) for item in value) + "]"


def _description_quality_score(value: str) -> int:
    normalized = re.sub(r"\s+", " ", value.strip())
    score = min(len(normalized), 500)
    business_terms = (
        "software",
        "soluciones",
        "desarrollo",
        "tecnologia",
        "servicios",
        "plataforma",
        "consultoria",
        "aplicaciones",
        "empresarial",
        "digital",
    )
    score += sum(35 for term in business_terms if term in normalized.casefold())
    return score


def _is_description_update_allowed(current: str, candidate: Any) -> bool:
    if not isinstance(candidate, str):
        return False

    cleaned = re.sub(r"\s+", " ", candidate).strip()
    if len(cleaned) < 80 or len(cleaned) > 700:
        return False

    rejected_patterns = (
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
        r"https?://",
        r"\bcookie\b",
        r"\bjavascript\b",
        r"\bdocument\.",
        r"\baddEventListener\b",
    )
    if any(re.search(pattern, cleaned, flags=re.IGNORECASE) for pattern in rejected_patterns):
        return False

    current_cleaned = re.sub(r"\s+", " ", current or "").strip()
    if cleaned.casefold() == current_cleaned.casefold():
        return False

    return _description_quality_score(cleaned) >= _description_quality_score(current_cleaned) + 40


async def tool_search_web(query: str) -> dict[str, Any]:
    """Search the web for information about a provider."""
    try:
        response = await client.responses.create(
            model=AGENT_MODEL,
            instructions=(
                "Busca informacion sobre esta empresa o proveedor de tecnologia. "
                "Encuentra su sitio web oficial, servicios principales, ubicacion y datos de contacto. "
                "Devuelve un resumen estructurado de lo que encontraste."
            ),
            input=query,
            tools=[{"type": "web_search"}],
            max_output_tokens=2000,
            text={"verbosity": "low"},
        )
        content = ""
        for output in response.output:
            if getattr(output, "type", None) == "message":
                for block in getattr(output, "content", []):
                    if getattr(block, "type", None) == "output_text":
                        content += getattr(block, "text", "")
        return {"found": bool(content.strip()), "content": content.strip()[:3000]}
    except Exception as exc:
        return {"found": False, "content": "", "error": str(exc)}


async def tool_fetch_website(url: str) -> dict[str, Any]:
    """Fetch and parse a website to extract useful information."""
    is_third_party_profile = _is_blocked_profile_url(url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as http_client:
            response = await http_client.get(url, headers=headers)
        if response.status_code >= 400:
            return {"success": False, "error": f"HTTP {response.status_code}"}

        html_content = response.text[:150_000]
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, flags=re.IGNORECASE | re.DOTALL)
        meta_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        headings = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html_content, flags=re.IGNORECASE | re.DOTALL)
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html_content, flags=re.IGNORECASE | re.DOTALL)

        return {
            "success": True,
            "final_url": str(response.url),
            "is_third_party_profile": (
                is_third_party_profile or _is_blocked_profile_url(str(response.url))
            ),
            "title": _clean_html_text(title_match.group(1)) if title_match else "",
            "meta_description": _clean_html_text(meta_match.group(1)) if meta_match else "",
            "headings": [_clean_html_text(h) for h in headings[:8]],
            "paragraphs": [_clean_html_text(p) for p in paragraphs[:6] if len(_clean_html_text(p)) > 20],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def tool_extract_contact(html_content_or_url: str) -> dict[str, Any]:
    """Extract contact information (email, phone) from web content."""
    content = html_content_or_url

    if content.startswith("http"):
        fetch_result = await tool_fetch_website(content)
        if not fetch_result.get("success"):
            return {"emails": [], "phones": [], "error": fetch_result.get("error")}
        content = json.dumps(fetch_result)

    emails = list(set(re.findall(
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
        content,
        flags=re.IGNORECASE,
    )))
    phone_candidates = re.findall(
        r"(?<![\w.])(?:\+?\d[\d\s().-]{6,}\d)(?![\w.])",
        content,
    )
    phones: list[str] = []
    seen_phones: set[str] = set()
    for candidate in phone_candidates:
        digits = re.sub(r"\D", "", candidate)
        if len(digits) < 7 or len(digits) > 15:
            continue
        if not (candidate.strip().startswith("+") or (len(digits) == 9 and digits.startswith("9")) or len(digits) >= 10):
            continue
        if digits not in seen_phones:
            seen_phones.add(digits)
            phones.append(candidate.strip())

    return {
        "emails": emails[:3],
        "phones": phones[:3],
    }


async def tool_categorize(db: AsyncSession, provider_id: str, description: str) -> dict[str, Any]:
    """Categorize a provider using AI."""
    result = await categorize_provider(db, provider_id, description)
    return result


async def tool_extract_entities_wrapper(db: AsyncSession, provider_id: str, description: str) -> dict[str, Any]:
    """Extract structured entities from a provider description."""
    result = await extract_entities(db, provider_id, description)
    return result


async def tool_generate_embedding_wrapper(db: AsyncSession, provider_id: str, description: str) -> dict[str, Any]:
    """Generate embedding for semantic search."""
    embedding = await generate_embedding(db, provider_id, description)
    return {"dimensions": len(embedding), "generated": True}


async def tool_update_provider(
    db: AsyncSession,
    provider: Provider,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Apply discovered updates to the provider record."""
    applied: dict[str, str] = {}
    fields = ["contact_email", "contact_phone", "website", "city", "country"]
    for field_name in fields:
        if field_name in updates and updates[field_name]:
            if field_name == "website" and _is_blocked_profile_url(str(updates[field_name])):
                continue
            current = getattr(provider, field_name)
            if not current:
                setattr(provider, field_name, updates[field_name])
                applied[field_name] = updates[field_name]

    if _is_description_update_allowed(provider.description, updates.get("description")):
        provider.description = re.sub(r"\s+", " ", updates["description"]).strip()
        applied["description"] = "updated"

    if "categories" in updates:
        for cat_data in updates["categories"]:
            cat_name = cat_data.get("name", "").strip()
            cat_slug = _slugify(cat_name)
            cat_result = await db.execute(
                select(Category).where(
                    (Category.name == cat_name) | (Category.slug == cat_slug)
                )
            )
            category = cat_result.scalar_one_or_none()
            if category:
                existing = await db.execute(
                    select(ProviderCategory).where(
                        ProviderCategory.provider_id == provider.id,
                        ProviderCategory.category_id == category.id,
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(ProviderCategory(
                        provider_id=provider.id,
                        category_id=category.id,
                        source="ai",
                        confidence=cat_data.get("confidence"),
                    ))
                    applied.setdefault("categories_added", [])
                    applied["categories_added"].append(cat_name)

    if "tags" in updates:
        for tag_name in updates["tags"]:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            slug = _slugify(tag_name)
            tag_result = await db.execute(select(Tag).where(Tag.slug == slug))
            tag = tag_result.scalar_one_or_none()
            if not tag:
                tag = Tag(name=tag_name, slug=slug)
                db.add(tag)
                await db.flush()
            existing_pt = await db.execute(
                select(ProviderTag).where(
                    ProviderTag.provider_id == provider.id,
                    ProviderTag.tag_id == tag.id,
                )
            )
            if not existing_pt.scalar_one_or_none():
                db.add(ProviderTag(
                    provider_id=provider.id,
                    tag_id=tag.id,
                    source="ai",
                ))
                applied.setdefault("tags_added", [])
                applied["tags_added"].append(tag_name)

    embedding_text = _serialize_embedding(updates.get("embedding"))
    if embedding_text:
        await db.execute(
            text("UPDATE providers SET search_embedding = :embedding WHERE id = :id"),
            {"embedding": embedding_text, "id": str(provider.id)},
        )
        applied["embedding"] = "generated"

    return {"applied": applied}


# --- AGENT ORCHESTRATOR ---


TOOL_DESCRIPTIONS = """
Available tools:
1. search_web(query: str) - Search the web for information about the provider. Use the provider name and any known details as the query.
2. fetch_website(url: str) - Fetch and parse a specific website URL to extract content, headings, meta description.
3. extract_contact(content_or_url: str) - Extract email addresses and phone numbers from web content or a URL.
4. categorize(description: str) - Categorize the provider into predefined categories using AI.
5. extract_entities(description: str) - Extract services, technologies, and specialties from the description.
6. generate_embedding(description: str) - Generate a vector embedding for semantic search.
7. update_provider(updates: object) - Apply discovered data to the provider. Fields: description, contact_email, contact_phone, website, city, country, categories, tags, embedding.
8. finish(summary: str) - Complete the enrichment process with a summary of what was done.
"""

SYSTEM_PROMPT = f"""Eres un agente inteligente de enriquecimiento de proveedores para un directorio B2B de tecnologia.

Tu objetivo es completar el perfil de un proveedor que tiene informacion basica (nombre y descripcion) usando las herramientas disponibles.

{TOOL_DESCRIPTIONS}

## Proceso de razonamiento (ReAct)

En cada iteracion debes responder con un JSON con esta estructura exacta:
{{
  "thought": "Tu razonamiento sobre que informacion falta y que hacer a continuacion",
  "action": "nombre_de_la_herramienta",
  "action_input": {{ ... argumentos de la herramienta ... }}
}}

O si ya terminaste:
{{
  "thought": "Razonamiento final",
  "action": "finish",
  "action_input": {{ "summary": "Resumen de lo que se hizo y encontro" }}
}}

## Reglas

1. Analiza que informacion falta del proveedor antes de actuar
2. Si no hay website, busca primero en la web con search_web
3. Si encontraste un website, usa fetch_website para obtener mas datos
4. Usa extract_contact para encontrar email y telefono
5. Siempre ejecuta categorize y extract_entities para mejorar la clasificacion
6. Siempre genera el embedding al final
7. Usa update_provider para aplicar los datos descubiertos ANTES de finish
8. No inventes datos — solo usa informacion verificada de las herramientas
9. Si una herramienta falla, intenta un enfoque alternativo
10. Maximo {MAX_ITERATIONS} iteraciones — prioriza lo mas importante primero
11. Responde SOLO con JSON valido, sin markdown ni texto adicional
12. No guardes paginas agregadoras como sitio oficial (SignalHire, LinkedIn, Apollo, ZoomInfo, Crunchbase, RocketReach)
13. No copies descripciones largas en action_input; si una herramienta acepta description, puedes omitirla y se usara la descripcion actual
14. Puedes mejorar description solo si el sitio oficial aporta informacion mas clara. Escribe 1-3 frases B2B, sin emails, telefonos, URLs, cookies ni texto tecnico del HTML
"""


def _parse_agent_response(content: str) -> dict[str, Any]:
    """Parse the agent's first JSON decision, tolerating fences and trailing text."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        fence_match = re.match(
            r"```(?:json)?\s*(.*?)\s*```",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fence_match:
            cleaned = fence_match.group(1).strip()

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            parsed, _end = decoder.raw_decode(cleaned[match.start():])
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            raise ValueError("Agent response JSON must be an object")
        return parsed

    if cleaned in {"", "{"}:
        raise ValueError("Incomplete JSON response from agent model")

    raise ValueError(f"No JSON found in response: {cleaned[:200]}")


def _extract_response_text(response: Any) -> str:
    text_parts: list[str] = []
    for output in response.output:
        if getattr(output, "type", None) != "message":
            continue
        for block in getattr(output, "content", []):
            if getattr(block, "type", None) == "output_text":
                text_parts.append(getattr(block, "text", ""))
    return "".join(text_parts)


async def _request_agent_decision(messages: list[dict[str, str]]) -> tuple[dict[str, Any], str]:
    """Request one structured ReAct decision from the model."""
    retry_message = {
        "role": "user",
        "content": (
            "La decision anterior llego vacia o incompleta. Devuelve una sola decision "
            "estructurada corta. No copies textos largos en action_input."
        ),
    }
    last_error: Exception | None = None

    for attempt in range(2):
        attempt_messages = messages if attempt == 0 else [*messages, retry_message]
        try:
            response = await client.responses.parse(
                model=AGENT_MODEL,
                instructions=SYSTEM_PROMPT,
                input=attempt_messages,
                text_format=AgentDecision,
                reasoning={"effort": "low"},
                max_output_tokens=1200,
                text={"verbosity": "low"},
            )
            if response.output_parsed is not None:
                decision = response.output_parsed.model_dump()
                return decision, json.dumps(decision, ensure_ascii=False)

            response_text = _extract_response_text(response)
            if response_text:
                try:
                    return _parse_agent_response(response_text), response_text
                except ValueError as exc:
                    last_error = exc
                    logger.warning(
                        "Structured agent decision text was invalid on attempt %d: %s",
                        attempt + 1,
                        exc,
                    )
                    continue

            last_error = ValueError("Empty structured agent decision")
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Structured agent decision failed on attempt %d: %s",
                attempt + 1,
                exc,
            )

    logger.warning("Structured agent decision failed, using raw JSON fallback: %s", last_error)

    for attempt in range(2):
        attempt_messages = messages if attempt == 0 else [*messages, retry_message]
        response = await client.responses.create(
            model=AGENT_MODEL,
            instructions=SYSTEM_PROMPT,
            input=attempt_messages,
            reasoning={"effort": "low"},
            max_output_tokens=1500,
            text={"verbosity": "low"},
        )
        response_text = _extract_response_text(response)
        try:
            return _parse_agent_response(response_text), response_text
        except ValueError as exc:
            last_error = exc
            logger.warning(
                "Raw agent decision was invalid on attempt %d: %s",
                attempt + 1,
                exc,
            )

    raise last_error or ValueError("Unable to get a valid agent decision")


def _build_provider_context(provider: Provider) -> str:
    """Build a description of the current provider state for the agent."""
    context = {
        "id": str(provider.id),
        "name": provider.name,
        "description": provider.description,
        "contact_email": provider.contact_email,
        "contact_phone": provider.contact_phone,
        "website": provider.website,
        "city": provider.city,
        "country": provider.country,
        "has_categories": len(provider.categories) > 0,
        "category_count": len(provider.categories),
        "has_tags": len(provider.tags) > 0,
        "tag_count": len(provider.tags),
    }

    missing = []
    if not provider.contact_email:
        missing.append("contact_email")
    if not provider.contact_phone:
        missing.append("contact_phone")
    if not provider.website:
        missing.append("website")
    if not provider.city:
        missing.append("city")
    if not provider.country:
        missing.append("country")
    if len(provider.categories) == 0:
        missing.append("categories")
    if len(provider.tags) == 0:
        missing.append("tags")

    context["missing_fields"] = missing
    return json.dumps(context, ensure_ascii=False)


async def run_enrichment_agent(
    db: AsyncSession,
    provider: Provider,
) -> AgentResult:
    """Run the ReAct enrichment agent on a provider."""
    start_time = time.monotonic()
    provider_id = str(provider.id)
    result = AgentResult(provider_id=provider_id, status="completed")

    provider_context = _build_provider_context(provider)
    messages = [
        {"role": "user", "content": f"Enriquece este proveedor:\n{provider_context}"},
    ]

    accumulated_updates: dict[str, Any] = {}
    last_fetch_content = ""

    for iteration in range(MAX_ITERATIONS):
        result.total_iterations = iteration + 1
        step_start = time.monotonic()

        try:
            parsed, response_text = await _request_agent_decision(messages)

        except Exception as exc:
            step_ms = int((time.monotonic() - step_start) * 1000)
            result.steps.append(AgentStep(
                type=StepType.ERROR,
                content=f"Error en iteracion {iteration + 1}: {exc}",
                duration_ms=step_ms,
            ))
            logger.warning("Agent iteration %d failed: %s", iteration + 1, exc)
            if iteration >= 2:
                result.status = "partial"
                break
            continue

        thought = parsed.get("thought", "")
        action = parsed.get("action", "")
        action_input = parsed.get("action_input", {})
        step_ms = int((time.monotonic() - step_start) * 1000)

        # Log thought
        result.steps.append(AgentStep(
            type=StepType.THOUGHT,
            content=thought,
            duration_ms=step_ms,
        ))

        # Handle finish
        if action == "finish":
            summary = action_input.get("summary", "Enriquecimiento completado.")
            result.steps.append(AgentStep(
                type=StepType.FINAL,
                content=summary,
            ))
            result.summary = summary
            break

        # Execute tool
        tool_start = time.monotonic()
        observation: dict[str, Any] = {}

        try:
            if action == "search_web":
                observation = await tool_search_web(action_input.get("query", provider.name))

            elif action == "fetch_website":
                observation = await tool_fetch_website(action_input.get("url", ""))
                last_fetch_content = json.dumps(observation, ensure_ascii=False, default=str)
                final_url = observation.get("final_url")
                if final_url and not observation.get("is_third_party_profile"):
                    accumulated_updates.setdefault("website", final_url)

            elif action == "extract_contact":
                contact_source = action_input.get("content_or_url") or last_fetch_content
                observation = await tool_extract_contact(contact_source)
                emails = observation.get("emails", [])
                phones = observation.get("phones", [])
                if emails:
                    accumulated_updates.setdefault("contact_email", emails[0])
                if phones:
                    accumulated_updates.setdefault("contact_phone", phones[0])

            elif action == "categorize":
                desc = action_input.get("description", provider.description)
                observation = await tool_categorize(db, provider_id, desc)
                accumulated_updates["categories"] = observation.get("categories", [])
                accumulated_updates["tags"] = observation.get("tags", [])

            elif action == "extract_entities":
                desc = action_input.get("description", provider.description)
                observation = await tool_extract_entities_wrapper(db, provider_id, desc)

            elif action == "generate_embedding":
                desc = action_input.get("description", provider.description)
                embedding = await generate_embedding(db, provider_id, desc)
                observation = {"dimensions": len(embedding), "generated": True}
                accumulated_updates["embedding"] = embedding

            elif action == "update_provider":
                updates = action_input.get("updates", action_input)
                updates.pop("embedding", None)
                # Merge model-proposed fields with trusted backend discoveries.
                merged = {**updates, **accumulated_updates}
                observation = await tool_update_provider(db, provider, merged)
                result.changes_applied = observation.get("applied", {})
                accumulated_updates.clear()

            else:
                observation = {"error": f"Herramienta desconocida: {action}"}

        except Exception as exc:
            await db.rollback()
            observation = {"error": str(exc)}
            logger.warning("Tool %s failed: %s", action, exc)

        tool_ms = int((time.monotonic() - tool_start) * 1000)

        result.steps.append(AgentStep(
            type=StepType.ACTION,
            content=f"Ejecutando {action}",
            tool=action,
            tool_input=action_input,
            tool_output=observation,
            duration_ms=tool_ms,
        ))

        # Feed observation back to the agent
        observation_text = json.dumps(observation, ensure_ascii=False, default=str)[:4000]
        messages.append({"role": "assistant", "content": response_text})
        messages.append({"role": "user", "content": f"OBSERVATION:\n{observation_text}"})

    else:
        # Max iterations reached
        result.status = "partial"
        result.summary = f"Agente detenido tras {MAX_ITERATIONS} iteraciones."
        result.steps.append(AgentStep(
            type=StepType.FINAL,
            content=result.summary,
        ))

    # Apply any remaining accumulated updates
    if accumulated_updates:
        try:
            applied = await tool_update_provider(db, provider, accumulated_updates)
            result.changes_applied.update(applied.get("applied", {}))
        except Exception as exc:
            logger.warning("Failed to apply remaining updates: %s", exc)

    # Refresh search index
    try:
        from app.services.search import refresh_provider_search_index
        await refresh_provider_search_index(db, provider_id)
    except Exception as exc:
        logger.warning("Failed to refresh search index: %s", exc)

    await db.commit()

    result.total_duration_ms = int((time.monotonic() - start_time) * 1000)
    return result
