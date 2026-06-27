"""API-key authentication + per-tier daily rate limiting.

Two identity paths are supported, both metered:

1. **Self-serve keys** — callers mint a key at POST /v1/keys and send it as the
   `X-API-Key` header. Tiers change via Stripe (see app/routers/billing.py) or
   the admin upgrade endpoint.
2. **RapidAPI** — when listed on the RapidAPI marketplace, every request is
   proxied with a shared `X-RapidAPI-Proxy-Secret` and the subscriber's plan in
   `X-RapidAPI-Subscription`. We trust that secret, identify the caller by
   `X-RapidAPI-User`, auto-provision a key for them, and map their plan to a
   tier. This means RapidAPI handles all billing — no payment code on our side.
"""

import hmac
from datetime import date
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from .config import settings
from .db import get_session
from .models import ApiKey, Usage


def _daily_limit(tier: str) -> int:
    return settings.pro_daily_limit if tier == "pro" else settings.free_daily_limit


def _enforce_rate_limit(session: Session, key: ApiKey) -> ApiKey:
    today = date.today()
    usage = session.exec(
        select(Usage).where(Usage.api_key_id == key.id, Usage.day == today)
    ).first()
    if usage is None:
        usage = Usage(api_key_id=key.id, day=today, count=0)

    limit = _daily_limit(key.tier)
    if usage.count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit reached ({limit}/day on the '{key.tier}' tier). Upgrade for more.",
        )
    usage.count += 1
    session.add(usage)
    session.commit()
    return key


def _rapidapi_tier(subscription: Optional[str]) -> str:
    if subscription and subscription.strip().upper() in settings.rapidapi_paid_set:
        return "pro"
    return "free"


def _provision_rapidapi_key(session: Session, user: str, tier: str) -> ApiKey:
    key_str = f"rapidapi:{user}"
    key = session.exec(select(ApiKey).where(ApiKey.key == key_str)).first()
    if key is None:
        key = ApiKey(key=key_str, name=user, tier=tier, source="rapidapi")
    elif key.tier != tier:
        key.tier = tier  # reflect upgrades/downgrades made on RapidAPI
    session.add(key)
    session.commit()
    session.refresh(key)
    return key


def get_api_key(
    x_api_key: Optional[str] = Header(default=None),
    x_rapidapi_proxy_secret: Optional[str] = Header(default=None),
    x_rapidapi_user: Optional[str] = Header(default=None),
    x_rapidapi_subscription: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> ApiKey:
    # Optional: lock the origin to RapidAPI-only traffic (no direct bypass).
    if settings.require_rapidapi and x_rapidapi_proxy_secret is None:
        raise HTTPException(status_code=403, detail="Access via the RapidAPI marketplace only")

    # --- RapidAPI path ---
    if x_rapidapi_proxy_secret is not None:
        if not settings.rapidapi_proxy_secret or not hmac.compare_digest(
            x_rapidapi_proxy_secret, settings.rapidapi_proxy_secret
        ):
            raise HTTPException(status_code=403, detail="Invalid RapidAPI proxy secret")
        user = (x_rapidapi_user or "rapidapi-user").strip()
        key = _provision_rapidapi_key(session, user, _rapidapi_tier(x_rapidapi_subscription))
        return _enforce_rate_limit(session, key)

    # --- Self-serve key path ---
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    key = session.exec(
        select(ApiKey).where(ApiKey.key == x_api_key, ApiKey.active == True)  # noqa: E712
    ).first()
    if key is None:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    return _enforce_rate_limit(session, key)


def require_admin(token: Optional[str] = None) -> None:
    """Guard for admin-only endpoints (dashboard, tier upgrades)."""
    if not hmac.compare_digest(token or "", settings.admin_token):
        raise HTTPException(status_code=403, detail="Admin token required")
