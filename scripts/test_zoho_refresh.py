"""
Script descartable para probar services/zoho.py.

Uso:
    python -m scripts.test_zoho_refresh

Pasos:
1. Lee la zoho_connection del tenant Dev Tech Py
2. Muestra estado actual (access_token y token_expires_at)
3. Llama sync_contact con un número de prueba ficticio
4. Muestra estado post-refresh

Después de validar A.4 completo, borrar este archivo.
"""

import logging

from app.database import SessionLocal
from app.models import Tenant, ZohoConnection
from app.services import zoho as zoho_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

TEST_PHONE = "+595981111111"
TEST_NAME = "Test Contact SiuChat"


def main() -> None:
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.name == "Dev Tech Py").first()
        if not tenant:
            logger.error("Tenant 'Dev Tech Py' no encontrado. Correr el seed primero.")
            return

        zoho_conn = db.query(ZohoConnection).filter(
            ZohoConnection.tenant_id == tenant.id
        ).first()
        if not zoho_conn:
            logger.error("ZohoConnection no encontrada para Dev Tech Py.")
            return

        print()
        print("=" * 60)
        print("ESTADO ANTES DEL TEST")
        print("=" * 60)
        print(f"access_token:    {zoho_conn.access_token[:30]}...")
        print(f"token_expires_at: {zoho_conn.token_expires_at}")
        print(f"region:           {zoho_conn.region}")
        print(f"org_id:           {zoho_conn.org_id}")
        print()

        logger.info("Llamando sync_contact con %s...", TEST_PHONE)
        zoho_contact_id = zoho_service.sync_contact(db, zoho_conn, TEST_PHONE, TEST_NAME)

        db.refresh(zoho_conn)

        print()
        print("=" * 60)
        print("ESTADO DESPUÉS DEL TEST")
        print("=" * 60)
        print(f"access_token:    {zoho_conn.access_token[:30]}...")
        print(f"token_expires_at: {zoho_conn.token_expires_at}")
        print()
        print(f"zoho_contact_id retornado: {zoho_contact_id}")
        print()

        if zoho_contact_id:
            print("[OK] Test exitoso.")
        else:
            print("[FAIL] sync_contact retorno None -- ver logs arriba.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
