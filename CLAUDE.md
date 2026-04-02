# CLAUDE.md — Reglas del proyecto WhatsApp Zoho MVP

## Stack

- FastAPI + SQLAlchemy + PostgreSQL (Docker)
- Pydantic v2 para validación de datos entrantes
- httpx para llamadas HTTP externas
- Alembic para migraciones de base de datos

## Arquitectura

- `Base` vive en `database.py`, no en `models.py`
- Lógica de negocio en `services/`, nunca en `routers/`
- Routers solo reciben requests y delegan a services
- Schemas Pydantic obligatorios para todo endpoint que reciba datos externos

## Patrones obligatorios

- Nunca llamar `.json()` sin verificar que el response tiene contenido (puede ser 204 o body vacío)
- Siempre hacer `db.rollback()` en el `except` antes de retornar `None`
- Usar `logger` para errores en servicios, no `print`
- `print` solo para debug temporal — eliminar antes de commitear

## Migraciones — Alembic

- Nunca hacer DROP TABLE para agregar columnas
- Flujo obligatorio ante cualquier cambio en `models.py`:
  1. `alembic revision --autogenerate -m "descripcion"`
  2. Revisar el archivo generado en `alembic/versions/`
  3. `alembic upgrade head`

## Zoho API

- `get_access_token()` se llama por request, no se cachea
- `find_contact_by_phone` retorna `None` si status 204 o body vacío
- Nunca asumir que Zoho devuelve JSON — verificar contenido antes de parsear

## Decisiones de diseño tomadas

- `zoho_contact_id` en `Conversation` — se sincroniza solo si todavía no tiene ID
- `body` en `Message` es nullable — los mensajes pueden ser imágenes o audios sin texto
- Conversaciones se identifican por `contact_number` (unique) — una conversación por núm

## Flujo de trabajo

- La arquitectura y decisiones se definen en el chat antes de implementar en Claude Code
- Cada prompt complejo a Claude Code debe incluir "siguiendo las reglas del CLAUDE.md"
- Si Claude Code genera algo que contradice este archivo, corregirlo y actualizar este archivo
