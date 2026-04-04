from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.routers import messages, webhook
from app.models import Conversation, Message

app = FastAPI(title="WhatsApp Zoho MVP")
app.include_router(webhook.router)
app.include_router(messages.router)

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok"}
