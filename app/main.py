from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="WhatsApp Zoho MVP")


@app.get("/health")
def health_check():
    return {"status": "ok"}
