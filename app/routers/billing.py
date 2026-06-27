"""Stripe billing webhook — the live, direct-sales upgrade path.

Flow (no Stripe SDK required, so nothing extra to install):
  1. In the Stripe dashboard, create a recurring Price and a **Payment Link**
     for it. Enable "client reference ID" on the link.
  2. Your signup page sends the customer to that link with
     `?client_reference_id=<their API key>` appended.
  3. On successful payment Stripe POSTs `checkout.session.completed` here; we
     verify the signature and flip that key to the 'pro' tier.
  4. Cancellations arrive as `customer.subscription.deleted`; we downgrade.

Set STRIPE_WEBHOOK_SECRET (whsec_...) to enable this endpoint.
"""

import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..models import ApiKey

router = APIRouter(prefix="/webhooks", tags=["billing"])


def verify_stripe_signature(
    payload: bytes, sig_header: str, secret: str, now: float, tolerance: int = 300
) -> bool:
    """Verify a Stripe 'Stripe-Signature' header (scheme v1 = HMAC-SHA256)."""
    if not sig_header:
        return False
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False
    try:
        if tolerance and abs(now - int(timestamp)) > tolerance:
            return False
    except ValueError:
        return False
    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _upgrade(session: Session, key_ref, customer, subscription) -> None:
    if not key_ref:
        return
    key = session.exec(select(ApiKey).where(ApiKey.key == key_ref)).first()
    if key is None:
        return
    key.tier = "pro"
    key.source = "stripe"
    key.stripe_customer_id = customer
    key.stripe_subscription_id = subscription
    session.add(key)
    session.commit()


def _downgrade_by_subscription(session: Session, subscription_id) -> None:
    if not subscription_id:
        return
    key = session.exec(
        select(ApiKey).where(ApiKey.stripe_subscription_id == subscription_id)
    ).first()
    if key is None:
        return
    key.tier = "free"
    session.add(key)
    session.commit()


@router.post("/stripe")
async def stripe_webhook(request: Request, session: Session = Depends(get_session)):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe billing not configured")

    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    if not verify_stripe_signature(payload, sig, settings.stripe_webhook_secret, time.time()):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(payload)
    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        key_ref = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("api_key")
        _upgrade(session, key_ref, obj.get("customer"), obj.get("subscription"))
    elif event_type == "customer.subscription.deleted":
        _downgrade_by_subscription(session, obj.get("id"))
    elif event_type == "customer.subscription.updated":
        if obj.get("status") in ("canceled", "unpaid", "incomplete_expired"):
            _downgrade_by_subscription(session, obj.get("id"))

    return {"received": True, "handled": event_type}
