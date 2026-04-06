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
