# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto. Leer esto primero al retomar después de una pausa.

**Última actualización:** cierre de Fase 4 Bloque A.4.a + reestructuración de documentación.

---

## Fase y bloque actual

**Fase 4 — Multi-tenant + Multi-channel + Onboarding**

Progreso del Bloque A:

- [x] A.1 Modelos y enums
- [x] A.2 Migración Alembic
- [x] A.3 Seed del tenant inicial
- [x] A.4.a Refactor services/zoho.py
- [ ] **A.4.b Refactor services/whatsapp.py** ← próximo paso
- [ ] A.4.c Refactor routers + panel

Bloques pendientes de Fase 4: B (Meta Embedded Signup), C (Zoho OAuth real), D (Registro).

Detalle completo del roadmap en `docs/roadmap.md`.

---

## Estado BD local

- Alembic head: `59662106973d` (fase 4 bloque a - schema multi-tenant)
- 7 tablas: `tenants`, `users`, `channels`, `contacts`, `zoho_connections`, `conversations`, `messages`
- 4 enums PostgreSQL: `tenant_plan`, `tenant_status`, `user_role`, `conversation_status` (valores lowercase)

### IDs del seed (BD local — se regeneran si reseteás Docker)

| Entidad              | ID                                     |
| -------------------- | -------------------------------------- |
| Tenant "Dev Tech Py" | `b9fab3be-a6d5-41b5-a36d-6c38729bc7e5` |
| Admin user           | `db543ea7-12b5-4b4f-8472-4384c1c98aa6` |
| Channel              | `6a119210-2662-4d72-993b-a1e5347f0f7b` |
| Zoho Connection      | `39f6764b-0eac-45c8-b75e-677d4eb9d575` |

### Estado Zoho

Access token real refrescado en A.4.a. Ya no es `SEEDED_PLACEHOLDER`.

Hay un contacto de prueba en Zoho CRM real ("Test Contact SiuChat", ID `7212255000000694001`) creado durante A.4.a — conviene borrarlo.

---

## Archivos creados/modificados en Bloque A

**Creados:** `app/enums.py`, `scripts/__init__.py`, `scripts/seed_initial_tenant.py`, `scripts/test_zoho_refresh.py` (en .gitignore), migración alembic.

**Modificados:** `app/models.py`, `app/services/zoho.py`, `app/config.py` (extra=ignore + ZOHO_BASE_URL eliminado).

**No modificados todavía** (los toca A.4.b y A.4.c):

- `app/services/whatsapp.py`
- `app/routers/*.py`
- `app/static/index.html`

---

## Variables de entorno (.env local)

Referencia rápida de qué variables están en `.env`. Las marcadas como "solo seed" pueden eliminarse una vez que Bloques B, C, D estén completos.

```
# Base de datos
DATABASE_URL=postgresql://admin:admin123@localhost:5432/whatsapp_zoho

# WhatsApp / Meta — en BD después de A.4.b
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=1056198860910219
WHATSAPP_BUSINESS_ACCOUNT_ID=1272036547749246   (solo seed)
WHATSAPP_DISPLAY_PHONE_NUMBER=+595983275273     (solo seed)
WHATSAPP_DISPLAY_NAME=Dev Tech Py               (solo seed)
WHATSAPP_VERIFY_TOKEN=...
WHATSAPP_API_VERSION=v19.0

# Zoho — credenciales del Self Client de Dev Tech Py (transitorias)
ZOHO_CLIENT_ID=...                              (app OAuth global — ver design-decisions.md)
ZOHO_CLIENT_SECRET=...                          (idem)
ZOHO_REFRESH_TOKEN=1000.bf62e2cbefb16d6...     (solo seed — ya en BD)
ZOHO_ORG_ID=912447340                           (solo seed)
ZOHO_REGION=com                                 (solo seed)

# Seed
SEED_TENANT_NAME=Dev Tech Py
SEED_ADMIN_EMAIL=sacst.py@gmail.com
SEED_ADMIN_NAME=Sergio
```

**Nota:** `ZOHO_BASE_URL` fue eliminado — ahora se arma dinámico desde `region` en BD.

---

## Arranque del entorno local

```bash
# 1. Postgres en Docker
docker start <container_name>
# o: docker compose up -d

# 2. Verificar
docker ps

# 3. Venv (Windows)
venv\Scripts\activate

# 4. Alembic en head
alembic current    # debe mostrar 59662106973d

# 5. FastAPI
uvicorn app.main:app --reload

# 6. (Opcional) ngrok para webhook real
ngrok http 8000
```

---

## Próximo paso concreto

**A.4.b — Refactor de `app/services/whatsapp.py`.**

Prompt listo en `docs/prompt-a4b.md`.

Secuencia:

1. Confirmar `git status` limpio
2. Abrir Claude Code en el repo
3. Activar **Plan Mode** (Shift+Tab)
4. Pegar prompt y revisar plan antes de aprobar
5. Revisar diffs archivo por archivo

Después de A.4.b: ver `docs/prompt-a4c-outline.md` para armar el prompt A.4.c en Claude.ai.

---

## Documentación del proyecto

| Archivo                        | Para qué                      | Frecuencia de cambio             |
| ------------------------------ | ----------------------------- | -------------------------------- |
| `CLAUDE.md`                    | Reglas activas del proyecto   | Bajo                             |
| `HANDOFF.md` (este)            | Estado operativo actual       | Alto                             |
| `docs/roadmap.md`              | Fases y bloques               | Bajo                             |
| `docs/design-decisions.md`     | Historial de por qué          | Bajo                             |
| `docs/common-patterns.md`      | Patrones de código            | Bajo                             |
| `docs/claude-code-workflow.md` | Guía operativa de Claude Code | Bajo                             |
| `docs/prompt-a4b.md`           | Prompt listo para A.4.b       | Cada bloque nuevo                |
| `docs/prompt-a4c-outline.md`   | Outline (no prompt completo)  | Se completa cuando A.4.b termina |

---

## Pendientes no bloqueantes

- Borrar "Test Contact SiuChat" (ID 7212255000000694001) de Zoho CRM real
- Al cerrar Fase 4: evaluar qué variables de `.env` pueden eliminarse (ya viven en BD)
- En Bloque B: reemplazar credenciales del Self Client por app OAuth "SiuChat" central
- Antes de Fase 7: buscar 1-2 clientes externos reales
