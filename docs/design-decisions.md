# docs/design-decisions.md — Historial de decisiones de diseño

Este archivo contiene el razonamiento detrás de las decisiones que hoy son reglas en `CLAUDE.md`. Es referencia para entender el **por qué**, no para escribir código.

Claude Code no carga este archivo automáticamente. Si necesitás referenciarlo, hacelo explícito en un prompt.

---

## Fase 4 — Arquitectura multi-tenant

### `contacts` como tabla propia, separada de `conversations`

**Decisión:** `contacts` es tabla separada. `conversations` referencia vía FK `contact_id`.

**Por qué:** En el MVP single-tenant, `Conversation` tenía `contact_number`, `contact_name`, `zoho_contact_id` directo. Funcionaba para 1:1. En multi-tenant no se sostiene:

- Una empresa con dos canales (ventas + soporte) puede tener al mismo cliente hablando por los dos → datos duplicados en conversations.
- Ficha de contacto (Fase 7) requiere "dame el historial de todas las conversaciones de Juan" — con solo `contact_number` se rompe si el cliente cambia de número.
- Sync Zoho en Fase 9 es contacto ↔ contacto, no conversación ↔ contacto.

Hacer esto en Fase 4 era prácticamente gratis (vaciábamos las tablas igual). Hacerlo después sería migración de datos dolorosa.

### Unicidad: `UNIQUE (channel_id, contact_id)` en conversations

**Decisión:** Un contacto tiene máximo una conversación por canal. El `tenant_id` queda implícito porque `channel_id` → `tenant_id` vía FK.

**Alternativas descartadas:**
- `UNIQUE (tenant_id, contact_number)` — un contacto = una conversación por empresa. Muy permisivo si la empresa tiene múltiples canales.
- `UNIQUE (tenant_id, channel_id, contact_number)` — redundante, porque `channel_id` ya determina `tenant_id`.

El `tenant_id` se denormaliza **aparte** en `conversations` y `messages`, no por el constraint sino por performance de queries (evitar JOIN con `channels` en listados).

### `users` mínima en Fase 4 (sin flow de login)

**Decisión:** Crear tabla `users` con schema completo en Fase 4, aunque el login funcional con Zoho sea de Fase 5.

**Por qué:** Varias tablas necesitan FK a users (`channels.created_by`, `zoho_connections.created_by`). Diferir users a Fase 5 obligaría a hacer migración de datos posterior para agregar FKs NOT NULL. Crearla vacía ahora cuesta casi nada.

Consecuencia: el seed script crea el primer user admin manualmente en Fase 4. El login real popula `zoho_user_id` en primer login de Fase 5.

### `users.zoho_user_id` nullable

**Decisión:** El campo es nullable.

**Por qué:** SiuChat puede evolucionar a mini-CRM independiente de Zoho. Si hicieramos NOT NULL, cada nuevo user obligaría a tener cuenta Zoho. Dejarlo nullable abre la puerta a usuarios sin Zoho en el futuro.

Partial unique index: `UNIQUE (tenant_id, zoho_user_id) WHERE zoho_user_id IS NOT NULL`. Así múltiples NULLs coexisten, pero valores reales no se duplican.

### Sin `created_by` en `tenants`

**Decisión:** No hay FK `tenants.created_by` → users.

**Por qué:** Dependencia circular. Para crear un tenant necesitaríamos un user, pero users tiene `tenant_id` NOT NULL. Resolver con "tenant.created_by nullable temporal + update después" genera un campo semánticamente nullable que no debería serlo.

Alternativa elegida: para saber quién creó un tenant, query `users WHERE tenant_id = ? AND role = 'admin' ORDER BY created_at LIMIT 1`. Menos explícito pero evita el huevo-gallina.

### `zoho_connections.tenant_id` UNIQUE (1:1 tenant ↔ Zoho)

**Decisión:** Un tenant tiene máximo una conexión Zoho.

**Por qué:** Caso "una empresa quiere conectar 2 orgs Zoho distintos" es excepcional y no lo diseñamos para Fase 4. Si aparece, se revisará. Mantener 1:1 simplifica queries y la UX del panel.

### `channels.phone_number_id` y `zoho_connections.org_id` UNIQUE global

**Decisión:** Unicidad global, no por tenant.

**Por qué:** Meta asigna `phone_number_id` único en toda su plataforma; Zoho igual con `org_id`. Si dos tenants intentan registrar el mismo recurso, es error (o intento malicioso). La BD rechaza sola.

### `region` de Zoho como código, no URL completa

**Decisión:** Guardar `com`, `eu`, `in`, `com.au`, `jp`. El service arma `https://www.zohoapis.{region}/crm/v2`.

**Por qué:** Guardar URL completa duplica información. Si Zoho cambia el formato, toca modificar filas. Código + función helper es más mantenible.

### `last_message_at` denormalizado en conversations

**Decisión:** Actualizar el campo en cada message inserted, en el mismo commit.

**Por qué:** El panel ordena conversaciones por última actividad. Calcular `MAX(messages.timestamp)` por cada fila en cada listado escala mal. Denormalizar cuesta 1 UPDATE por mensaje, pero hace el listado ~30x más rápido en producción.

---

## Fase 4 — Decisiones operativas

### Tokens en texto plano hasta Fase 5

**Decisión:** `channels.token`, `zoho_connections.access_token`, `zoho_connections.refresh_token` en texto plano en BD.

