"""Pipeline entrypoint. Run locally or from CI (GitHub Actions) on a schedule:

    python -m app.pipeline.run
"""

import asyncio

from sqlmodel import Session

from ..config import settings
from ..db import engine, init_db
from .ingest import collect, store_companies


def main() -> None:
    init_db()
    collected = asyncio.run(collect(settings.coverage_list))
    with Session(engine) as session:
        n_companies, n_rows = store_companies(session, collected)
    print(f"covered {n_companies} companies -> {n_rows} financial-year rows")


if __name__ == "__main__":
    main()
