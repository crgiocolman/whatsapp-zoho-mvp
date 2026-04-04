import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Conversation, Message
from app.schemas import WhatsAppWebhookPayload
from app.services.zoho import sync_contact

logger = logging.getLogger(__name__)


def process_incoming_message(payload: WhatsAppWebhookPayload, db: Session):
    try:
        # Extract data from Meta payload
        if not payload.entry:
            return None

        value = payload.entry[0].changes[0].value

        messages = value.messages
        if not messages:
            return None

        contacts = value.contacts
        if not contacts:
            return None

        # Extract message data
        message_data = messages[0]
        from_number = message_data.from_number
        contact_name = contacts[0].profile.name
        body = message_data.text.body if message_data.text else None
        whatsapp_message_id = message_data.id
        timestamp_unix = int(message_data.timestamp)
        timestamp = datetime.fromtimestamp(timestamp_unix)

        # Find or create Conversation
        conversation = db.query(Conversation).filter_by(contact_number=from_number).first()

        if conversation:
            conversation.contact_name = contact_name
            conversation.updated_at = datetime.utcnow()
        else:
            conversation = Conversation(
                contact_number=from_number,
                contact_name=contact_name,
                status="open"
            )
            db.add(conversation)
            db.flush()  # Flush to get the ID before creating the message

        if not conversation.zoho_contact_id:
            zoho_contact_id = sync_contact(from_number, contact_name)
            if zoho_contact_id:
                conversation.zoho_contact_id = zoho_contact_id

        # Create Message
        message = Message(
            conversation_id=conversation.id,
            direction="inbound",
            body=body,
            whatsapp_message_id=whatsapp_message_id,
            timestamp=timestamp
        )
        db.add(message)
        db.commit()

        return message

    except (KeyError, IndexError, ValueError, TypeError) as e:
        db.rollback()
        print(f"Error procesando mensaje: {e}")
        return None


def send_message(to_number: str, body: str, db: Session) -> dict:
    try:
        response = httpx.post(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            json={
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": body},
            },
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
        )
        response.raise_for_status()

        if not response.text:
            raise ValueError("Respuesta vacía de la API de WhatsApp")
        response_data = response.json()

        # Find or create Conversation
        conversation = db.query(Conversation).filter_by(contact_number=to_number).first()
        if not conversation:
            conversation = Conversation(contact_number=to_number, status="open")
            db.add(conversation)
            db.flush()

        whatsapp_message_id = (
            response_data.get("messages", [{}])[0].get("id")
            if response_data.get("messages")
            else None
        )

        message = Message(
            conversation_id=conversation.id,
            direction="outbound",
            body=body,
            whatsapp_message_id=whatsapp_message_id,
            timestamp=datetime.utcnow(),
        )
        db.add(message)
        db.commit()

        return response_data

    except Exception as e:
        db.rollback()
        logger.error("Error enviando mensaje a %s: %s", to_number, e)
        raise
