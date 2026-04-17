import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ZohoConnection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _get_api_base_url(region: str) -> str:
    return f"https://www.zohoapis.{region}/crm/v2"


def _get_accounts_url(region: str) -> str:
    return f"https://accounts.zoho.{region}/oauth/v2/token"


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def _refresh_access_token(db: Session, zoho_conn: ZohoConnection) -> str:
    """Calls Zoho token endpoint, persists new token to DB, returns access_token.

    Raises on any failure so callers can decide how to handle it.
    """
    payload = {
        "refresh_token": zoho_conn.refresh_token,
        "client_id": settings.ZOHO_CLIENT_ID,
        "client_secret": settings.ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    try:
        response = httpx.post(_get_accounts_url(zoho_conn.region), data=payload)

        if not response.text:
            raise ValueError("Empty response from Zoho token endpoint")
        if not response.is_success:
            raise ValueError(
                f"Zoho token refresh failed: status={response.status_code} body={response.text}"
            )

        data = response.json()
        if "access_token" not in data:
            raise ValueError(f"Zoho token response missing access_token: {data}")

        new_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))

        zoho_conn.access_token = new_token
        zoho_conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        db.commit()

        logger.info(
            "Zoho access_token refreshed for org_id=%s, expires_at=%s",
            zoho_conn.org_id,
            zoho_conn.token_expires_at,
        )
        return new_token

    except Exception:
        db.rollback()
        raise


def _get_valid_access_token(db: Session, zoho_conn: ZohoConnection) -> str:
    """Returns a valid access_token, refreshing if expired or expiring within 5 min."""
    now = datetime.now(timezone.utc)
    expires_at = zoho_conn.token_expires_at
    threshold = now + timedelta(minutes=5)

    if expires_at is None or expires_at <= threshold:
        return _refresh_access_token(db, zoho_conn)
    return zoho_conn.access_token


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_contact_by_phone(
    db: Session,
    zoho_conn: ZohoConnection,
    phone_number: str,
) -> Optional[dict]:
    """Searches Zoho CRM for a contact by phone number.

    Returns the first matching contact dict, or None if not found.
    """
    access_token = _get_valid_access_token(db, zoho_conn)
    api_base = _get_api_base_url(zoho_conn.region)

    response = httpx.get(
        f"{api_base}/Contacts/search",
        params={"criteria": f"(Phone:equals:{phone_number})"},
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
    )

    if response.status_code == 204 or not response.text:
        return None

    if response.status_code == 200:
        data = response.json().get("data", [])
        return data[0] if data else None

    logger.warning(
        "find_contact_by_phone unexpected response: status=%s body=%s",
        response.status_code,
        response.text,
    )
    return None


def create_contact(
    db: Session,
    zoho_conn: ZohoConnection,
    phone_number: str,
    name: Optional[str] = None,
) -> Optional[dict]:
    """Creates a contact in Zoho CRM. Returns the created contact details dict, or None."""
    access_token = _get_valid_access_token(db, zoho_conn)
    api_base = _get_api_base_url(zoho_conn.region)

    last_name = name or f"WhatsApp {phone_number}"
    payload = {
        "data": [
            {
                "Last_Name": last_name,
                "Phone": phone_number,
                "Description": "Contacto creado desde SiuChat",
            }
        ]
    }

    response = httpx.post(
        f"{api_base}/Contacts",
        json=payload,
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
    )

    if not response.text:
        logger.error("create_contact empty response for phone=%s", phone_number)
        return None
    if not response.is_success:
        logger.error(
            "create_contact failed: status=%s body=%s",
            response.status_code,
            response.text,
        )
        return None

    data = response.json().get("data", [])
    if not data:
        logger.error("create_contact empty data in response: %s", response.text)
        return None

    return data[0].get("details")


def sync_contact(
    db: Session,
    zoho_conn: ZohoConnection,
    phone_number: str,
    name: Optional[str] = None,
) -> Optional[str]:
    """Finds or creates a contact in Zoho CRM. Returns zoho_contact_id or None."""
    try:
        result = find_contact_by_phone(db, zoho_conn, phone_number)
        if result:
            return result["id"]

        result = create_contact(db, zoho_conn, phone_number, name)
        if result:
            return result["id"]

        logger.error(
            "sync_contact: find and create both returned None for phone=%s", phone_number
        )
        return None

    except Exception as e:
        logger.error("sync_contact error for phone=%s: %s", phone_number, e)
        return None
