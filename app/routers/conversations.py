from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ConversationResponse, MessageResponse
from app.services.whatsapp import get_conversation_messages, get_conversations

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=List[ConversationResponse])
def list_conversations(tenant_id: UUID, db: Session = Depends(get_db)):
    return get_conversations(db, tenant_id)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def list_conversation_messages(conversation_id: UUID, tenant_id: UUID, db: Session = Depends(get_db)):
    result = get_conversation_messages(db, tenant_id, conversation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result
