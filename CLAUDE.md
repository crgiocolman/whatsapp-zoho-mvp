# CLAUDE.md — Reglas del proyecto SiuChat

Plataforma multi-tenant de WhatsApp Business integrada con Zoho CRM.
Repo: `whatsapp-zoho-mvp` (nombre histórico, producto = SiuChat).

---

## Stack

- FastAPI + SQLAlchemy + PostgreSQL (Docker en local, managed en Railway)
- Pydantic v2 para validación de datos entrantes
- httpx para llamadas HTTP externas
- Alembic para migraciones de base de datos

---

## Entornos de desarrollo

**Local es el entorno de desarrollo por defecto. Producción (Railway) es solo para deploys validados.**

- Desarrollo: PostgreSQL en Docker en la máquina local + FastAPI corriendo con `uvicorn --reload`
- Webhook de Meta durante desarrollo: ngrok apuntando al backend local
- El webhook de Meta se cambia manualmente entre URL de ngrok y URL de Railway según corresponda
- Nunca desarrollar features nuevas directo en producción — siempre validar localmente primero
- Migraciones de Alembic se prueban en local (aplicar + rollback + aplicar de nuevo) antes de correr en Railway
- Deploy a Railway solo cuando:
  1. La feature está completa y validada localmente
  2. Las migraciones fueron probadas con rollback en local
  3. Se hizo commit + push a GitHub

---

## Arquitectura

- `Base` vive en `database.py`, no en `models.py`
- Lógica de negocio exclusivamente en `services/`, nunca en `routers/`
- Routers solo reciben requests, validan con schemas Pydantic, y delegan a services
- Schemas Pydantic obligatorios para todo endpoint que reciba datos externos
- Scripts one-shot (seeds, migraciones de datos) viven en `scripts/`

---

## Reglas multi-tenant (críticas)

**Toda query que toque `conversations`, `messages`, `contacts`, `channels`, `users` o `zoho_connections` debe filtrar por `tenant_id`. Sin excepciones.**

- Todo service recibe `tenant_id` como parámetro (o lo deriva del usuario autenticado)
- Nunca hardcodear IDs de tenant, channel, user o contact en código de producción
- El webhook entrante identifica el tenant+channel por `phone_number_id` que provee Meta
- Ningún endpoint público debe exponer datos sin pasar por un filtro de tenant
- `tenant_id` se denormaliza en `conversations` y `messages` para evitar JOINs en queries frecuentes — mantener la consistencia es responsabilidad del service (si se inserta un message, su tenant_id debe coincidir con el de su conversation)

---

## Principios de schema

- Enums como tipos nativos de PostgreSQL (no strings libres con CHECK) — SQLAlchemy + Alembic los soportan bien
- Timestamps con timezone (`TIMESTAMPTZ` / `DateTime(timezone=True)`) — sin excepción
- Partial unique indexes donde aplique (ej: `UNIQUE (tenant_id, zoho_user_id) WHERE zoho_user_id IS NOT NULL`)
- FKs con `ON DELETE RESTRICT` por default — borrados se manejan con soft delete (cambio de status), no con DELETE físico
- Tokens sensibles en columnas `Text`, no `String` con límite arbitrario
- UUID como PK en todas las tablas nuevas

---

## Patrones obligatorios

- Nunca llamar `.json()` sin verificar que el response tiene contenido (puede ser 204 o body vacío)
- Siempre hacer `db.rollback()` en el `except` antes de retornar `None`
- Usar `logger` para errores en servicios, no `print`
- `print` solo para debug temporal — eliminar antes de commitear
- Toda función que modifique BD debe estar en un service, no en un router

---

## Migraciones — Alembic

- Nunca hacer DROP TABLE para agregar columnas — eso es destructivo
- `DELETE FROM` sí es aceptable cuando los datos son descartables y está explícito en el diseño
- Flujo obligatorio ante cualquier cambio en `models.py`:
  1. `alembic revision --autogenerate -m "descripcion"`
  2. Revisar el archivo generado en `alembic/versions/` antes de correrlo
  3. Probar en local: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`
  4. Solo entonces deploy a Railway (que corre `alembic upgrade head` automáticamente en el Procfile)

---

## Zoho API

- `find_contact_by_phone` retorna `None` si status 204 o body vacío
- Nunca asumir que Zoho devuelve JSON — verificar contenido antes de parsear
- Desde Fase 4: las credenciales de Zoho viven por tenant en la tabla `zoho_connections`, no en `.env` global
- El access_token se cachea en BD con `token_expires_at`. Solo se refresca si venció o está por vencer (<5 min). El refresh actualiza ambos campos en una transacción.

---

## Decisiones de diseño tomadas

**Modelo de datos (Fase 4):**

- `contacts` es tabla propia, separada de `conversations` — un contacto puede tener múltiples conversaciones (por canal) dentro del mismo tenant
- `conversations` tiene FK a `contacts`, no guarda datos del contacto directamente
- `UNIQUE (channel_id, contact_id)` en conversations — un contacto tiene máximo una conversación por canal
- `tenant_id` denormalizado en `conversations` y `messages` para evitar JOINs frecuentes
- `body` en `Message` es nullable — los mensajes pueden ser imágenes o audios sin texto
- `users.zoho_user_id` es nullable — SiuChat puede evolucionar a mini-CRM sin Zoho obligatorio
- Roles fijos en enum: `admin`, `supervisor`, `agent` — el primer user de un tenant es siempre `admin`
- Sin `created_by` en `tenants` para evitar dependencia circular con users (se consulta via query a users)
- `channels.phone_number_id` y `zoho_connections.org_id` son UNIQUE global — no puede haber dos tenants registrando el mismo recurso de Meta/Zoho
- `zoho_connections.tenant_id` es UNIQUE — relación 1:1 entre tenant y cuenta Zoho
- `region` de Zoho se guarda como código (`com`, `eu`, `in`, `com.au`, `jp`), no URL completa

**Operación:**

- Tokens (Meta + Zoho) en texto plano hasta Fase 5 — en Fase 5 se encriptan con Fernet a nivel aplicación
- Desarrollo local-first con Docker + ngrok; producción solo para deploys validados
- Frontend actual (vanilla JS en `app/static/`) se mantiene en Fase 4 con adaptaciones mínimas; migración a SPA se planifica para Fase 5

---

## Flujo de trabajo

1. La arquitectura y decisiones se definen en el chat antes de implementar en Claude Code
2. Cada prompt complejo a Claude Code debe incluir "siguiendo las reglas del CLAUDE.md"
3. Si Claude Code genera algo que contradice este archivo, corregirlo y actualizar este archivo
4. El output de Claude Code se revisa en el chat antes de aceptar/commitear
5. Sin apuros — cada feature se diseña en detalle antes de implementar
