"""Create the tables and mint a demo free key + a demo pro key for local testing.

    python -m scripts.seed
"""

import secrets

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import ApiKey


def _ensure(session: Session, name: str, tier: str) -> ApiKey:
    existing = session.exec(select(ApiKey).where(ApiKey.name == name)).first()
    if existing:
        return existing
    key = ApiKey(key="sk_" + secrets.token_urlsafe(24), name=name, tier=tier)
    session.add(key)
    session.commit()
    session.refresh(key)
    return key


def main() -> None:
    init_db()
    with Session(engine) as session:
        # Read the key strings while the instances are still session-bound.
        free_key = _ensure(session, "demo-free", "free").key
        pro_key = _ensure(session, "demo-pro", "pro").key
    print("Demo keys (send as 'X-API-Key' header):")
    print(f"  free: {free_key}")
    print(f"  pro : {pro_key}")


if __name__ == "__main__":
    main()
