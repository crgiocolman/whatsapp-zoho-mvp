import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import nullslast
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import ConversationStatus
from app.models import Channel, Contact, Conversation, Message, ZohoConnection
from app.schemas import WhatsAppContact, WhatsAppMessage, WhatsAppWebhookPayload
from app.services import zoho as zoho_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_contact_name(
    phone_number: str,
    contacts: Optional[list[WhatsAppContact]],
) -> Optional[str]:
    if not contacts:
        return None
    for c in contacts:
        if c.wa_id == phone_number:
            return c.profile.name if c.profile else None
    return None


def _find_or_create_contact(
    db: Session,
    tenant_id: UUID,
    phone_number: str,
    name: Optional[str],
    zoho_conn: Optional[ZohoConnection],
) -> Contact:
    contact = (
        db.query(Contact)
        .filter(Contact.tenant_id == tenant_id, Contact.phone_number == phone_number)
        .first()
    )

    if contact:
        updated = False
        if contact.name is None and name is not None:
            contact.name = name
            updated = True
        if contact.zoho_contact_id is None and zoho_conn is not None:
            zoho_id = zoho_service.sync_contact(db, zoho_conn, phone_number, name)
            if zoho_id:
                contact.zoho_contact_id = zoho_id
                updated = True
        if updated:
            db.flush()
        return contact

    zoho_contact_id: Optional[str] = None
    if zoho_conn is not None:
        zoho_contact_id = zoho_service.sync_contact(db, zoho_conn, phone_number, name)

    contact = Contact(
        tenant_id=tenant_id,
        phone_number=phone_number,
        name=name,
        zoho_contact_id=zoho_contact_id,
    )
    db.add(contact)
    db.flush()
    return contact


def _find_or_create_conversation(
    db: Session,
    tenant_id: UUID,
    channel_id: UUID,
    contact_id: UUID,
) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.channel_id == channel_id, Conversation.contact_id == contact_id)
        .first()
    )
    if conversation:
        return conversation

    conversation = Conversation(
        tenant_id=tenant_id,
        channel_id=channel_id,
        contact_id=contact_id,
        status=ConversationStatus.OPEN,
    )
    db.add(conversation)
    db.flush()
    return conversation


# ---------------------------------------------------------------------------
# Incoming webhook
# ---------------------------------------------------------------------------

def process_incoming_message(db: Session, payload: WhatsAppWebhookPayload) -> None:
    if not payload.entry:
        return

    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            phone_number_id = value.metadata.phone_number_id

            channel = (
                db.query(Channel)
                .filter(
                    Channel.phone_number_id == phone_number_id,
                    Channel.active.is_(True),
                )
                .first()
            )
            if not channel:
                logger.warning(
                    "Webhook recibido para phone_number_id=%s sin canal activo", phone_number_id
                )
                continue

            if not value.messages:
                continue

            for message in value.messages:
                _process_single_message(db, channel, message, value.contacts)


def _process_single_message(
    db: Session,
    channel: Channel,
    message: WhatsAppMessage,
    contacts: Optional[list[WhatsAppContact]],
) -> None:
    existing = (
        db.query(Message)
        .filter(Message.whatsapp_message_id == message.id)
        .first()
    )
    if existing:
        return

    if message.type != "text":
        logger.warning(
            "Tipo de mensaje no soportado todavia: %s. "
            "whatsapp_message_id=%s, phone_number=%s. "
            "Soporte multimedia se implementa en Fase 8.",
            message.type,
            message.id,
            message.from_number,
        )
        return

    phone_number = message.from_number
    contact_name = _extract_contact_name(phone_number, contacts)
    tenant_id = channel.tenant_id

    zoho_conn = (
        db.query(ZohoConnection)
        .filter(ZohoConnection.tenant_id == tenant_id)
        .first()
    )
    if zoho_conn is None:
        logger.warning(
            "No zoho_connection para tenant_id=%s, procesando sin sync Zoho", tenant_id
        )

    try:
        contact = _find_or_create_contact(db, tenant_id, phone_number, contact_name, zoho_conn)
        conversation = _find_or_create_conversation(db, tenant_id, channel.id, contact.id)

        # Usar timestamp de procesamiento para consistencia de orden en el panel.
        # El timestamp original de Meta (message.timestamp) se preservará en Fase 6
        # cuando se agregue messages.meta_timestamp junto con messages.status.
        timestamp_dt = datetime.now(timezone.utc)
        body = message.text.body if message.text else None

        message_obj = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            direction="inbound",
            body=body,
            whatsapp_message_id=message.id,
            timestamp=timestamp_dt,
        )
        conversation.last_message_at = timestamp_dt
        db.add(message_obj)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(
            "Error procesando mensaje entrante phone=%s wamid=%s channel_id=%s: %s",
            phone_number,
            message.id,
            channel.id,
            e,
        )


