"""FastAPI application entrypoint.

    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from sqlmodel import Session, select

from .config import settings
from .db import engine, init_db
from .models import Company
from .routers import billing, companies, dashboard, keys, signup
from .snapshot import load_snapshot


def _seed_from_snapshot() -> None:
    """If the product tables are empty, load the committed data snapshot.

    This is what lets the API serve real data with no external database — on an
    ephemeral host the local DB starts empty each boot and is reseeded here."""
    with Session(engine) as session:
        if session.exec(select(Company).limit(1)).first() is None:
            rows = load_snapshot(session)
            if rows:
                print(f"loaded {rows} financial rows from committed snapshot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_from_snapshot()
    scheduler = None
    if settings.run_scheduler:
        # Optional: run the pipeline inside the web process (handy on a single
        # always-on host). On free tiers that sleep, prefer the GitHub Actions
        # cron in .github/workflows/ingest.yml instead.
        from apscheduler.schedulers.background import BackgroundScheduler

        from .pipeline.run import main as run_pipeline

        scheduler = BackgroundScheduler()
        scheduler.add_job(run_pipeline, "interval", hours=24)
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Fundamenta",
    version="1.0.0",
    description=(
        "Fundamenta — clean, normalized company fundamentals (revenue, margins, "
        "growth, ROE) derived from SEC EDGAR filings. Get a free key at "
        "POST /v1/keys, then send it as the 'X-API-Key' header."
    ),
    lifespan=lifespan,
)

app.include_router(companies.router)
app.include_router(keys.router)
app.include_router(dashboard.router)
app.include_router(billing.router)
app.include_router(signup.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/", tags=["meta"])
def root():
    return {
        "service": "Fundamenta",
        "docs": "/docs",
        "signup": "/signup",
        "get_a_key": "POST /v1/keys",
        "endpoints": [
            "/v1/companies",
            "/v1/companies/{ticker}",
            "/v1/companies/{ticker}/fundamentals",
            "/v1/screen",
        ],
        "source": "SEC EDGAR (public domain)",
    }
