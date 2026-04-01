from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Conversation, Message
from app.schemas import WhatsAppWebhookPayload


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
