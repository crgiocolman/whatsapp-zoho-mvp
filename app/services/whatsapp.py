from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Conversation, Message


def process_incoming_message(payload: dict, db: Session):
    try:
        # Extract data from Meta payload
        entry = payload.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])

        # If no messages, return None (it's a status update or similar)
        if not messages:
            return None

        contacts = value.get("contacts", [])
        if not contacts:
            return None

        # Extract message data
        message_data = messages[0]
        from_number = message_data.get("from")
        contact_info = contacts[0]
        contact_name = contact_info.get("profile", {}).get("name")
        body = message_data.get("text", {}).get("body")
        whatsapp_message_id = message_data.get("id")
        timestamp_unix = int(message_data.get("timestamp", 0))
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
