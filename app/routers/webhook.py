import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import WhatsAppWebhookPayload
from app.services import whatsapp as whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("", status_code=403)


@router.post("")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception as e:
        logger.warning(f"Webhook recibido con body no-JSON: {e}")
        return {"status": "ok"}

    try:
        payload = WhatsAppWebhookPayload.model_validate(body)
    except Exception as e:
        logger.debug(
            f"Webhook con payload inválido (no matchea WhatsAppWebhookPayload). "
            f"Error: {e}. Body: {body}"
        )
        return {"status": "ok"}

    event_types = _detect_event_types(payload)
    if event_types:
        logger.info(f"Webhook recibido con eventos: {event_types}")

    try:
        whatsapp_service.process_incoming_message(db, payload)
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}", exc_info=True)

    return {"status": "ok"}


def _detect_event_types(payload: WhatsAppWebhookPayload) -> list[str]:
    types = set()
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            if getattr(value, "messages", None):
                types.add("messages")
            if getattr(value, "statuses", None):
                types.add("statuses")
    return sorted(types)
