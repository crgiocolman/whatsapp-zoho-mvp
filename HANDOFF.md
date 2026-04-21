# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto. Leer esto primero al retomar después de una pausa.

**Última actualización:** cierre de Fase 4 Bloque A completo + decisión de avanzar con Bloque B.

---

## Fase y bloque actual

**Fase 4 — Multi-tenant + Multi-channel + Onboarding**

Progreso:

- [x] **Bloque A — Schema + seed + services** (CERRADO)
  - [x] A.1 Modelos y enums
  - [x] A.2 Migración Alembic
  - [x] A.3 Seed del tenant inicial
  - [x] A.4.a Refactor services/zoho.py
  - [x] A.4.b Refactor services/whatsapp.py
  - [x] A.4.c Refactor routers + panel + fixes finales
- [ ] **Bloque B — Meta Embedded Signup** ← próximo paso
- [ ] Bloque C — Zoho OAuth real (reemplazar Self Client)
- [ ] Bloque D — Página de registro de tenants

Detalle del roadmap en `docs/roadmap.md`.

---

## Estado validado al cierre del Bloque A

Pipeline end-to-end funcionando con 1 tenant ("Dev Tech Py"):

- Webhook Meta recibe mensajes entrantes y status updates, siempre retorna 200 OK
- Service resuelve tenant+channel por `phone_number_id` correctamente
- Find-or-create de `Contact` y `Conversation` con filtros multi-tenant
- Sync con Zoho CRM funcional (refresh on-demand de access_token)
- Panel vanilla JS lista conversaciones, muestra historial, envía respuestas
- Link a Zoho CRM desde el panel usa `zoho_org_id` dinámico del tenant
- Orden de mensajes en el panel coincide con el flujo real (timestamp de procesamiento)

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

Access token real refrescado automáticamente. No es `SEEDED_PLACEHOLDER`.

Contactos reales sincronizados en Zoho CRM durante las pruebas end-to-end (Sergio Colman, con `zoho_contact_id = 7212255000000673001`).

---

## Variables de entorno (.env local)

```
# Base de datos
DATABASE_URL=postgresql://admin:admin123@localhost:5432/whatsapp_zoho

# WhatsApp / Meta — en BD después del seed
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=1056198860910219
WHATSAPP_BUSINESS_ACCOUNT_ID=1272036547749246   (solo seed)
WHATSAPP_DISPLAY_PHONE_NUMBER=+595983275273     (solo seed)
WHATSAPP_DISPLAY_NAME=Dev Tech Py               (solo seed)
WHATSAPP_VERIFY_TOKEN=...
WHATSAPP_API_VERSION=v19.0

# Zoho — credenciales del Self Client de Dev Tech Py (transitorias, reemplazar en Bloque C)
ZOHO_CLIENT_ID=...
ZOHO_CLIENT_SECRET=...
ZOHO_REFRESH_TOKEN=1000.bf62e2cbefb16d6...     (solo seed — ya en BD)
ZOHO_ORG_ID=912447340                           (solo seed)
ZOHO_REGION=com                                 (solo seed)

# Seed
SEED_TENANT_NAME=Dev Tech Py
SEED_ADMIN_EMAIL=sacst.py@gmail.com
SEED_ADMIN_NAME=Sergio
```

`ZOHO_BASE_URL` eliminado — se arma dinámico desde `region` en BD.

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

**Bloque B — Meta Embedded Signup**

Objetivo: permitir que un segundo tenant conecte su número de WhatsApp Business desde el panel de onboarding, sin intervención manual del admin de SiuChat.

**Antes de arrancar Bloque B** — pendiente hacer en Meta Developer Console:

- Configurar la app Meta para soportar Embedded Signup
- Definir URL de callback (producción + local via ngrok)
- Revisar permisos de la app (`whatsapp_business_management`, `whatsapp_business_messaging`)
- Agregar testers si hace falta para desarrollo

**Pasos de diseño** (hacer en Claude.ai antes de prompts a Claude Code):