# ---------------------------------------------------------------------------
# Outgoing message
# ---------------------------------------------------------------------------

def send_message(
    db: Session,
    channel: Channel,
    to_phone: str,
    text: str,
) -> Optional[Message]:
    if not channel.active:
        logger.warning("Intento de envío por canal inactivo channel_id=%s", channel.id)
        return None

    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
        f"/{channel.phone_number_id}/messages"
    )
    try:
        response = httpx.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "text",
                "text": {"body": text},
            },
            headers={
                "Authorization": f"Bearer {channel.token}",
                "Content-Type": "application/json",
            },
        )

        if not response.text:
            logger.error(
                "send_message: respuesta vacía de WhatsApp API channel_id=%s to=%s",
                channel.id,
                to_phone,
            )
            return None
        if not response.is_success:
            logger.error(
                "send_message: error de WhatsApp API status=%s body=%s channel_id=%s to=%s",
                response.status_code,
                response.text,
                channel.id,
                to_phone,
            )
            return None

        data = response.json()
        messages_list = data.get("messages") or []
        whatsapp_message_id = messages_list[0].get("id") if messages_list else None

        tenant_id = channel.tenant_id
        zoho_conn = (
            db.query(ZohoConnection)
            .filter(ZohoConnection.tenant_id == tenant_id)
            .first()
        )

        contact = _find_or_create_contact(db, tenant_id, to_phone, None, zoho_conn)
        conversation = _find_or_create_conversation(db, tenant_id, channel.id, contact.id)

        now = datetime.now(timezone.utc)
        message_obj = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            direction="outbound",
            body=text,
            whatsapp_message_id=whatsapp_message_id,
            timestamp=now,
        )
        conversation.last_message_at = now
        db.add(message_obj)
        db.commit()
        return message_obj

    except Exception as e:
        db.rollback()
        logger.error("Error enviando mensaje a %s channel_id=%s: %s", to_phone, channel.id, e)
        return None


# ---------------------------------------------------------------------------
# Read queries
# ---------------------------------------------------------------------------

def get_conversations(db: Session, tenant_id: UUID) -> list[dict]:
    rows = (
        db.query(Conversation, Contact, Channel)
        .join(Contact, Conversation.contact_id == Contact.id)
        .join(Channel, Conversation.channel_id == Channel.id)
        .filter(Conversation.tenant_id == tenant_id)
        .order_by(nullslast(Conversation.last_message_at.desc()))
        .all()
    )

    result = []
    for conv, contact, channel in rows:
        result.append(
            {
                "id": conv.id,
                "status": conv.status,
                "last_message_at": conv.last_message_at,
                "created_at": conv.created_at,
                "contact": {
                    "phone_number": contact.phone_number,
                    "name": contact.name,
                    "zoho_contact_id": contact.zoho_contact_id,
                },
                "channel": {
                    "display_phone_number": channel.display_phone_number,
                    "display_name": channel.display_name,
                },
            }
        )
    return result


def get_conversation_messages(
    db: Session,
    tenant_id: UUID,
    conversation_id: UUID,
) -> Optional[list[Message]]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        .first()
    )
    if not conversation:
        return None

    return (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_id,
        )
        .order_by(Message.timestamp.asc())
        .all()
    )
