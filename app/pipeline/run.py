"""Pipeline entrypoint. Run locally or from CI (GitHub Actions) on a schedule:

    python -m app.pipeline.run

No-signup mode: this uses a local SQLite DB and exports the results to a
committed JSON snapshot (app/data/fundamentals.json). In CI it commits the
refreshed snapshot back to the repo, so the dataset stays fresh with no external
database. Set DATABASE_URL to also write into a persistent Postgres.
"""

import asyncio
import os
import subprocess

from sqlmodel import Session

from ..config import settings
from ..db import engine, init_db
from ..snapshot import DEFAULT_PATH, export_snapshot
from .ingest import collect, store_companies


def _commit_snapshot(path: str) -> None:
    """In CI, commit the refreshed snapshot back to the repo (best-effort)."""
    try:
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(
            ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
            check=True,
        )
        subprocess.run(["git", "add", path], check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
            print("snapshot unchanged; nothing to commit")
            return
        subprocess.run(
            ["git", "commit", "-m", "chore: refresh fundamentals snapshot [skip ci]"], check=True
        )
        subprocess.run(["git", "push"], check=True)
        print("committed refreshed snapshot")
    except Exception as exc:  # never fail the job over the commit step
        print(f"snapshot commit skipped: {exc}")


def main() -> None:
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    if in_ci and not os.environ.get("SEC_USER_AGENT", "").strip():
        print(
            "Skipping ingest: SEC_USER_AGENT secret not set. Add it in "
            "Settings -> Secrets and variables -> Actions to enable the pipeline."
        )
        return

    init_db()
    collected = asyncio.run(collect(settings.coverage_list))
    with Session(engine) as session:
        n_companies, n_rows = store_companies(session, collected)
        n_snap = export_snapshot(session)
    print(f"covered {n_companies} companies -> {n_rows} rows; snapshot has {n_snap} companies")

    if in_ci:
        _commit_snapshot(DEFAULT_PATH)


if __name__ == "__main__":
    main()
