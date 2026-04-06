# Manual de Usuario — BC Directorio Inteligente

## Tabla de Contenidos

- [Introduccion](#introduccion)
- [Acceso a la aplicacion](#acceso-a-la-aplicacion)
- [Funcionalidades principales](#funcionalidades-principales)
- [Flujos principales](#flujos-principales)
- [Preguntas frecuentes](#preguntas-frecuentes)

---

## Introduccion

**BC Directorio Inteligente** es una plataforma web para gestionar un directorio de proveedores de servicios tecnologicos. Permite buscar, crear, editar y eliminar proveedores, con la particularidad de que la inteligencia artificial (IA) enriquece automaticamente cada proveedor con categorias, tags y embeddings para ofrecer una **busqueda semantica avanzada**.

**Para quien es:**
- Equipos que necesitan un catalogo organizado de proveedores de servicios IT
- Usuarios que quieren descubrir proveedores por necesidad ("alguien que haga apps moviles") en vez de por nombre exacto

---

## Acceso a la aplicacion

### URL de produccion

- **Frontend:** https://frontend-ten-tau-nq31sjk493.vercel.app
- **API Docs:** https://bc-directorio-backend-production.up.railway.app/api/docs

### Crear una cuenta

1. Abre la aplicacion en tu navegador
2. Haz clic en **"Iniciar Sesion"** en la barra de navegacion
3. Selecciona **"Registrarse"** e ingresa tu email y contrasena
4. Confirma tu cuenta desde el email de verificacion que recibiras
5. Ya puedes iniciar sesion con tus credenciales

### Iniciar sesion

1. Haz clic en **"Iniciar Sesion"**
2. Ingresa tu email y contrasena
3. Seras redirigido a la pagina principal

> **Nota:** Algunas funciones como crear proveedores o usar la busqueda inteligente requieren iniciar sesion.

---

## Funcionalidades principales

### 1. Listado de proveedores

La pagina principal muestra todos los proveedores del directorio en tarjetas con:
- Nombre del proveedor
- Descripcion breve
- Categorias asignadas (badges de colores)
- Tags (etiquetas)
- Ubicacion (ciudad, pais)

**Filtros disponibles:**
- **Busqueda por texto:** filtra por nombre o descripcion
- **Por categoria:** selecciona una categoria del catalogo
- **Por pais:** filtra por ubicacion geografica

La lista se pagina automaticamente (20 proveedores por pagina).

### 2. Detalle de proveedor

Al hacer clic en una tarjeta de proveedor, se abre la vista de detalle con:
- Informacion completa del proveedor
- Email, telefono y sitio web de contacto
- Todas las categorias (con badge indicando si fueron asignadas manual o por IA)
- Tags completos
- Botones de **Editar** y **Eliminar** (solo visibles si eres el creador)

### 3. Crear proveedor

Requiere autenticacion. Haz clic en **"Nuevo Proveedor"** y completa:
- **Nombre** (obligatorio)
- **Descripcion** (obligatorio) — la IA usara este texto para categorizar automaticamente
- Email, telefono, sitio web (opcionales)
- Ciudad y pais (opcionales)
- Categorias — selecciona del catalogo predefinido
- Tags — escribe tags separados que describan los servicios

Al guardar:
- El proveedor se crea inmediatamente
- En background, la IA genera automaticamente un embedding para busqueda semantica
- Puedes ejecutar **"Enriquecer con IA"** desde el detalle para que la IA sugiera categorias y tags adicionales

### 4. Busqueda inteligente

Accede desde el boton **"Buscar"** en la navegacion (requiere autenticacion).

La busqueda tiene dos modos:

#### Busqueda en Directorio
Escribe lo que necesitas en lenguaje natural (ejemplo: *"necesito alguien que haga apps para iOS"*). El sistema:
- Interpreta tu consulta con IA
- Busca por similitud semantica en los embeddings
- Combina con busqueda lexical y filtros de metadatos
- Muestra resultados con **score de relevancia** desglosado

#### Expansion Web
Haz clic en **"Buscar en la Web"** para encontrar proveedores fuera del directorio. El sistema:
- Busca en la web usando IA (OpenAI web search)
- Muestra resultados con titulo, descripcion, URL y ubicacion
- Cada resultado web tiene un boton **"Anadir al directorio"** para importarlo

#### Analista IA
Debajo de los resultados, el analista IA proporciona:
- Un **resumen** de los resultados encontrados
- **Recomendaciones** justificadas
- La posibilidad de hacer **preguntas de seguimiento** sobre los resultados

### 5. Importar proveedor desde la web

Desde los resultados de busqueda web:
1. Haz clic en **"Anadir al directorio"** en un resultado
2. Se abre un modal con un borrador generado automaticamente por IA
3. La IA extrae: nombre, descripcion, contacto, categorias y tags del sitio web
4. Revisa y edita los datos si es necesario
5. Haz clic en **"Guardar en directorio"** para crear el proveedor
6. Si el proveedor ya existe, el sistema te lo indicara y bloqueara la duplicacion

### 6. Editar proveedor

Solo el creador del proveedor puede editarlo:
1. Ve al detalle del proveedor
2. Haz clic en **"Editar"**
3. Modifica los campos necesarios
4. Guarda los cambios

Si cambias la descripcion, el embedding se regenera automaticamente.

### 7. Eliminar proveedor

Solo el creador puede eliminar un proveedor:
1. Ve al detalle del proveedor
2. Haz clic en **"Eliminar"**
3. Confirma la accion

> La eliminacion es "suave" (soft delete) — el proveedor deja de ser visible pero no se borra fisicamente de la base de datos.

---

## Flujos principales

### Como buscar un proveedor por necesidad

1. Inicia sesion
2. Haz clic en **"Buscar"**
3. Escribe lo que necesitas en lenguaje natural: *"empresa de ciberseguridad en Colombia"*
4. Revisa los resultados del directorio, ordenados por relevancia
5. Haz clic en un resultado para ver el detalle completo
6. Si no encuentras lo que buscas, usa **"Buscar en la Web"** para expandir la busqueda

### Como agregar un proveedor nuevo

1. Inicia sesion
2. Haz clic en **"Nuevo Proveedor"**
3. Completa al menos nombre y descripcion (se descriptivo para que la IA categorice bien)
4. Selecciona categorias y agrega tags relevantes
5. Guarda el proveedor
6. Opcionalmente, ve al detalle y usa **"Enriquecer con IA"** para que la IA sugiera mas categorias y tags

### Como importar un proveedor desde la web

1. Inicia sesion y ve a la busqueda inteligente
2. Busca el tipo de proveedor que necesitas
3. Haz clic en **"Buscar en la Web"**
4. En el resultado que te interese, haz clic en **"Anadir al directorio"**
5. Revisa el borrador que genero la IA
6. Ajusta cualquier dato si es necesario
7. Haz clic en **"Guardar en directorio"**

---

## Preguntas frecuentes

**P: Necesito pagar algo para usar la aplicacion?**
R: No. La aplicacion es gratuita para el usuario final.

**P: Que pasa si la IA categoriza mal a un proveedor?**
R: Las categorias asignadas por IA se distinguen con un badge "ai". Puedes editar el proveedor y cambiar las categorias manualmente.

**P: Puedo eliminar un proveedor que creo otra persona?**
R: No. Solo el creador original puede editar o eliminar un proveedor.

**P: La busqueda inteligente funciona sin iniciar sesion?**
R: No. La busqueda inteligente requiere autenticacion. Sin embargo, puedes navegar el listado de proveedores y ver sus detalles sin cuenta.

**P: Cuantos proveedores puedo crear?**
R: No hay limite en la cantidad de proveedores que puedes crear.

**P: En que idioma debo escribir la descripcion del proveedor?**
R: La IA funciona bien tanto en espanol como en ingles. Escribe en el idioma que prefieras.
