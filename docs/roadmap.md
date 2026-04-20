# docs/roadmap.md — Roadmap de SiuChat

Este archivo es la versión texto del roadmap visual (`roadmap-siuchat.html`). Contiene las fases, bloques, objetivos y outputs esperados sin el overhead de HTML/CSS/JS.

---

## Fases completadas

- **Fase 0–3** — MVP en producción. FastAPI + PostgreSQL + Alembic + Webhook WhatsApp + Sync Zoho CRM + Panel agente vanilla JS + Deploy Railway + Token permanente Meta + App publicada + Número real `+595 983 275273`. **COMPLETADAS**.

---

## Fase 4 — Multi-tenant + Multi-channel + Onboarding (ACTUAL)

**Objetivo:** Convertir SiuChat en producto para múltiples empresas. Esta fase es la más crítica — todo lo que viene después se construye encima de ella.

**Tiempo estimado:** 6–8 semanas.

### Bloque A — Schema + seed + services (EN PROGRESO)

- **A.1** Modelos SQLAlchemy y enums multi-tenant — COMPLETADO
- **A.2** Migración Alembic aplicada, ciclo upgrade/downgrade/upgrade validado — COMPLETADO
- **A.3** Seed script `scripts/seed_initial_tenant.py` — COMPLETADO
- **A.4.a** Refactor `services/zoho.py` con credenciales por tenant + refresh on-demand — COMPLETADO
- **A.4.b** Refactor `services/whatsapp.py` para multi-tenant — PRÓXIMO PASO
- **A.4.c** Refactor de routers + ajuste mínimo del panel — PENDIENTE

### Bloque B — Meta Embedded Signup

Onboarding de canales WhatsApp para nuevos tenants:
- Flujo completo: login FB → selección negocio → selección/creación cuenta WA → callback → guardar en BD
- Implementar Meta Embedded Signup SDK en panel de onboarding
- Endpoint callback que recibe token y datos del canal
- Webhook dinámico: rutear mensajes al tenant+channel correcto por `phone_number_id`

### Bloque C — Zoho OAuth multi-tenant

Reemplazar el Self Client de Dev Tech Py por una app OAuth "SiuChat" central:
- Registrar app OAuth en Zoho Developer Console con URL de callback
- Implementar flow OAuth estándar (authorize → callback → guardar refresh_token en `zoho_connections`)
- Cada tenant autoriza con su propia cuenta Zoho

### Bloque D — Página de registro

- Formulario: nombre empresa, email del admin
- Crear tenant + primer user (role=admin)
- Post-registro: onboarding de canal (Bloque B) → conectar Zoho (Bloque C)
- Test de aislamiento: segundo tenant no puede ver datos del primero

### Output de Fase 4

Podés registrar una segunda empresa en SiuChat, conectar su número de WhatsApp via Meta Embedded Signup, y conectar su Zoho. Los mensajes de cada empresa llegan a su tenant aislado. El primer cliente sigue funcionando sin cambios.

---

## Fase 5 — Frontend SPA + Login con Zoho + Roles + Asignación

**Objetivo:** Migrar a SPA, autenticación real, múltiples usuarios por organización con permisos.

**Tiempo estimado:** 6–8 semanas.

**Por qué el frontend se migra acá:** El vanilla JS del MVP funcionó para Fase 4, pero con login, sesiones, rutas protegidas y múltiples vistas, se vuelve inmantenible. Se hace antes de Fase 6 (WebSockets) para no reescribir la lógica de tiempo real dos veces.

### Bloques

- **Migración a SPA** — Elegir framework (React/Vue/Svelte), armar proyecto con Vite, migrar panel actual
- **Encriptación de tokens** — `ENCRYPTION_KEY` + Fernet para `channels.token`, `zoho_connections.access_token`, `refresh_token`. Migración de datos existentes
- **Login con Zoho** — OAuth flow → identificar tenant → crear sesión → popular `users.zoho_user_id` en primer login → JWT/session token → proteger panel
- **Roles y permisos** — Permisos concretos por rol (admin/supervisor/agent, ya definidos en Fase 4). Admin: gestión users/canales/config. Supervisor: todas las conversaciones, reasignar. Agente: solo sus asignadas
- **Propietario de chat y asignación** — Campo `assigned_to` en conversations. Asignación manual por admin/supervisor. Regla equitativa: mensaje sin asignar → agente con menos chats activos. Auditoría básica

### Output de Fase 5

Un admin crea usuarios en su organización. Cada agente hace login con su cuenta Zoho y ve solo sus chats asignados. El supervisor ve todos. Los nuevos chats se asignan automáticamente.

---

