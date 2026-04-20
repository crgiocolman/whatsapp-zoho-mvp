# CLAUDE.md — Reglas del proyecto SiuChat

Plataforma multi-tenant de WhatsApp Business integrada con Zoho CRM. Repo: `whatsapp-zoho-mvp` (nombre histórico, producto = SiuChat).

Para contexto extendido: ver `docs/design-decisions.md` (historial de por qué), `docs/common-patterns.md` (patrones de código del proyecto), `docs/roadmap.md` (fases), `HANDOFF.md` (estado actual operativo).

---

## Stack

FastAPI + SQLAlchemy + PostgreSQL + Pydantic v2 + httpx + Alembic. Docker local, Railway en prod.

---

## Entornos

- Desarrollo: Docker Postgres + `uvicorn --reload` + ngrok para webhook de Meta
- Nunca desarrollar features nuevas directo en producción
- Migraciones probadas localmente con `upgrade → downgrade → upgrade` antes de Railway
- Deploy a Railway solo con feature validada + migración probada + commit pusheado

---

## Arquitectura

- `Base` vive en `database.py`, no en `models.py`
- Lógica de negocio en `services/`, nunca en `routers/`
- Routers: validan con Pydantic y delegan a services
- Schemas Pydantic obligatorios para todo endpoint con datos externos
- Scripts one-shot en `scripts/`

---

## Multi-tenant (crítico)

- Toda query a `conversations`, `messages`, `contacts`, `channels`, `users`, `zoho_connections` filtra por `tenant_id`. Sin excepciones.
- Services reciben `tenant_id` como parámetro, o objeto ya resuelto (`Channel`, `ZohoConnection`)
- Nunca hardcodear IDs de tenant, channel, user o contact
- Webhook entrante identifica tenant+channel por `phone_number_id` de Meta
- `tenant_id` denormalizado en `conversations` y `messages` — service responsable de consistencia

---

## Schema

- Enums como tipos nativos de PostgreSQL, no strings con CHECK
- Enums Python heredan de `(str, Enum)`, miembros UPPERCASE, valores lowercase. Usar `values_callable=lambda obj: [e.value for e in obj]` en la columna SQLAlchemy
- Timestamps con timezone siempre: `DateTime(timezone=True)` / `TIMESTAMPTZ`
- `datetime.now(timezone.utc)` en Python. Nunca `datetime.utcnow()` (deprecated)
- FKs con `ON DELETE RESTRICT` por default. Borrados lógicos via status, no físicos
- Todas las FKs y unique constraints llevan `name="..."` explícito
- Partial unique indexes donde aplique
- Tokens sensibles en `Text`, no `String`
- UUID como PK en tablas nuevas

---

## Patrones obligatorios

- Nunca `.json()` sin verificar que el response tiene contenido (puede ser 204 o body vacío)
- `db.rollback()` en except antes de retornar None
- `logger` para errores en services, nunca `print`
- `print` solo debug temporal, eliminar antes de commit
- Toda función que modifique BD vive en service, no en router
- Mensajes (inbound/outbound) usan timestamp de procesamiento con
  datetime.now(timezone.utc), no timestamp del proveedor externo. Así
  el orden de mensajes en el panel refleja el flujo real de la
  conversación. El timestamp original del proveedor se preserva en
  campo separado cuando corresponde (Fase 6 para meta_timestamp).

---

## Alembic

- Nunca DROP TABLE para agregar columnas
- `DELETE FROM` solo si datos son descartables y está explícito en el diseño
- Flujo: `alembic revision --autogenerate` → revisar el archivo → probar upgrade/downgrade/upgrade local → deploy
- Alembic autogenerate tiene bugs conocidos: no emite ENUM DROP en downgrade, no emite `ORDER BY DESC` en índices, no siempre respeta orden de FKs entre tablas nuevas. Revisar siempre.
- Cambio de columna String a Enum: requiere `postgresql_using="col::enum_type"`
- ADD COLUMN NOT NULL sobre tabla con datos: DELETE primero (si descartables) o migración en 3 pasos (add nullable → backfill → alter not null)