1. Decidir shape del endpoint callback (query params vs POST, qué datos recibe de Meta)
2. Decidir flujo del panel de onboarding: ¿nueva página? ¿dentro del panel actual?
3. Decidir cómo identificar qué tenant está haciendo el onboarding (sin login aún — puede ser temporal con session storage o query param)
4. Validar el flujo end-to-end con un segundo número WhatsApp de prueba antes de refactorizar el panel completo

**Secuencia sugerida** (a validar en Claude.ai):

- B.1 — Configuración de Meta Developer Console (fuera de código)
- B.2 — Endpoint backend que recibe callback y crea Channel
- B.3 — Página de onboarding con SDK de Meta Embedded Signup
- B.4 — Flujo end-to-end con segundo tenant de prueba

---

## Bugs conocidos / deuda técnica aceptada

- **Timestamp de Meta no se preserva**: los mensajes inbound usan `datetime.now(utc)` en el service, no el timestamp que manda Meta (`message.timestamp`). Se agregará campo `meta_timestamp` en Fase 6 junto con `messages.status`.
- **Panel HTML vanilla**: funciona para 1 tenant, no tiene login, tenant_id se resuelve via `/api/current-tenant` transicional. Migración a SPA en Fase 5.
- **Credenciales Zoho del Self Client**: solo sirven para Dev Tech Py. Reemplazar por app OAuth "SiuChat" central en Bloque C (no antes de intentar conectar otro tenant).
- **Sin tests automatizados**: todo se validó manualmente. Si algún refactor de B o C rompe algo de A, se va a descubrir corriendo flujos a mano.

---

## Documentación del proyecto

| Archivo                        | Para qué                      | Frecuencia de cambio |
| ------------------------------ | ----------------------------- | -------------------- |
| `CLAUDE.md`                    | Reglas activas del proyecto   | Bajo                 |
| `HANDOFF.md` (este)            | Estado operativo actual       | Alto                 |
| `docs/roadmap.md`              | Fases y bloques               | Bajo                 |
| `docs/design-decisions.md`     | Historial de por qué          | Bajo                 |
| `docs/common-patterns.md`      | Patrones de código            | Bajo                 |
| `docs/claude-code-workflow.md` | Guía operativa de Claude Code | Bajo                 |
| `docs/prompt-a4b.md`           | Prompt de A.4.b (histórico)   | Ya no se usa         |
| `docs/prompt-a4c-outline.md`   | Outline de A.4.c (histórico)  | Ya no se usa         |

**Nota**: los prompts `prompt-a4b.md` y `prompt-a4c-outline.md` quedan como referencia histórica. El Bloque A ya está cerrado. Para Bloque B se generará un nuevo `docs/prompt-b1.md` (o similar) cuando se diseñe el próximo paso en Claude.ai.

---

## Pendientes operativos

- [ ] Borrar "Test Contact SiuChat" (ID 7212255000000694001) de Zoho CRM real si todavía no se hizo
- [ ] Al cerrar Fase 4 completa: evaluar qué variables `WHATSAPP_*` y `ZOHO_*` del `.env` pueden eliminarse (ya viven en BD)
- [ ] En Bloque C: reemplazar credenciales del Self Client por app OAuth "SiuChat" central
- [ ] Antes de Fase 7: buscar 1-2 clientes externos reales (señal más valiosa que seguir probando con el propio negocio)

---

## Cómo retomar después de la pausa

1. Leer este archivo (HANDOFF.md) primero
2. `git log --oneline -20` para ver últimos commits
3. Verificar entorno local: `docker ps`, venv activado, `alembic current`
4. Levantar backend: `uvicorn app.main:app --reload`
5. Abrir `http://localhost:8000/panel` — debería cargar con conversaciones previas
6. Para avanzar con Bloque B: volver a Claude.ai (este chat o uno nuevo con project knowledge actualizado) y diseñar los pasos antes de tocar Claude Code

### Producción (Railway):

Tenant ID: 2b1409fa-f46c-4f6c-befc-ed449e30072c
Admin User ID: e2e3608d-e6a6-4be3-b3ff-c214e8a08ed9
Channel ID: b8d56120-0cca-467e-9a5e-f66989aa2806
Zoho Connection ID: 87467615-d803-4c66-81d5-d101970c28f4
