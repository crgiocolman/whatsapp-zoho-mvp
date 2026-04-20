from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import conversations, messages, tenants, webhook
from app.models import Conversation, Message

app = FastAPI(title="WhatsApp Zoho MVP")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(webhook.router)
app.include_router(messages.router)
app.include_router(conversations.router)
app.include_router(tenants.router)

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/panel")
def panel():
    return FileResponse("app/static/index.html")
