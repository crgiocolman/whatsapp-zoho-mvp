from fastapi import APIRouter, Query, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import WhatsAppWebhookPayload
from app.services.whatsapp import process_incoming_message

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("", status_code=403)


@router.post("")
def receive_webhook(payload: WhatsAppWebhookPayload, db: Session = Depends(get_db)):
    process_incoming_message(payload, db)
    return {"status": "ok"}
