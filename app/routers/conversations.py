from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ConversationResponse, MessageResponse
from app.services.whatsapp import get_conversation_messages, get_conversations

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=List[ConversationResponse])
def list_conversations(db: Session = Depends(get_db)):
    return get_conversations(db)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def list_conversation_messages(conversation_id: str, db: Session = Depends(get_db)):
    result = get_conversation_messages(conversation_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result
