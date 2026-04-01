from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str


class WhatsAppContact(BaseModel):
    model_config = ConfigDict(extra="allow")
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppTextBody(BaseModel):
    model_config = ConfigDict(extra="allow")
    body: str


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    from_number: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppTextBody] = None


class WhatsAppMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    model_config = ConfigDict(extra="allow")
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None


class WhatsAppChange(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    object: str
    entry: List[WhatsAppEntry]
