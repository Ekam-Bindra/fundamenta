import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import ApiKey
from app.routers.billing import verify_stripe_signature

client = TestClient(app)
SECRET = "whsec_test"


def _sign(payload: bytes, t: int, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()


def test_verify_signature_accepts_valid_and_rejects_tampered():
    payload = b'{"hello":"world"}'
    t = 1_700_000_000
    good = _sign(payload, t)
    assert verify_stripe_signature(payload, f"t={t},v1={good}", SECRET, now=t) is True
    # wrong secret
    assert verify_stripe_signature(payload, f"t={t},v1={good}", "whsec_other", now=t) is False
    # stale timestamp (beyond tolerance)
    assert verify_stripe_signature(payload, f"t={t},v1={good}", SECRET, now=t + 10_000) is False


def test_webhook_upgrades_key_on_checkout_completed():
    api_key = client.post("/v1/keys", params={"name": "buyer"}).json()["api_key"]

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": api_key,
                "customer": "cus_123",
                "subscription": "sub_123",
            }
        },
    }
    payload = json.dumps(event).encode()
    t = int(time.time())
    resp = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": f"t={t},v1={_sign(payload, t)}"},
    )
    assert resp.status_code == 200

    with Session(engine) as session:
        row = session.exec(select(ApiKey).where(ApiKey.key == api_key)).first()
        assert row.tier == "pro"
        assert row.stripe_subscription_id == "sub_123"


def test_webhook_rejects_bad_signature():
    resp = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 400
