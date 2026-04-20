from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ConversationStatus


class WhatsAppProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str


class WhatsAppContact(BaseModel):
    model_config = ConfigDict(extra="allow")
    profile: Optional[WhatsAppProfile] = None
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
    statuses: Optional[List[dict]] = None


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


class SendMessageRequest(BaseModel):
    conversation_id: UUID
    text: str


class ContactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phone_number: str
    name: Optional[str] = None
    zoho_contact_id: Optional[str] = None


class ChannelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    display_phone_number: str
    display_name: Optional[str] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: ConversationStatus
    last_message_at: Optional[datetime] = None
    created_at: datetime
    contact: ContactSummary
    channel: ChannelSummary


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    direction: str
    body: Optional[str] = None
    timestamp: datetime