**Por qué:** Encriptar con Fernet es simple pero requiere `ENCRYPTION_KEY` en env, manejo de rotación, migración de tokens existentes. Fase 4 ya es grande. Railway encripta en reposo a nivel disco — el riesgo residual es "alguien con acceso a la BD", que es control de acceso, no de encriptación.

Se encripta en Fase 5 como sub-bloque dedicado, antes de escalar número de tenants.

### Desarrollo local-first con Docker + ngrok

**Decisión:** Toda Fase 4 se desarrolla contra Postgres en Docker local, webhook via ngrok. Deploy a Railway solo post-validación.

**Por qué:** Refactor destructivo (cambios a tablas existentes, reescritura de services). Iterar en Railway es lento, riesgoso, y consume la ventana de mensajes de Meta para testeo. Local es instantáneo y reseteable.

### Sync con Zoho sincrónico (no async)

**Decisión:** Webhook entrante llama a Zoho y espera respuesta antes de commitear el mensaje.

**Por qué:** Async requiere queue (Redis/RabbitMQ), workers, manejo de errores distribuido. Fase 4 no lo justifica. Volumen actual (1 tenant) no presiona el timeout de Meta (20s). Si aparece el problema, se migra a async en Fase 8.

Fallback: si Zoho falla, se guarda el mensaje con `zoho_contact_id = None`. No perder mensajes.

### `app/config.py` Settings con `extra="ignore"`

**Decisión:** Settings ignora variables de `.env` que no están declaradas como campos.

**Por qué:** El seed usa variables como `SEED_TENANT_NAME`, `ZOHO_ORG_ID`, `WHATSAPP_BUSINESS_ACCOUNT_ID` que no son runtime de la app. Declararlas en Settings ensucia la clase y obliga a setearlas en Railway aunque no se usen. `extra="ignore"` permite que `.env` tenga variables adicionales sin romper Settings.

Riesgo aceptado: typos en nombres de variables declaradas no se detectan en el `.env`. Si el código intenta usar una variable no declarada, falla con error claro igualmente.

### `ZOHO_BASE_URL` eliminado del `.env`

**Decisión:** Removido. La URL se arma dinámicamente desde `region`.

**Por qué:** Duplicaba información. La región determina la URL base completamente. Con la URL hardcoded en `.env`, un tenant de otra región requeriría override manual.

### Credenciales OAuth Zoho actuales son transitorias

**Decisión:** `ZOHO_CLIENT_ID` y `ZOHO_CLIENT_SECRET` actuales son del **Self Client** de Dev Tech Py.

**Por qué:** Para desarrollo de Fase 4 (un tenant), el Self Client alcanza. Para multi-tenant real (Fase 4 Bloque B), hay que crear una app OAuth "SiuChat" central en Zoho Developer Console con URL de callback. El Self Client NO sirve para que otros tenants se conecten.

Reemplazo está planificado en Bloque B.

### Interface de services Zoho: reciben `ZohoConnection`, no `tenant_id`

**Decisión:** `zoho_service.sync_contact(db, zoho_conn, phone, name)` en lugar de `(db, tenant_id, phone, name)`.

**Por qué:**
- El caller (router o webhook handler) ya tiene resuelto el tenant y probablemente el `ZohoConnection` también. Volver a hacer la query en el service es trabajo duplicado.
- Testing más simple: mock de `ZohoConnection` directo, no requiere DB.
- Más explícito: leer la firma del service dice qué recursos usa.

---

## Fase 4 — Cambios al roadmap original

### Rate limiting movido de Fase 8 a Fase 6

**Decisión:** Rate limiting del webhook entrante en Fase 6, no Fase 8.

**Por qué:** Con 2-3 tenants activos y Meta mandando bursts (reintento de webhooks, campañas), el backend puede caerse. Fase 8 es demasiado tarde. Fase 6 ya agrega tiempo real (WebSockets) y cambia la carga del backend, es momento natural para agregar rate limiting.

### Frontend SPA movido a Fase 5

**Decisión:** Migrar de vanilla JS a SPA (React/Vue/Svelte) en Fase 5, no antes ni después.

**Por qué:** Fase 4 ya es gigante, no mezclar con refactor de frontend. Fase 5 agrega login + roles + rutas protegidas — el frontend necesita sesiones y estado complejo, donde vanilla JS ya no escala. Hacerlo antes de Fase 6 (WebSockets) evita reescribir la lógica de WS dos veces.

### Tabla `users` adelantada a Fase 4

**Decisión:** Schema de `users` en Fase 4, login funcional en Fase 5.

**Por qué:** FKs `channels.created_by` y `zoho_connections.created_by` necesitan users existente desde el día uno. Ver decisión de `users` más arriba.

### Contacto externo real antes de Fase 7

**Decisión (pendiente):** Buscar 1-2 clientes externos (aunque gratis) antes de terminar Fase 7.

**Por qué:** El cliente actual (Dev Tech Py = propio negocio) no da señal real. Un cliente externo fuerza a resolver problemas que el "yo mismo como cliente" evita naturalmente.

No es acción inmediata. Anotado para revisar en cierre de Fase 6.

---

## Cómo agregar nuevas decisiones acá

Cuando se tome una decisión que merezca ir a `CLAUDE.md` como regla, agregarla también acá con su razonamiento. Plantilla:

```
### [Nombre corto de la decisión]

**Decisión:** [Qué se decidió, una oración]

**Por qué:** [Contexto, alternativas consideradas, justificación de la elección]
```
