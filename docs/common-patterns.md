# docs/common-patterns.md — Patrones de código del proyecto

Patrones recurrentes en SiuChat con ejemplos. Sirve como referencia para Claude Code cuando hace falta replicar un patrón existente, y para evitar que Claude.ai regenere ejemplos de cero cada vez.

---

## Enums Python + PostgreSQL nativos

```python
# app/enums.py
from enum import Enum

class TenantPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
```

En el modelo SQLAlchemy, usar `values_callable` para persistir el `.value` (lowercase) en lugar del `.name` (UPPERCASE):

```python
from sqlalchemy import Enum as SQLEnum
from app.enums import TenantPlan

plan = Column(
    SQLEnum(
        TenantPlan,
        name="tenant_plan",
        native_enum=True,
        create_type=True,
        values_callable=lambda obj: [e.value for e in obj],
    ),
    nullable=False,
    server_default=TenantPlan.FREE.value,
)
```

---

## FK con nombre explícito

```python
tenant_id = Column(
    UUID(as_uuid=True),
    ForeignKey("tenants.id", ondelete="RESTRICT", name="fk_channels_tenant_id"),
    nullable=False,
)
```

Convenciones de nombres:
- FK: `fk_<tabla>_<columna>`
- Unique simple: `uq_<tabla>_<columna>`
- Unique compuesto: `uq_<tabla>_<col1>_<col2>`
- Índice: `ix_<tabla>_<columna>`

---

## Constraint en `__table_args__`

```python
__table_args__ = (
    UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    Index(
        "uq_users_tenant_zoho_user",
        "tenant_id",
        "zoho_user_id",
        unique=True,
        postgresql_where=text("zoho_user_id IS NOT NULL"),
    ),
    Index("ix_users_tenant_id", "tenant_id"),
)
```

Usar `__table_args__` incluso si hay un solo item (por consistencia). Si hay un solo item, va como tupla: `(UniqueConstraint(...),)` con la coma final.

---

## Timestamp con timezone

Python:
```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)  # Correcto
# datetime.utcnow()  # MAL — deprecated, devuelve naive datetime
```

SQLAlchemy:
```python
created_at = Column(
    DateTime(timezone=True),
    nullable=False,
    server_default=func.now(),
)

updated_at = Column(
    DateTime(timezone=True),
    nullable=False,
    server_default=func.now(),
    onupdate=func.now(),  # Solo lado cliente (ORM). Para DB-level, requiere trigger
)
```

---

## Parseo de timestamp de WhatsApp

Meta manda `timestamp` como string de epoch seconds (`"1729800000"`):

```python
from datetime import datetime, timezone

timestamp_int = int(message.timestamp)
timestamp_dt = datetime.fromtimestamp(timestamp_int, tz=timezone.utc)
```

---

## Find-or-create con transacción atómica

Patrón estándar para contactos, conversaciones, etc. Todo en una transacción, rollback en caso de error:

```python
def find_or_create_contact(db, tenant_id, phone_number, name=None, zoho_contact_id=None):
    contact = db.query(Contact).filter(
        Contact.tenant_id == tenant_id,
        Contact.phone_number == phone_number,
    ).first()

    if contact:
        # Actualizar si hay info nueva
        if contact.zoho_contact_id is None and zoho_contact_id:
            contact.zoho_contact_id = zoho_contact_id
        if contact.name is None and name:
            contact.name = name
        return contact

    contact = Contact(
        tenant_id=tenant_id,
        phone_number=phone_number,
        name=name,
        zoho_contact_id=zoho_contact_id,
    )
    db.add(contact)
    db.flush()  # para obtener el id sin commit
    return contact
```

El `commit()` y `rollback()` se manejan en el caller (una transacción por mensaje, no por operación):

```python
try:
    contact = find_or_create_contact(db, ...)
    conversation = find_or_create_conversation(db, ...)
    message = Message(...)
    db.add(message)
    conversation.last_message_at = message.timestamp
    db.commit()
except Exception as e:
    db.rollback()
    logger.error(f"Error procesando mensaje: {e}")
```

---

## Response con contenido opcional (Zoho)

Zoho puede retornar 204 No Content cuando no encuentra resultados. Nunca llamar `.json()` sin verificar:

```python
response = httpx.get(url, headers=headers)

if response.status_code == 204:
    return None

if not response.content:
    return None

try:
    data = response.json()
except ValueError:
    logger.warning(f"Zoho devolvió contenido no-JSON: {response.text[:200]}")
    return None

return data.get("data", [None])[0]
```

---

## Refresh de access_token Zoho

```python
def _get_valid_access_token(db: Session, zoho_conn: ZohoConnection) -> str:
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    expires_at = zoho_conn.token_expires_at
    threshold = now + timedelta(minutes=5)

    if expires_at is None or expires_at <= threshold:
        return _refresh_access_token(db, zoho_conn)

    return zoho_conn.access_token


def _refresh_access_token(db: Session, zoho_conn: ZohoConnection) -> str:
    from datetime import datetime, timezone, timedelta

    url = _get_accounts_url(zoho_conn.region)
    payload = {
        "refresh_token": zoho_conn.refresh_token,
        "client_id": settings.ZOHO_CLIENT_ID,
        "client_secret": settings.ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }

    try:
        response = httpx.post(url, data=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        zoho_conn.access_token = data["access_token"]
        zoho_conn.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=data.get("expires_in", 3600)
        )
        db.commit()
        return zoho_conn.access_token

    except Exception as e:
        db.rollback()
        logger.error(f"Error refrescando token Zoho para tenant {zoho_conn.tenant_id}: {e}")
        raise
```

---

## Query con eager loading

Para evitar N+1 en listados:

```python
from sqlalchemy.orm import joinedload

conversations = (
    db.query(Conversation)
    .options(
        joinedload(Conversation.contact),
        joinedload(Conversation.channel),
    )
    .filter(Conversation.tenant_id == tenant_id)
    .order_by(Conversation.last_message_at.desc().nullslast())
    .all()
)
```

---

## Validación multi-tenant en lectura

Doble filtro cuando se accede a sub-entidades (protección extra):

```python
def get_conversation_messages(db, tenant_id, conversation_id):
    # Primer filtro: la conversation debe pertenecer al tenant
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
    ).first()

    if not conversation:
        return None

    # Segundo filtro: messages también filtran por tenant_id denormalizado
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.tenant_id == tenant_id,
    ).order_by(Message.timestamp.asc()).all()

    return messages
```

---

## Settings con `extra="ignore"`

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    WHATSAPP_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    # ...
```

---

## Script one-shot con `load_dotenv` directo

Scripts en `scripts/` leen `.env` sin pasar por Settings (para no tener que declarar cada variable one-shot):

```python
import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED = ["SEED_TENANT_NAME", "SEED_ADMIN_EMAIL", ...]

missing = [v for v in REQUIRED if not os.getenv(v)]
if missing:
    logger.error(f"Faltan variables: {missing}")
    sys.exit(2)

env = {v: os.getenv(v) for v in REQUIRED}
```
