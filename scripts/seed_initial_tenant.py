"""
Seed del tenant inicial para SiuChat.

Crea el tenant Dev Tech Py, el primer user admin, el canal de WhatsApp
inicial y la conexión Zoho a partir de valores del .env local.

Uso:
    python -m scripts.seed_initial_tenant

Idempotente: si el tenant ya existe, aborta sin cambios.

Variables obligatorias en .env:
    SEED_TENANT_NAME, SEED_ADMIN_EMAIL, SEED_ADMIN_NAME,
    ZOHO_ORG_ID, ZOHO_REGION, ZOHO_REFRESH_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_BUSINESS_ACCOUNT_ID,
    WHATSAPP_DISPLAY_PHONE_NUMBER, WHATSAPP_TOKEN
"""

import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.database import SessionLocal
from app.enums import TenantPlan, TenantStatus, UserRole
from app.models import Channel, Tenant, User, ZohoConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


REQUIRED_VARS = [
    "SEED_TENANT_NAME",
    "SEED_ADMIN_EMAIL",
    "SEED_ADMIN_NAME",
    "ZOHO_ORG_ID",
    "ZOHO_REGION",
    "ZOHO_REFRESH_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "WHATSAPP_DISPLAY_PHONE_NUMBER",
    "WHATSAPP_TOKEN",
]


def load_and_validate_env() -> dict:
    """Carga .env y valida que todas las vars obligatorias estén presentes.

    Exits con código 2 si falta alguna variable obligatoria.
    """
    load_dotenv()

    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        logger.error("Faltan variables de entorno obligatorias: %s", missing)
        sys.exit(2)

    env = {var: os.getenv(var) for var in REQUIRED_VARS}
    env["WHATSAPP_DISPLAY_NAME"] = os.getenv("WHATSAPP_DISPLAY_NAME") or env["SEED_TENANT_NAME"]

    logger.info("Todas las variables de entorno obligatorias están presentes.")
    return env


def seed(env: dict) -> None:
    """Crea el tenant inicial y sus entidades asociadas en una transacción atómica."""
    db = SessionLocal()
    try:
        existing = db.query(Tenant).filter(Tenant.name == env["SEED_TENANT_NAME"]).first()
        if existing:
            logger.error(
                "Tenant '%s' ya existe (id=%s). "
                "Si querés re-seedear, borralo manualmente.",
                env["SEED_TENANT_NAME"],
                existing.id,
            )
            sys.exit(1)

        logger.info("Creando tenant '%s'...", env["SEED_TENANT_NAME"])

        # 1. Tenant
        tenant = Tenant(
            name=env["SEED_TENANT_NAME"],
            plan=TenantPlan.PRO,
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        db.flush()

        # 2. User admin
        admin = User(
            tenant_id=tenant.id,
            email=env["SEED_ADMIN_EMAIL"],
            name=env["SEED_ADMIN_NAME"],
            zoho_user_id=None,
            role=UserRole.ADMIN,
            active=True,
        )
        db.add(admin)
        db.flush()

        # 3. Channel
        channel = Channel(
            tenant_id=tenant.id,
            phone_number_id=env["WHATSAPP_PHONE_NUMBER_ID"],
            business_account_id=env["WHATSAPP_BUSINESS_ACCOUNT_ID"],
            display_phone_number=env["WHATSAPP_DISPLAY_PHONE_NUMBER"],
            display_name=env["WHATSAPP_DISPLAY_NAME"],
            token=env["WHATSAPP_TOKEN"],
            active=True,
            created_by=admin.id,
        )
        db.add(channel)
        db.flush()

        # 4. ZohoConnection — access_token placeholder, expires_at=ahora para forzar refresh
        zoho_conn = ZohoConnection(
            tenant_id=tenant.id,
            org_id=env["ZOHO_ORG_ID"],
            access_token="SEEDED_PLACEHOLDER",
            refresh_token=env["ZOHO_REFRESH_TOKEN"],
            region=env["ZOHO_REGION"],
            token_expires_at=datetime.now(timezone.utc),
            created_by=admin.id,
        )
        db.add(zoho_conn)
        db.flush()

        db.commit()

        logger.info("Seed completado exitosamente.")
        print()
        print(f"Tenant ID:          {tenant.id}")
        print(f"Admin User ID:      {admin.id}")
        print(f"Channel ID:         {channel.id}")
        print(f"Zoho Connection ID: {zoho_conn.id}")

    except Exception as e:
        db.rollback()
        logger.error("Error durante el seed: %s", e)
        raise
    finally:
        db.close()


def main() -> None:
    env = load_and_validate_env()
    seed(env)


if __name__ == "__main__":
    main()