---

## Zoho API

- `find_contact_by_phone` retorna None si status 204 o body vacío
- Nunca asumir que Zoho devuelve JSON — verificar contenido antes de parsear
- Credenciales viven por tenant en `zoho_connections`, no en `.env` global
- `access_token` se cachea en BD con `token_expires_at`. Refresh solo si venció o falta <5 min
- Refresh actualiza `access_token` + `token_expires_at` en la misma transacción, commit inmediato
- Race condition aceptada: dos requests concurrentes pueden refrescar, ambos tokens funcionan
- URLs dinámicas por región: `https://www.zohoapis.{region}/crm/v2` y `https://accounts.zoho.{region}/oauth/v2/token`
- Services de Zoho reciben `ZohoConnection` como parámetro, no `tenant_id`

---

## Webhook entrante — manejo de errores

- `phone_number_id` sin canal activo → log warning, retornar sin procesar. Router responde 200 OK a Meta (nunca retornar error, Meta reintenta agresivo)
- Sync Zoho falla (network, 401, timeout) → guardar mensaje con `contact.zoho_contact_id = None`. No perder mensajes por culpa de Zoho
- Cada mensaje es transacción independiente
- Idempotencia: verificar `whatsapp_message_id` duplicado antes de insertar (Meta reenvía si no respondemos 200 rápido)
- Webhooks externos (Meta, Zoho, otros proveedores) se reciben como dict
  libre, no como Pydantic model en el router. El router siempre responde
  2xx al proveedor. Validación estricta ocurre dentro del service con
  try/except.

---

## Flujo de trabajo

1. Decisiones de diseño en Claude.ai, ejecución en Claude Code
2. Prompts a Claude Code referencian "siguiendo CLAUDE.md" en lugar de repetir reglas
3. Si Claude Code detecta que una regla contradice al código actual, o encuentra un caso no cubierto: parar y pedir clarificación. No improvisar. CLAUDE.md es fuente de verdad — si hay gap, se actualiza el archivo
4. Al terminar una tarea, resumen de 2-3 oraciones: qué cambió y resultado. Sin desglosar archivo por archivo salvo pedido explícito
5. Output de Claude Code se revisa antes de aceptar/commitear
6. Sin apuros — cada feature se diseña antes de implementar

---

## Trabajando con Claude Code

**Plan Mode obligatorio** para tareas que tocan más de un archivo. Activar con `Shift + Tab`. Proponer plan escrito antes de editar.

**Ejecución directa permitida** solo para: fixes chicos (1 archivo, <50 líneas), renombrar variables, agregar logs/docstrings, ejecutar diseños ya validados en Claude.ai.

**Revisión de diffs — qué rechazar automáticamente:**

- Queries sin filtro de `tenant_id`
- Timestamps sin timezone o `datetime.utcnow()`
- `except Exception: pass` que silencia errores
- Nombres autogenerados de constraints/FKs
- `.json()` sin verificar contenido
- Hardcoding de IDs (tenant, channel)
- Diff >150 líneas en un archivo — pedir partir en cambios más chicos

**Cuándo volver a Claude.ai:**

- Claude Code pregunta entre alternativas que afectan arquitectura
- Error cuya causa sospechás que es problema de diseño más profundo
- Acumulando deuda técnica por apuro

**Comandos útiles:** `/clear` limpia contexto, `/compact` resume sesión, "think hard" / "ultrathink" en prompt aumenta thinking budget.

---

## Retomar después de pausa

1. Leer `HANDOFF.md` primero
2. `git log --oneline -20` para últimos commits
3. Verificar entorno: `docker ps`, venv activado, `alembic current`
4. Abrir Claude Code en la raíz del proyecto (lee CLAUDE.md automático)
5. Prompt del próximo paso está en `docs/`
6. Si volvés a Claude.ai: subir versión actual de CLAUDE.md y HANDOFF.md al project knowledge primero
