import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Channel, Contact, Conversation
from app.schemas import SendMessageRequest
from app.services.whatsapp import send_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/send")
def send_message_endpoint(request: SendMessageRequest, tenant_id: UUID, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.tenant_id == tenant_id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or not yours")

    channel = db.query(Channel).filter(Channel.id == conversation.channel_id).first()
    contact = db.query(Contact).filter(Contact.id == conversation.contact_id).first()

    message = send_message(db, channel, contact.phone_number, request.text)
    if message is None:
        raise HTTPException(status_code=500, detail="Failed to send message")

    return {
        "id": str(message.id),
        "direction": message.direction,
        "body": message.body,
        "timestamp": message.timestamp,
    }
