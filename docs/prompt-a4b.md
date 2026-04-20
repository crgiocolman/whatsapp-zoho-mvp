# Prompt A.4.b — Refactor services/whatsapp.py para multi-tenant

Este prompt es el siguiente paso concreto del proyecto. Está listo para pegar a Claude Code.

## Cómo usarlo

1. Abrí Claude Code en el directorio del proyecto
2. Verificá que el repo está limpio: `git status`
3. Activá **Plan Mode** con `Shift + Tab`
4. Pegá el prompt completo (todo lo que está entre las dos líneas `---` de abajo)
5. Revisá el plan antes de aprobar
6. Claude Code va a ejecutar en chunks — revisá cada diff antes de aceptar
7. Al final, corré las validaciones indicadas

**NO ejecutes este prompt en modo auto — las reglas multi-tenant son demasiado críticas para dejar que Claude Code decida sin plan previo.**

---

# Tarea: Fase 4 Bloque A.4.b — Refactor de services/whatsapp.py para multi-tenant

Siguiendo las reglas del CLAUDE.md del proyecto SiuChat, necesito refactorizar `app/services/whatsapp.py` para que funcione con la arquitectura multi-tenant: resolver tenant+channel por `phone_number_id` del webhook, find-or-create del contact (tabla separada), find-or-create de la conversation con los FKs nuevos, y sync con Zoho por tenant.

## Contexto

Ya completamos A.1 (modelos), A.2 (migración), A.3 (seed) y A.4.a (refactor de zoho.py). La BD tiene el tenant "Dev Tech Py" con su channel y zoho_connection. El service `zoho.py` ya funciona con la nueva interface que recibe `ZohoConnection`.

**El webhook entrante** (via `routers/webhook.py`) llama a `process_incoming_message()` de este service con el payload de Meta. El service debe identificar el canal correcto, procesar el mensaje en el tenant correspondiente, y persistir todo correctamente.

## Decisiones arquitectónicas ya tomadas (NO revisar, implementar)

1. **Sync con Zoho es sincrónico** — primero Zoho, después guardar en BD
2. **Si Zoho falla** (network, 401, etc.) → guardar el mensaje igual con `contact.zoho_contact_id = None`. No perder mensajes entrantes por culpa de Zoho
3. **Si el channel no existe** (phone_number_id no coincide con ningún registro) → log warning y retornar sin procesar. El router debe responder 200 OK a Meta igual para evitar reintentos agresivos
4. **Orden de operaciones en webhook entrante**: channel → tenant (del channel) → zoho_conn (del tenant) → sync contact en Zoho → find-or-create contact en BD → find-or-create conversation → insert message
5. **`tenant_id` denormalizado** en conversations y messages — responsabilidad del service que coincida con el tenant del channel
6. **`last_message_at` en conversation** — actualizar al timestamp del mensaje en el mismo commit
7. **Idempotencia**: si ya existe un `Message` con el mismo `whatsapp_message_id`, no hacer nada (Meta reenvía webhooks si no respondemos 200 rápido)

## Alcance exacto de esta tarea

1. Reescribir `app/services/whatsapp.py` completo
2. **NO tocar** `app/routers/*` (eso es A.4.c)
3. **NO tocar** `app/services/zoho.py` (ya está hecho en A.4.a)
4. **NO tocar** el panel HTML en `app/static/`
5. **NO tocar** `app/models.py`, `app/schemas.py`, `app/enums.py`

## Reglas obligatorias

- Seguir CLAUDE.md: `logger` no `print`, `db.rollback()` en except, schemas Pydantic ya existen (`WhatsAppWebhookPayload`)
- Un solo commit por mensaje procesado. Si algo falla a mitad, rollback de esa transacción
- Todos los timestamps timezone-aware con `datetime.now(timezone.utc)` — nunca `datetime.utcnow()` (deprecated)
- Toda query filtra por tenant_id, channel_id o contact_id según corresponda — nunca queries "globales"
- Usar `httpx` para HTTP externo (ya es la dependencia del proyecto)
- Nunca llamar `.json()` sin verificar que el response tiene contenido (204 o body vacío)

## Estructura del nuevo service

### Imports esperados

```python
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import ConversationStatus
from app.models import Channel, Contact, Conversation, Message, ZohoConnection
from app.schemas import WhatsAppWebhookPayload, WhatsAppMessage, WhatsAppContact
from app.services import zoho as zoho_service

logger = logging.getLogger(__name__)
```

### Funciones a implementar

**`process_incoming_message(db: Session, payload: WhatsAppWebhookPayload) -> None`**

