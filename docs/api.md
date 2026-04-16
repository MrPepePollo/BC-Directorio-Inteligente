# Documentacion de API — BC Directorio Inteligente

**Base URL:** `https://bc-directorio-backend-production.up.railway.app/api`
**Swagger UI:** `/api/docs`
**OpenAPI JSON:** `/api/openapi.json`

## Tabla de Contenidos

- [Autenticacion](#autenticacion)
- [Health](#health)
- [Providers (Proveedores)](#providers-proveedores)
- [Categories (Categorias)](#categories-categorias)
- [Search (Busqueda Inteligente)](#search-busqueda-inteligente)
- [AI (Inteligencia Artificial)](#ai-inteligencia-artificial)
- [Agents (Agentes de IA)](#agents-agentes-de-ia)

---

## Autenticacion

Los endpoints protegidos requieren un JWT de Supabase Auth en el header `Authorization`.

```
Authorization: Bearer <supabase_access_token>
```

El token se obtiene al iniciar sesion con Supabase Auth desde el frontend. El backend lo valida contra la API de Supabase.

**Endpoints publicos (sin auth):** listar proveedores, ver detalle, listar categorias, health check.
**Endpoints protegidos (auth requerida):** crear, editar, eliminar proveedores, busqueda inteligente, enriquecimiento IA, importacion web.

---

## Health

### `GET /api/health`

Health check del servicio.

**Response:**
```json
{
  "status": "ok",
  "service": "BC Directorio API"
}
```

---

## Providers (Proveedores)

### `GET /api/providers`

Listar proveedores con paginacion y filtros.

**Query Parameters:**

| Parametro | Tipo | Default | Descripcion |
|-----------|------|---------|-------------|
| `page` | int | 1 | Numero de pagina (min: 1) |
| `page_size` | int | 20 | Elementos por pagina (min: 1, max: 100) |
| `search` | string | null | Busqueda por texto en nombre y descripcion |
| `category_id` | UUID | null | Filtrar por categoria |
| `country` | string | null | Filtrar por pais |

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "TechCorp",
      "description": "Desarrollo de software a medida",
      "city": "Bogota",
      "country": "Colombia",
      "created_at": "2026-04-01T10:00:00Z",
      "categories": [
        {
          "category": { "id": "uuid", "name": "Desarrollo Web", "slug": "desarrollo-web", "description": "...", "icon": "globe" },
          "source": "manual",
          "confidence": null
        }
      ],
      "tags": [
        {
          "tag": { "id": "uuid", "name": "Python", "slug": "python" },
          "source": "ai"
        }
      ]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

### `GET /api/providers/{provider_id}`

Obtener detalle de un proveedor.

**Response (200):**
```json
{
  "id": "uuid",
  "name": "TechCorp",
  "description": "Desarrollo de software a medida...",
  "contact_email": "info@techcorp.co",
  "contact_phone": "+57 301 123 4567",
  "website": "https://techcorp.co",
  "logo_url": null,
  "city": "Bogota",
  "country": "Colombia",
  "created_at": "2026-04-01T10:00:00Z",
  "updated_at": "2026-04-01T10:00:00Z",
  "categories": [...],
  "tags": [...]
}
```

**Errores:**
- `404` — Proveedor no encontrado

---

### `POST /api/providers`

Crear un nuevo proveedor. **Requiere autenticacion.**

**Request Body:**
```json
{
  "name": "TechCorp",
  "description": "Empresa de desarrollo de software especializada en soluciones cloud",
  "contact_email": "info@techcorp.co",
  "contact_phone": "+57 301 123 4567",
  "website": "https://techcorp.co",
  "city": "Bogota",
  "country": "Colombia",
  "category_ids": ["uuid-categoria-1", "uuid-categoria-2"],
  "tag_names": ["Python", "AWS", "FastAPI"]
}
```

| Campo | Tipo | Obligatorio | Descripcion |
|-------|------|-------------|-------------|
| `name` | string | Si | Nombre (1-200 caracteres) |
| `description` | string | Si | Descripcion (min 1 caracter) |
| `contact_email` | string | No | Email de contacto |
| `contact_phone` | string | No | Telefono |
| `website` | string | No | URL del sitio web |
| `logo_url` | string | No | URL del logo |
| `city` | string | No | Ciudad |
| `country` | string | No | Pais |
| `category_ids` | UUID[] | No | IDs de categorias del catalogo |
| `tag_names` | string[] | No | Tags (se crean si no existen) |

**Response (201):** Proveedor creado (mismo formato que GET detail).

> **Nota:** Al crear un proveedor, se genera automaticamente un embedding en background para la busqueda semantica.

**Errores:**
- `401` — Autenticacion requerida
- `422` — Validacion fallida

---

### `PUT /api/providers/{provider_id}`

Actualizar un proveedor. **Solo el creador puede editar. Requiere autenticacion.**

**Request Body:** Mismos campos que POST, todos opcionales (solo se actualizan los enviados).

**Response (200):** Proveedor actualizado.

**Errores:**
- `401` — Autenticacion requerida
- `403` — No autorizado (no eres el creador)
- `404` — Proveedor no encontrado

---

### `DELETE /api/providers/{provider_id}`

Eliminar un proveedor (soft delete). **Solo el creador puede eliminar. Requiere autenticacion.**

**Response:** `204 No Content`

**Errores:**
- `401` — Autenticacion requerida
- `403` — No autorizado
- `404` — Proveedor no encontrado

---

## Categories (Categorias)

### `GET /api/categories`

Listar todas las categorias del catalogo.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "Desarrollo Web",
    "slug": "desarrollo-web",
    "description": "Desarrollo de sitios y aplicaciones web",
    "icon": "globe"
  },
  ...
]
```

---

## Search (Busqueda Inteligente)

### `GET /api/search`

Busqueda inteligente con retrieval hibrido (semantico + lexical + metadatos). **Requiere autenticacion.**

**Query Parameters:**

| Parametro | Tipo | Default | Descripcion |
|-----------|------|---------|-------------|
| `q` | string | (requerido) | Query de busqueda (min 2 caracteres) |
| `limit` | int | 20 | Maximo de resultados (1-50) |
| `category_id` | UUID | null | Filtrar por categoria |
| `country` | string | null | Filtrar por pais |
| `include_web` | bool | false | Incluir resultados de busqueda web |
| `analyze` | bool | true | Incluir analisis IA de los resultados |

**Response (200):**
```json
{
  "query": "empresa de ciberseguridad",
  "interpreted_query": "ciberseguridad servicios empresa",
  "applied_filters": {
    "country": null,
    "city": null,
    "categories": ["Ciberseguridad"],
    "technologies": [],
    "specialties": ["auditoria", "pentesting"]
  },
  "directory_results": [
    {
      "id": "uuid",
      "name": "SecureTech",
      "description": "...",
      "city": "Lima",
      "country": "Peru",
      "score": 0.87,
      "semantic_score": 0.92,
      "lexical_score": 0.75,
      "metadata_score": 0.85,
      "match_reasons": ["Alta similitud semantica", "Categoria: Ciberseguridad"]
    }
  ],
  "web_results": [
    {
      "title": "CyberDefense Corp",
      "snippet": "Empresa de ciberseguridad...",
      "url": "https://cyberdefense.com",
      "source": "openai-web-search",
      "city": "Mexico City",
      "country": "Mexico",
      "detected_categories": ["Ciberseguridad"],
      "detected_tags": ["pentesting", "SOC"],
      "match_reasons": ["Proveedor B2B de ciberseguridad"]
    }
  ],
  "analysis": {
    "summary": "Se encontraron 5 proveedores de ciberseguridad...",
    "recommendations": [
      {
        "label": "SecureTech",
        "target_type": "provider",
        "target_id": "uuid",
        "reason": "Mayor experiencia en pentesting y compliance"
      }
    ]
  },
  "session_id": "uuid",
  "meta": {
    "used_llm_parser": true,
    "used_web_search": true,
    "strategy": "hybrid",
    "web_provider": "openai"
  }
}
```

---

### `POST /api/search/sessions/{session_id}/messages`

Enviar una pregunta de seguimiento sobre los resultados de una sesion de busqueda.

**Request Body:**
```json
{
  "message": "Cual de estos proveedores tiene mas experiencia en compliance?"
}
```

**Response (200):**
```json
{
  "answer": "Basado en los resultados, SecureTech menciona explicitamente...",
  "referenced_results": ["uuid-provider-1"],
  "warning": null
}
```

---

### `POST /api/search/sessions/{session_id}/web-results/import-preview`

Generar un borrador de proveedor a partir de un resultado web. **Requiere autenticacion.**

**Request Body:**
```json
{
  "url": "https://cyberdefense.com",
  "regenerate": false
}
```

**Response (200):**
```json
{
  "status": "ready",
  "draft": {
    "name": "CyberDefense Corp",
    "description": "Empresa de ciberseguridad especializada en...",
    "contact_email": "contact@cyberdefense.com",
    "contact_phone": null,
    "website": "https://cyberdefense.com",
    "city": "Mexico City",
    "country": "Mexico",
    "category_ids": ["uuid-ciberseguridad"],
    "tag_names": ["pentesting", "SOC", "compliance"]
  },
  "source_url": "https://cyberdefense.com",
  "warnings": [],
  "duplicate_provider": null,
  "provenance": "Extraido de https://cyberdefense.com el 2026-04-05"
}
```

**Estados posibles de `status`:**
- `ready` — borrador listo para revision
- `duplicate` — ya existe un proveedor con esa URL o nombre
- `error` — no se pudo extraer informacion de la URL

---

## AI (Inteligencia Artificial)

### `POST /api/ai/enrich/{provider_id}`

Ejecutar todas las operaciones de IA sobre un proveedor: categorizar, extraer entidades y generar embedding. **Requiere autenticacion.**

**Response (200):**
```json
{
  "provider_id": "uuid",
  "categorization": {
    "categories": [
      { "name": "Desarrollo Web", "confidence": 0.95 }
    ],
    "tags": ["Python", "React", "AWS"]
  },
  "entities": {
    "services": ["Desarrollo web", "Consultoria"],
    "technologies": ["Python", "React"],
    "specialties": ["E-commerce"]
  },
  "embedding_generated": true
}
```

---

### `POST /api/ai/categorize/{provider_id}`

Ejecutar solo la categorizacion IA. **Requiere autenticacion.**

---

### `POST /api/ai/extract/{provider_id}`

Ejecutar solo la extraccion de entidades IA. **Requiere autenticacion.**

---

## Agents (Agentes de IA)

### `POST /api/agents/enrich/{provider_id}`

Ejecutar el agente autonomo de enriquecimiento sobre un proveedor. A diferencia del endpoint `/ai/enrich`, este agente usa un **loop de razonamiento ReAct** para decidir autonomamente que herramientas usar (busqueda web, scraping, extraccion de contacto, categorizacion, embeddings) y en que orden. **Requiere autenticacion.**

El agente ejecuta hasta 8 iteraciones, razonando en cada paso sobre que informacion falta y que accion tomar. Retorna una traza completa de su razonamiento y acciones.

**Herramientas del agente:**

| Herramienta | Descripcion |
|-------------|-------------|
| `search_web` | Busca informacion del proveedor en internet |
| `fetch_website` | Obtiene y parsea contenido de un sitio web |
| `extract_contact` | Extrae emails y telefonos de contenido web |
| `categorize` | Categoriza al proveedor usando IA |
| `extract_entities` | Extrae servicios, tecnologias y especialidades |
| `generate_embedding` | Genera embedding vectorial para busqueda semantica |
| `update_provider` | Aplica los datos descubiertos al proveedor |

**Response (200):**
```json
{
  "provider_id": "uuid",
  "status": "completed",
  "steps": [
    {
      "type": "thought",
      "content": "El proveedor no tiene website ni contacto. Voy a buscar en la web.",
      "duration_ms": 1200
    },
    {
      "type": "action",
      "content": "Ejecutando search_web",
      "tool": "search_web",
      "tool_input": { "query": "TechCorp servicios tecnologia" },
      "tool_output": { "found": true, "content": "TechCorp es una empresa..." },
      "duration_ms": 3400
    },
    {
      "type": "thought",
      "content": "Encontre su sitio web. Ahora voy a extraer datos de contacto.",
      "duration_ms": 800
    },
    {
      "type": "action",
      "content": "Ejecutando fetch_website",
      "tool": "fetch_website",
      "tool_input": { "url": "https://techcorp.co" },
      "tool_output": { "success": true, "title": "TechCorp", "meta_description": "..." },
      "duration_ms": 1500
    },
    {
      "type": "action",
      "content": "Ejecutando categorize",
      "tool": "categorize",
      "tool_input": { "description": "..." },
      "tool_output": { "categories": [...], "tags": [...] },
      "duration_ms": 2100
    },
    {
      "type": "action",
      "content": "Ejecutando update_provider",
      "tool": "update_provider",
      "tool_input": { "updates": { "website": "https://techcorp.co", "contact_email": "info@techcorp.co" } },
      "tool_output": { "applied": { "website": "https://techcorp.co", "contact_email": "info@techcorp.co" } },
      "duration_ms": 150
    },
    {
      "type": "final",
      "content": "Enriquecimiento completado. Se agrego website, email de contacto, 2 categorias y 4 tags."
    }
  ],
  "changes_applied": {
    "website": "https://techcorp.co",
    "contact_email": "info@techcorp.co",
    "categories_added": ["Desarrollo Web", "Cloud & DevOps"],
    "tags_added": ["python", "aws", "docker", "fastapi"]
  },
  "summary": "Enriquecimiento completado. Se agrego website, email de contacto, 2 categorias y 4 tags.",
  "total_iterations": 6,
  "total_duration_ms": 12350
}
```

**Campos de la respuesta:**

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `provider_id` | UUID | ID del proveedor enriquecido |
| `status` | string | `completed`, `partial` (limite de iteraciones), o `error` |
| `steps` | AgentStep[] | Traza completa del razonamiento y acciones |
| `changes_applied` | object | Datos que fueron efectivamente aplicados al proveedor |
| `summary` | string | Resumen en lenguaje natural de lo realizado |
| `total_iterations` | int | Numero de iteraciones del agente |
| `total_duration_ms` | int | Duracion total en milisegundos |

**Campos de cada step:**

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `type` | string | `thought`, `action`, `final`, o `error` |
| `content` | string | Descripcion del paso |
| `tool` | string? | Nombre de la herramienta (solo en `action`) |
| `tool_input` | object? | Parametros enviados a la herramienta |
| `tool_output` | object? | Resultado retornado por la herramienta |
| `duration_ms` | int? | Duracion del paso en milisegundos |

**Errores:**
- `401` — Autenticacion requerida
- `404` — Proveedor no encontrado
- `500` — Error ejecutando el agente
