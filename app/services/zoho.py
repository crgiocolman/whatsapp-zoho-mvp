import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def get_access_token() -> str:
    response = httpx.post(
        "https://accounts.zoho.com/oauth/v2/token",
        params={
            "refresh_token": settings.ZOHO_REFRESH_TOKEN,
            "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
    )
    print(f"[get_access_token] status={response.status_code} body={response.text}")
    response.raise_for_status()
    return response.json()["access_token"]


def find_contact_by_phone(phone: str, access_token: str) -> str | None:
    response = httpx.get(
        f"{settings.ZOHO_BASE_URL}/Contacts/search",
        params={"phone": phone},
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
    )
    if response.status_code == 204 or not response.text:
        return None
    response.raise_for_status()
    data = response.json().get("data")
    if data:
        return data[0]["id"]
    return None


def create_contact(phone: str, name: str, access_token: str) -> str:
    response = httpx.post(
        f"{settings.ZOHO_BASE_URL}/Contacts",
        json={"data": [{"Phone": phone, "Last_Name": name}]},
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
    )
    response.raise_for_status()
    return response.json()["data"][0]["details"]["id"]


def sync_contact(phone: str, name: str) -> str | None:
    try:
        access_token = get_access_token()
        contact_id = find_contact_by_phone(phone, access_token)
        if not contact_id:
            contact_id = create_contact(phone, name, access_token)
        return contact_id
    except Exception as e:
        print(f"[sync_contact] Error sincronizando contacto en Zoho (phone={phone}): {e}")
        return None
