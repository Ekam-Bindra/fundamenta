"""Pipeline entrypoint. Run locally or from CI (GitHub Actions) on a schedule:

    python -m app.pipeline.run
"""

import asyncio
import os

from sqlmodel import Session

from ..config import settings
from ..db import engine, init_db
from .ingest import collect, store_companies

# Secrets the scheduled pipeline needs to do real work in CI.
_REQUIRED_IN_CI = ("DATABASE_URL", "SEC_USER_AGENT")


def main() -> None:
    # In GitHub Actions, skip cleanly (instead of failing) until the backing
    # secrets are configured — a run against an ephemeral SQLite DB, or against
    # SEC with no contact header, is pointless and would error confusingly.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        missing = [v for v in _REQUIRED_IN_CI if not os.environ.get(v, "").strip()]
        if missing:
            print(
                f"Skipping ingest: missing secret(s) {', '.join(missing)}. "
                "Add them in the repo's Settings -> Secrets and variables -> Actions "
                "to enable the scheduled pipeline."
            )
            return

    init_db()
    collected = asyncio.run(collect(settings.coverage_list))
    with Session(engine) as session:
        n_companies, n_rows = store_companies(session, collected)
    print(f"covered {n_companies} companies -> {n_rows} financial-year rows")


if __name__ == "__main__":
    main()