## Fase 6 — Estados de chat + Tiempo real + Rate limiting

**Objetivo:** De un panel que recarga a una experiencia de chat real.

**Tiempo estimado:** 4–5 semanas.

### Bloques

- **Estados de chat y ventana 24hs** — Estados `open/waiting/resolved/expired`. Lógica de ventana 24hs de WhatsApp (fuera de ventana solo plantillas). Indicador visual en panel. Job periódico de expiración
- **Estados de mensajes** — Recibir webhooks de status de Meta (sent/delivered/read). Guardar en `messages.status` (campo nuevo). Mostrar en panel (✓, ✓✓, ✓✓ azul)
- **Tiempo real con WebSockets** — Arquitectura WS por tenant con reconexión automática. Push de mensajes nuevos al panel. Update de status en tiempo real. Indicador de conexión. Búsqueda por número/nombre/texto
- **Rate limiting** — En el webhook entrante, limitar requests por `phone_number_id` por segundo. Protege contra bursts de Meta (movido desde Fase 8)

### Output de Fase 6

El agente tiene el panel abierto. Cliente manda mensaje. Sin recargar, aparece en tiempo real. Ve si fue entregado y leído. Sabe si puede responder libremente o necesita plantilla.

---

## Fase 7 — Chat avanzado

**Objetivo:** Features que convierten el panel en herramienta de trabajo real.

**Tiempo estimado:** 3–4 semanas.

### Bloques

- **Responder mensaje** — Referencia al mensaje original en DB y UI (click derecho → reply). Enviar la referencia a API de Meta
- **Ficha de contacto** — Panel lateral con datos desde Zoho CRM (nombre, número, email, empresa). Historial de conversaciones anteriores. Link directo al contacto en Zoho CRM
- **Plantillas Meta** — Sincronizar plantillas aprobadas desde la cuenta de Meta del tenant. Selector en panel (obligatorio fuera de ventana 24hs). Rellenar variables antes de enviar

### Output de Fase 7

Agente responde a mensaje específico como en WhatsApp. Ve ficha completa con datos Zoho. Si ventana 24hs cerrada, selecciona plantilla aprobada y la envía con variables.

---

## Fase 8 — Multimedia + UX

**Objetivo:** Pulido — de funcional a placentero de usar.

**Tiempo estimado:** 3–4 semanas.

### Bloques

- **Mensajes multimedia** — Tipos soportados (imagen, audio, video, documento). Storage: S3 o Railway volume. Recibir: descargar de Meta, guardar, mostrar en panel. Enviar: upload desde panel → API Meta. Previsualización inline (imagen, player de audio, documento con nombre/tamaño)
- **Carga progresiva** — Paginación del GET messages — cargar últimos N al abrir. Scroll arriba → cargar bloque anterior sin perder posición
- **Notificaciones push** — Web Push API o servicio externo (OneSignal/Firebase). Notificación cuando llega mensaje aunque panel cerrado. Configurable por usuario (silenciar)

### Output de Fase 8

Agente recibe notificación push en celular. Abre panel, ve imágenes y archivos inline. En conversaciones largas, scroll carga mensajes anteriores sin perder contexto.

---

## Fase 9 — Sync avanzado + Auditoría + Suscripciones

**Objetivo:** Escala y negocio.

**Tiempo estimado:** 4–5 semanas.

### Bloques

- **Sync avanzado Zoho CRM** — Webhook de Zoho → cambio de owner en Zoho actualiza `assigned_to` en SiuChat. Y viceversa. Manejo de conflictos cuando ambos cambian simultáneamente
- **Auditoría y métricas** — Dashboard para supervisores: chats por agente, tiempo promedio de respuesta, chats resueltos. Log de acciones (asignación, reasignación, resolución). Exportación CSV/PDF
- **Suscripciones** — Planes Free/Pro/Business con límites (conversaciones, agentes, canales). Integración Stripe o MercadoPago. Aplicación automática de límites por plan

### Output de Fase 9

Cambio de owner en Zoho → SiuChat reasigna chat automáticamente. Supervisor ve métricas del equipo. Tenants pagan por plan. SiuChat es un negocio.

---

## Fase Opcional — IA + Zoho Books + RAG

Upsell premium, no core. Se activa si el cliente lo pide.

### Posibles bloques

- Toggle IA por tenant
- Sugerencias de respuesta con Claude (agente decide si enviar)
- Modo autónomo opcional (IA responde fuera de horario)
- RAG por tenant — base de conocimiento del negocio
- Zoho MCP — explorar para simplificar integraciones
- Zoho Books — verificar facturas pendientes del contacto, resumen de cuenta en ficha
