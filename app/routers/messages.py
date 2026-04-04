from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SendMessageRequest
from app.services.whatsapp import send_message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/send")
def send_message_endpoint(request: SendMessageRequest, db: Session = Depends(get_db)):
    try:
        return send_message(request.to_number, request.body, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
