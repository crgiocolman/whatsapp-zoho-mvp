import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.enums import ConversationStatus, TenantPlan, TenantStatus, UserRole

# Helper: force SQLAlchemy to use enum .value (lowercase) in PostgreSQL, not .name.
_enum_values = lambda obj: [e.value for e in obj]  # noqa: E731


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    plan = Column(
        SQLEnum(TenantPlan, name="tenant_plan", native_enum=True, create_type=True,
                values_callable=_enum_values),
        nullable=False,
        default=TenantPlan.FREE,
        server_default=f"'{TenantPlan.FREE.value}'",
    )
    status = Column(
        SQLEnum(TenantStatus, name="tenant_status", native_enum=True, create_type=True,
                values_callable=_enum_values),
        nullable=False,
        default=TenantStatus.TRIAL,
        server_default=f"'{TenantStatus.TRIAL.value}'",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    zoho_user_id = Column(String, nullable=True)
    role = Column(
        SQLEnum(UserRole, name="user_role", native_enum=True, create_type=True,
                values_callable=_enum_values),
        nullable=False,
    )
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            ondelete="RESTRICT", name="fk_users_tenant_id_tenants",
        ),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("uq_users_tenant_zoho_user", "tenant_id", "zoho_user_id",
              unique=True, postgresql_where=text("zoho_user_id IS NOT NULL")),
        Index("ix_users_tenant_id", "tenant_id"),
    )


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------

class Channel(Base):
    __tablename__ = "channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    phone_number_id = Column(String, nullable=False)
    business_account_id = Column(String, nullable=False)
    display_phone_number = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    token = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            ondelete="RESTRICT", name="fk_channels_tenant_id_tenants",
        ),
        ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            ondelete="RESTRICT", name="fk_channels_created_by_users",
        ),
        UniqueConstraint("phone_number_id", name="uq_channels_phone_number_id"),
        Index("ix_channels_tenant_id", "tenant_id"),
    )


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    phone_number = Column(String, nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    zoho_contact_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            ondelete="RESTRICT", name="fk_contacts_tenant_id_tenants",
        ),
        UniqueConstraint("tenant_id", "phone_number", name="uq_contacts_tenant_phone"),
        Index("ix_contacts_tenant_id", "tenant_id"),
    )


# ---------------------------------------------------------------------------
# ZohoConnection
# ---------------------------------------------------------------------------

class ZohoConnection(Base):
    __tablename__ = "zoho_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    org_id = Column(String, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    region = Column(String, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            ondelete="RESTRICT", name="fk_zoho_connections_tenant_id_tenants",
        ),
        ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            ondelete="RESTRICT", name="fk_zoho_connections_created_by_users",
        ),
        UniqueConstraint("tenant_id", name="uq_zoho_connections_tenant_id"),
        UniqueConstraint("org_id", name="uq_zoho_connections_org_id"),
    )


# ---------------------------------------------------------------------------
# Conversation  (modified from MVP)
# ---------------------------------------------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    channel_id = Column(UUID(as_uuid=True), nullable=False)
    contact_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(
        SQLEnum(ConversationStatus, name="conversation_status", native_enum=True, create_type=True,
                values_callable=_enum_values),
        nullable=False,
        default=ConversationStatus.OPEN,
        server_default=f"'{ConversationStatus.OPEN.value}'",
    )
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    messages = relationship("Message", back_populates="conversation")

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            ondelete="RESTRICT", name="fk_conversations_tenant_id_tenants",
        ),
        ForeignKeyConstraint(
            ["channel_id"], ["channels.id"],
            ondelete="RESTRICT", name="fk_conversations_channel_id_channels",
        ),
        ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"],
            ondelete="RESTRICT", name="fk_conversations_contact_id_contacts",
        ),
        UniqueConstraint("channel_id", "contact_id", name="uq_conversations_channel_contact"),
        Index("ix_conversations_tenant_id", "tenant_id"),
        Index("ix_conversations_contact_id", "contact_id"),
        # DESC on last_message_at must be added manually after autogenerate —
        # Alembic does not emit DESC ordering in index definitions.
        Index("ix_conversations_tenant_last_msg", "tenant_id", "last_message_at"),
    )


# ---------------------------------------------------------------------------
# Message  (modified from MVP)
# ---------------------------------------------------------------------------

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    direction = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    whatsapp_message_id = Column(String, unique=True, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            ondelete="RESTRICT", name="fk_messages_tenant_id_tenants",
        ),
        ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            ondelete="RESTRICT", name="fk_messages_conversation_id_conversations",
        ),
        Index("ix_messages_tenant_id", "tenant_id"),
    )
