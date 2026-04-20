# Prompt A.4.c — Outline (NO LISTO PARA USAR)

Este archivo NO es un prompt listo para Claude Code. Es el outline que vamos a completar en el chat de Claude.ai cuando A.4.b esté validado.

## Por qué outline y no prompt completo

A.4.c depende del resultado de A.4.b. Los routers se adaptan al shape exacto de los services refactorizados. Si dejamos A.4.c como prompt completo ahora, probablemente haya que reescribir mitad después.

Cuando A.4.b esté listo:
1. Volvé al chat de Claude.ai (hilo de Fase 4)
2. Pegá el output de A.4.b para que tenga contexto
3. Pedí: "armá el prompt A.4.c siguiendo este outline"

---

## Alcance esperado de A.4.c

### Archivos a modificar

- `app/routers/webhook.py` — adaptar a la nueva firma de `process_incoming_message(db, payload)` (probablemente sin cambios grandes, solo verificar)
- `app/routers/conversations.py` — ahora recibe `tenant_id` (de dónde? ver decisión de abajo) y lo pasa a los services
- `app/routers/messages.py` — POST /messages/send ahora necesita resolver el `channel` a usar antes de llamar a `send_message(db, channel, to, text)`
- `app/static/index.html` + JS asociado — el panel debe funcionar igual pero contra la nueva API (mínimos ajustes)

### Decisiones a cerrar en Claude.ai antes del prompt

**Decisión D1 — ¿De dónde sale `tenant_id` en los endpoints del panel?**

Hoy no hay login. El panel asume que hay un solo tenant ("Dev Tech Py"). Opciones:

- **a)** Hardcodear `tenant_id` en una variable del panel JS (feo pero rápido para Fase 4)
- **b)** Endpoint nuevo `/api/current-tenant` que devuelve el único tenant activo (menos feo, pero asume single-tenant)
- **c)** Header custom `X-Tenant-Id` en cada request (preparatorio para Fase 5 cuando haya login)
- **d)** Query param `?tenant_id=...` en cada endpoint (peor)

Mi voto temporal: **opción b**, con el endpoint devolviendo el tenant del primer user admin que encuentre. Es una solución transicional hasta Fase 5.

**Decisión D2 — POST /messages/send: ¿cómo se elige el channel?**

Si el tenant tiene múltiples channels (en el futuro), el endpoint necesita saber cuál usar. Hoy con 1 channel:

- **a)** Endpoint `/messages/send` recibe `channel_id` en el body
- **b)** Endpoint usa el primer channel activo del tenant
- **c)** Endpoint recibe `conversation_id` (del cual saca el channel) en lugar de un número

Opción **c** es la más correcta: respondés a una conversación, no a un número suelto. Eso también hace que `channel_id` se derive del contexto y no haya ambigüedad.

**Decisión D3 — ¿Qué hacer con el panel HTML vanilla?**

El panel hoy tiene algunas cosas hardcodeadas (`ZOHO_ORG_ID` fue la más notable). Con los endpoints multi-tenant ajustados:

- Mínimo: que siga funcionando con single-tenant sin errores visibles
- Deseable: que el link a Zoho CRM se arme con el `zoho_contact_id` + el `org_id` del tenant actual (dinámicamente desde el endpoint `/api/current-tenant` o similar)

No invertir mucho tiempo en hacer bonito el panel — migración a SPA está en Fase 5.

### Validaciones a hacer al final de A.4.c

1. Levantar uvicorn local
2. Abrir ngrok y apuntar el webhook de Meta al endpoint local
3. Mandar un mensaje desde WhatsApp al número +595983275273
4. Verificar que:
   - Llega al webhook sin errores
   - Se crea/actualiza el contact con `zoho_contact_id` real
   - Se crea/actualiza la conversation con `last_message_at`
   - Se guarda el message en BD
   - El panel en localhost:8000/panel muestra la conversación
   - Al responder desde el panel, el mensaje outbound llega a WhatsApp
5. Hacer `SELECT` en psql para confirmar:
   ```sql
   SELECT * FROM conversations WHERE tenant_id = 'b9fab3be-a6d5-41b5-a36d-6c38729bc7e5';
   SELECT * FROM messages WHERE tenant_id = 'b9fab3be-a6d5-41b5-a36d-6c38729bc7e5' ORDER BY timestamp DESC LIMIT 10;
   ```
6. Limpiar en Zoho CRM el contacto de prueba que se haya creado

### Cosas a NO tocar en A.4.c

- No migrar el frontend a SPA (eso es Fase 5)
- No agregar login (Fase 5)
- No implementar Meta Embedded Signup (eso es Bloque B de Fase 4, siguiente después de A)
- No tocar `services/whatsapp.py` ni `services/zoho.py` ya refactorizados

### Flag para cerrar Fase 4 Bloque A

Cuando A.4.c esté validado end-to-end (mensaje entrante desde WhatsApp real llega y se muestra en el panel), el Bloque A está cerrado.

Próximos pasos después de A:
- **B** — Meta Embedded Signup
- **C** — Zoho OAuth multi-tenant real (reemplaza Self Client)
- **D** — Página de registro de tenants
