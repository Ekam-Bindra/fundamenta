"""Repo-committed data snapshot — the zero-signup data path.

The pipeline exports company fundamentals to app/data/fundamentals.json, which is
committed to the repo. On startup the app loads that snapshot into its local DB,
so the API serves real data with **no external database** required.

Tradeoff: product data (companies/financials) is served from the committed
snapshot, but API keys and usage counters live in the app's local DB — which is
NOT persistent on ephemeral free hosts (they reset on restart). Fine for a
demo/portfolio; move to a real Postgres (set DATABASE_URL) for a production
business that must retain customers' keys.
"""

import json
import os

from sqlmodel import Session, select

from .models import Company, Financials

DEFAULT_PATH = "app/data/fundamentals.json"

_FIN_FIELDS = (
    "fiscal_year",
    "revenue",
    "net_income",
    "assets",
    "liabilities",
    "equity",
    "net_margin",
    "revenue_growth",
    "roe",
)


def export_snapshot(session: Session, path: str = DEFAULT_PATH) -> int:
    """Write all companies + financials to a stable, diff-friendly JSON file.

    Deterministic ordering + sorted keys keep git diffs minimal so an unchanged
    dataset produces an identical file (and thus no commit)."""
    companies = session.exec(select(Company).order_by(Company.ticker)).all()
    out = []
    for c in companies:
        fins = session.exec(
            select(Financials)
            .where(Financials.cik == c.cik)
            .order_by(Financials.fiscal_year)
        ).all()
        out.append(
            {
                "cik": c.cik,
                "ticker": c.ticker,
                "name": c.name,
                "financials": [{f: getattr(fin, f) for f in _FIN_FIELDS} for fin in fins],
            }
        )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"companies": out}, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return len(out)


def load_snapshot(session: Session, path: str = DEFAULT_PATH) -> int:
    """Load a snapshot into the DB. Returns the number of financial rows added."""
    if not os.path.exists(path):
        return 0
    with open(path) as fh:
        payload = json.load(fh)
    rows = 0
    for c in payload.get("companies", []):
        session.add(Company(cik=c["cik"], ticker=c["ticker"], name=c.get("name", "")))
        for fin in c.get("financials", []):
            session.add(
                Financials(cik=c["cik"], ticker=c["ticker"], **{f: fin.get(f) for f in _FIN_FIELDS})
            )
            rows += 1
    session.commit()
    return rows
