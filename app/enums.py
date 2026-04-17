from enum import Enum


class TenantPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class TenantStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AGENT = "agent"


class ConversationStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
