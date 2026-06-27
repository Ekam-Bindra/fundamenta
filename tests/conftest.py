"""Set test env before anything imports app.config, then create the schema
(a bare TestClient does not trigger the lifespan)."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ADMIN_TOKEN", "test-admin")
os.environ.setdefault("RAPIDAPI_PROXY_SECRET", "test-proxy")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")

from app.db import init_db  # noqa: E402  (must follow the env setup above)

init_db()
