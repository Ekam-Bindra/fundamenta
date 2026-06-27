"""Self-serve API-key issuance + admin tier management.

`POST /v1/keys` is the free-tier on-ramp: anyone can mint a free key and start
calling immediately. Upgrading a key to the paid tier is an admin action that
you would trigger from your Stripe/RapidAPI webhook once a payment succeeds.
"""

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth import require_admin
from ..config import settings
from ..db import get_session
from ..models import ApiKey

router = APIRouter(prefix="/v1/keys", tags=["keys"])


@router.post("")
def create_key(name: str = "anonymous", session: Session = Depends(get_session)):
    key = ApiKey(key="sk_" + secrets.token_urlsafe(24), name=name, tier="free")
    session.add(key)
    session.commit()
    session.refresh(key)
    return {
        "api_key": key.key,
        "tier": key.tier,
        "daily_limit": settings.free_daily_limit,
        "usage": "Send this as the 'X-API-Key' header on every request.",
    }


@router.post("/{key_id}/upgrade")
def upgrade_key(
    key_id: int,
    token: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Promote a key to the paid tier. Call this from your payment webhook."""
    require_admin(token)
    key = session.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="Key not found")
    key.tier = "pro"
    session.add(key)
    session.commit()
    return {"id": key.id, "tier": key.tier, "daily_limit": settings.pro_daily_limit}
