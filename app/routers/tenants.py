import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import UserRole
from app.models import Tenant, User, ZohoConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tenants"])


@router.get("/current-tenant")
def get_current_tenant(db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.role == UserRole.ADMIN, User.active == True)
        .order_by(User.created_at.asc())
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="No tenant found")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    zoho = db.query(ZohoConnection).filter(ZohoConnection.tenant_id == user.tenant_id).first()

    return {
        "tenant_id": str(user.tenant_id),
        "name": tenant.name if tenant else None,
        "zoho_org_id": zoho.org_id if zoho else None,
    }