Función principal llamada desde el webhook. No retorna nada — todo el trabajo es side-effect en BD.

Pseudocódigo:
```
1. Iterar payload.entry → changes → value
2. Para cada change.value:
   a. Extraer phone_number_id de value.metadata.phone_number_id
   b. Resolver channel: db.query(Channel).filter(phone_number_id=..., active=True).first()
   c. Si no existe channel → log warning "Webhook recibido para phone_number_id={} sin canal activo" y continuar al siguiente
   d. Si value.messages está vacío o None → continuar (puede ser un status update, no mensaje entrante)
   e. Iterar value.messages:
      - Llamar _process_single_message(db, channel, message, value.contacts)
3. Todo el manejo de transacciones es por mensaje (no por payload)
```

**`_process_single_message(db: Session, channel: Channel, message: WhatsAppMessage, contacts: Optional[list[WhatsAppContact]]) -> None`**

Procesa un único mensaje entrante.

Pseudocódigo:
```
1. Check duplicado: si ya existe Message.whatsapp_message_id == message.id → return (idempotencia)
2. Extraer phone_number = message.from_number
3. Extraer contact_name de contacts (buscar el contacto en la lista con wa_id == phone_number, tomar profile.name). Puede ser None.
4. Resolver tenant: tenant_id = channel.tenant_id
5. Resolver zoho_connection: db.query(ZohoConnection).filter(tenant_id=...).first()
   - Si no existe zoho_conn → log warning, pero continuar sin sync Zoho
6. Sync con Zoho (capturando excepciones):
   - Si hay zoho_conn → intentar zoho_service.sync_contact(db, zoho_conn, phone_number, contact_name)
   - Si devuelve ID → guardarlo para usar en el contact
   - Si devuelve None o lanza excepción → log warning, seguir con zoho_contact_id=None
7. Find-or-create contact:
   - db.query(Contact).filter(tenant_id=..., phone_number=...).first()
   - Si no existe → crear con tenant_id, phone_number, name=contact_name, zoho_contact_id=<del paso 6>
   - Si existe pero su zoho_contact_id es None y ahora tenemos uno → actualizarlo
   - Si existe y name era None pero ahora tenemos uno → actualizarlo
8. Find-or-create conversation:
   - db.query(Conversation).filter(channel_id=channel.id, contact_id=contact.id).first()
   - Si no existe → crear con tenant_id, channel_id, contact_id, status=ConversationStatus.OPEN
9. Parsear timestamp: int(message.timestamp) → datetime en UTC con timezone.utc
10. Crear Message:
    - conversation_id=conversation.id
    - tenant_id=tenant_id (denormalizado)
    - direction="inbound"
    - body=message.text.body si message.text else None
    - whatsapp_message_id=message.id
    - timestamp=datetime_parseado
11. Actualizar conversation.last_message_at = datetime_parseado
12. db.commit()

Si algo falla en pasos 7-12 → db.rollback() y log error con contexto (phone_number, message.id, channel.id).
```

**`send_message(db: Session, channel: Channel, to_phone: str, text: str) -> Optional[Message]`**

Envía un mensaje saliente desde un canal a un número. El caller (router) ya debe tener resuelto el channel.

Pseudocódigo:
```
1. Validar que channel.active == True, sino return None con log warning
2. POST a https://graph.facebook.com/{api_version}/{channel.phone_number_id}/messages con:
   - Headers: Authorization: Bearer {channel.token}, Content-Type: application/json
   - Body JSON: {
       "messaging_product": "whatsapp",
       "to": to_phone,
       "type": "text",
       "text": {"body": text}
     }
3. Si response no ok → log error con status y body, return None
4. Extraer whatsapp_message_id del response (messages[0].id)
5. Find-or-create contact por (channel.tenant_id, to_phone):
   - Si no existe → sync con Zoho primero (capturando excepciones), luego crear contact
   - Misma lógica que _process_single_message pasos 5-7
6. Find-or-create conversation (channel.id, contact.id)
7. Crear Message con:
   - conversation_id
   - tenant_id=channel.tenant_id
   - direction="outbound"
   - body=text
   - whatsapp_message_id=<del response>
   - timestamp=datetime.now(timezone.utc)
8. Actualizar conversation.last_message_at
9. db.commit()
10. Retornar Message creado
```

**`get_conversations(db: Session, tenant_id: UUID) -> list[dict]`**

Lista todas las conversaciones de un tenant. Retorna info enriquecida (JOIN con contact y channel).

