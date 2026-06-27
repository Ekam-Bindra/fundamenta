"""FastAPI application entrypoint.

    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import init_db
from .routers import billing, companies, dashboard, keys, signup


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
    title="Company Fundamentals API",
    version="1.0.0",
    description=(
        "Clean, normalized company fundamentals (revenue, margins, growth, ROE) "
        "derived from SEC EDGAR filings. Get a free key at POST /v1/keys, then "
        "send it as the 'X-API-Key' header."
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
        "service": "Company Fundamentals API",
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
