# Guia de Instalacion Local — BC Directorio Inteligente

## Tabla de Contenidos

- [Prerrequisitos](#prerrequisitos)
- [Clonar el repositorio](#clonar-el-repositorio)
- [Variables de entorno](#variables-de-entorno)
- [Backend (FastAPI)](#backend-fastapi)
- [Frontend (Vue 3)](#frontend-vue-3)
- [Base de datos (Supabase)](#base-de-datos-supabase)
- [Verificacion](#verificacion)
- [Troubleshooting](#troubleshooting)

---

## Prerrequisitos

| Herramienta | Version minima | Instalacion |
|-------------|---------------|-------------|
| **Git** | 2.x | `sudo apt install git` |
| **Python** | 3.12+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 20.19+ o 22.12+ | [nodejs.org](https://nodejs.org/) |
| **pnpm** | 9.x+ | `npm install -g pnpm` |
| **Cuenta Supabase** | - | [supabase.com](https://supabase.com) (free tier) |
| **API Key de OpenAI** | - | [platform.openai.com](https://platform.openai.com/api-keys) |

---

## Clonar el repositorio

```bash
git clone https://github.com/MrPepePollo/BC-Directorio-Inteligente.git
cd BC-Directorio-Inteligente
```

---

## Variables de entorno

### Backend (`backend/.env`)

Crear el archivo `backend/.env` con las siguientes variables:

```env
# Supabase (obligatorio)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key
DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/postgres

# OpenAI (obligatorio)
OPENAI_API_KEY=sk-proj-tu-api-key

# Opcionales
DEBUG=true
FRONTEND_URL=http://localhost:5173
OPENAI_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
WEB_SEARCH_PROVIDER=openai
```

| Variable | Obligatoria | Descripcion |
|----------|-------------|-------------|
| `SUPABASE_URL` | Si | URL de tu proyecto Supabase |
| `SUPABASE_ANON_KEY` | Si | Clave publica (anon) de Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Si | Clave de servicio de Supabase |
| `DATABASE_URL` | Si | Connection string de PostgreSQL (formato asyncpg) |
| `OPENAI_API_KEY` | Si | API key de OpenAI para IA |
| `DEBUG` | No | Activa logs SQL detallados (default: false) |
| `FRONTEND_URL` | No | URL del frontend para CORS (default: http://localhost:5173) |
| `OPENAI_MODEL` | No | Modelo para categorizacion/extraccion (default: gpt-5-mini) |
| `OPENAI_EMBEDDING_MODEL` | No | Modelo de embeddings (default: text-embedding-3-small) |
| `WEB_SEARCH_PROVIDER` | No | Proveedor de busqueda web: openai, none, disabled (default: openai) |

> **Donde encontrar las credenciales de Supabase:** Dashboard del proyecto > Settings > API. El `DATABASE_URL` esta en Settings > Database > Connection string (usar el formato de Session pooler).

### Frontend (`frontend/.env`)

Crear el archivo `frontend/.env`:

```env
VITE_SUPABASE_URL=https://tu-proyecto.supabase.co
VITE_SUPABASE_ANON_KEY=tu-anon-key
VITE_API_URL=http://localhost:8000/api
```

| Variable | Obligatoria | Descripcion |
|----------|-------------|-------------|
| `VITE_SUPABASE_URL` | Si | URL de tu proyecto Supabase |
| `VITE_SUPABASE_ANON_KEY` | Si | Clave publica (anon) de Supabase |
| `VITE_API_URL` | Si | URL base de la API del backend |

---

## Backend (FastAPI)

Todos los comandos se ejecutan desde la carpeta `backend/`:

```bash
cd backend
```

### 1. Crear entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Iniciar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

**Output esperado:**

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

El backend estara disponible en `http://localhost:8000` con documentacion Swagger en `http://localhost:8000/api/docs`.

---

## Frontend (Vue 3)

Todos los comandos se ejecutan desde la carpeta `frontend/`:

```bash
cd frontend
```

### 1. Instalar dependencias

```bash
pnpm install
```

### 2. Iniciar servidor de desarrollo

```bash
pnpm dev
```

**Output esperado:**

```
  VITE v8.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

El frontend estara disponible en `http://localhost:5173`.

---

## Base de datos (Supabase)

### 1. Crear proyecto en Supabase

1. Ir a [supabase.com](https://supabase.com) y crear una cuenta
2. Crear un nuevo proyecto (elegir region cercana)
3. Anotar las credenciales de API (Settings > API)

### 2. Habilitar extensiones

Desde el SQL Editor de Supabase, ejecutar:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS moddatetime;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 3. Crear tablas

El esquema completo de tablas, funciones, triggers y politicas RLS esta documentado en [plans/database_schema.md](../plans/database_schema.md). Ejecutar los bloques SQL en orden desde el SQL Editor de Supabase.

### 4. Seed de categorias

```sql
INSERT INTO categories (name, slug, description, icon) VALUES
  ('Desarrollo Web', 'desarrollo-web', 'Desarrollo de sitios y aplicaciones web', 'globe'),
  ('Desarrollo Movil', 'desarrollo-movil', 'Apps nativas e hibridas iOS/Android', 'smartphone'),
  ('Diseno UI/UX', 'diseno-ui-ux', 'Diseno de interfaces y experiencia de usuario', 'palette'),
  ('Data Science', 'data-science', 'Analisis de datos, ML e inteligencia artificial', 'bar-chart'),
  ('Cloud & DevOps', 'cloud-devops', 'Infraestructura cloud, CI/CD, contenedores', 'cloud'),
  ('Ciberseguridad', 'ciberseguridad', 'Seguridad informatica y auditoria', 'shield'),
  ('Marketing Digital', 'marketing-digital', 'SEO, SEM, redes sociales, contenido', 'megaphone'),
  ('Consultoria IT', 'consultoria-it', 'Asesoria tecnologica y transformacion digital', 'briefcase'),
  ('ERP & CRM', 'erp-crm', 'Implementacion de sistemas empresariales', 'database'),
  ('Soporte & Mantenimiento', 'soporte-mantenimiento', 'Soporte tecnico y mantenimiento de sistemas', 'wrench')
ON CONFLICT (name) DO NOTHING;
```

---

## Verificacion

Una vez que tanto backend como frontend esten corriendo:

### Health check del backend

```bash
curl http://localhost:8000/api/health
```

**Respuesta esperada:**

```json
{"status": "ok", "service": "BC Directorio API"}
```

### Swagger UI

Abrir en el navegador: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### Frontend

Abrir en el navegador: [http://localhost:5173](http://localhost:5173)

Deberias ver la pagina principal con el listado de proveedores (vacio si es una instalacion nueva).

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'asyncpg'`

Asegurate de tener `asyncpg` en requirements.txt e instalar con:

```bash
pip install asyncpg
```

### El frontend no conecta con el backend (CORS)

Verificar que `FRONTEND_URL` en `backend/.env` coincida exactamente con la URL del frontend (incluyendo protocolo y puerto).

### `Error: Token invalido` al crear un proveedor

Asegurate de haber iniciado sesion en el frontend. La creacion/edicion de proveedores requiere autenticacion via Supabase Auth.

### La busqueda semantica no devuelve resultados

Los embeddings se generan en background al crear un proveedor. Espera unos segundos y reintenta. Verifica que `OPENAI_API_KEY` sea valida.

### `DATABASE_URL` connection refused

Verifica que el connection string use el formato correcto:
- Para uso con asyncpg: `postgresql+asyncpg://user:pass@host:5432/postgres`
- Usa el Session pooler de Supabase (puerto 5432), no el Direct connection