```
1. Query con eager loading (joinedload de contact y channel):
   db.query(Conversation).filter(tenant_id=tenant_id).order_by(last_message_at DESC NULLS LAST).all()
2. Para cada conversation: construir dict con:
   - id, status, last_message_at, created_at
   - contact: {phone_number, name, zoho_contact_id}
   - channel: {display_phone_number, display_name}
3. Retornar lista
```

No necesita paginación todavía (Fase 8 la agrega).

**`get_conversation_messages(db: Session, tenant_id: UUID, conversation_id: UUID) -> Optional[list[Message]]`**

Retorna mensajes de una conversación. Valida que pertenece al tenant correcto.

```
1. Query: db.query(Conversation).filter(id=conversation_id, tenant_id=tenant_id).first()
2. Si no existe (o pertenece a otro tenant) → return None
3. Query: db.query(Message).filter(conversation_id=conversation_id, tenant_id=tenant_id).order_by(timestamp ASC).all()
4. Return lista de messages
```

**Importante**: el filtro por `tenant_id` en `Message` es protección doble (el `conversation_id` ya filtra por tenant indirectamente, pero explicitarlo con `tenant_id` denormalizado es la regla multi-tenant de CLAUDE.md).

## Detalles importantes

### Timestamps de WhatsApp

Meta manda `timestamp` como string de epoch seconds (ej: `"1729800000"`). Parseo correcto:

```python
timestamp_int = int(message.timestamp)
timestamp_dt = datetime.fromtimestamp(timestamp_int, tz=timezone.utc)
```

### Contact name del payload

El payload de Meta trae `contacts` a nivel de `value` (no de `message`). Cada contacto tiene `wa_id` y `profile.name`. Para un mensaje, buscar en la lista el contacto cuyo `wa_id` matchee el `from_number` del mensaje.

Helper sugerido:
```python
def _extract_contact_name(phone_number: str, contacts: Optional[list[WhatsAppContact]]) -> Optional[str]:
    if not contacts:
        return None
    for c in contacts:
        if c.wa_id == phone_number:
            return c.profile.name
    return None
```

### Manejo de contact.name null → not null transition

Si el contact ya existe con name=None y ahora recibimos un nombre del payload → actualizarlo. Es útil porque el primer webhook puede no traer nombre pero uno posterior sí.

### URL de la API de WhatsApp

Se arma con `settings.WHATSAPP_API_VERSION`:
```python
url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{channel.phone_number_id}/messages"
```

## Pasos de ejecución sugeridos

1. Leer el `app/services/whatsapp.py` actual para entender qué funciones existen hoy
2. Leer `app/schemas.py` para confirmar nombres exactos de campos (especialmente el alias `from` → `from_number`)
3. Leer `app/models.py` para confirmar nombres de columnas y relaciones
4. Reescribir completo `app/services/whatsapp.py`
5. Mostrar diffs

**NO corras tests ni el servidor todavía**. El webhook y los routers no están adaptados al nuevo service (eso es A.4.c). Los tests end-to-end van después del prompt siguiente.

## Validaciones a correr al final

1. `python -c "from app.services import whatsapp"` — debe importar sin errores
2. Inspeccionar que la firma de `process_incoming_message` recibe `db: Session` y `payload: WhatsAppWebhookPayload`
3. Verificar que NO hay `print()` en el archivo (usar `grep "print(" app/services/whatsapp.py`)
4. Verificar que NO hay `datetime.utcnow()` (usar `grep "utcnow" app/services/whatsapp.py`)
5. Verificar que todas las queries sobre Message/Contact/Conversation tengan filtro por tenant_id visible

## Si encontrás algo inesperado

- Si `app.schemas.WhatsAppWebhookPayload` no tiene los atributos esperados → parar y reportar
- Si `app.models.Conversation` o `Contact` tienen columnas distintas a las esperadas → parar y reportar
- Si detectás una contradicción entre este prompt y CLAUDE.md → parar y reportar

## Reglas obligatorias

- NO tocar routers, panel HTML, `services/zoho.py`, modelos, schemas
- NO correr pytest ni levantar el servidor — no funcionaría aún
- NO hacer commit
- En Plan Mode, proponer primero el plan completo antes de editar

## Output esperado

1. Lista de archivos que leíste para entender contexto (especialmente schemas.py y models.py)
2. El nuevo `app/services/whatsapp.py` completo
3. Confirmación de que las 5 validaciones pasaron
4. Lista de cualquier supuesto que hiciste sobre los schemas/models que no estaba en este prompt
5. Si encontraste inconsistencias → parar antes de seguir
