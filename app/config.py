"""Central configuration. All values are overridable via environment variables
or a local .env file (see .env.example). Defaults are chosen so the project
runs on a zero-cost local SQLite setup with no secrets required."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_DATABASE_URL = "sqlite:///./data.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def _fallback_database_url(cls, v):
        # An unset secret in CI expands to "" and would otherwise crash
        # create_engine(). Treat empty/whitespace as "use the default".
        if v is None or not str(v).strip():
            return _DEFAULT_DATABASE_URL
        return v

    # --- Storage -----------------------------------------------------------
    # SQLite for local dev (free, file-based). In production, point this at a
    # free managed Postgres (Neon / Supabase free tier), e.g.
    #   postgresql://user:pass@host/db
    database_url: str = _DEFAULT_DATABASE_URL

    # --- Auth / billing tiers ---------------------------------------------
    admin_token: str = "change-me"          # protects /dashboard and admin endpoints
    free_daily_limit: int = 100             # calls/day on the free tier
    pro_daily_limit: int = 10_000           # calls/day on the paid tier
    pro_price_usd: float = 29.0             # monthly price of the pro tier (for MRR estimate)

    # --- RapidAPI (marketplace billing; zero code on our side) ------------
    # When listed on RapidAPI, the marketplace proxies every request and adds a
    # shared secret + the subscriber's plan. Set this to the secret RapidAPI
    # shows you; leave empty to disable the RapidAPI trust path.
    rapidapi_proxy_secret: str = ""
    # RapidAPI plan names that count as "paid". BASIC is RapidAPI's free plan.
    rapidapi_paid_plans: str = "PRO,ULTRA,MEGA,CUSTOM"
    # Lock the origin to RapidAPI-only: reject direct (non-proxied) traffic so
    # nobody can bypass marketplace billing. Leave False if you also sell direct.
    require_rapidapi: bool = False

    # --- Stripe (direct billing via Payment Link + webhook) ---------------
    stripe_webhook_secret: str = ""         # whsec_...; leave empty to disable
    stripe_pro_price_id: str = ""           # informational (your Price ID)
    # Your Stripe Payment Link URL. When set, the /signup page shows an
    # "Upgrade to Pro" button that hands the new key to Stripe checkout.
    stripe_payment_link: str = ""

    # --- Data source: SEC EDGAR -------------------------------------------
    # SEC requires a descriptive User-Agent with real contact info and rate
    # limits to <10 req/s. CHANGE THIS to your real name + email before running
    # against SEC in production, or they will block you.
    sec_user_agent: str = "SummerProject Data API admin@example.com"
    # The universe of companies we cover (comma-separated tickers). Used unless
    # COVERAGE_FILE is set (below).
    coverage_tickers: str = (
        "AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA,NFLX,AMD,INTC,"
        "CRM,ORCL,ADBE,CSCO,IBM,QCOM,TXN,AVGO,PYPL,SHOP"
    )
    # Optional: path to a newline-delimited ticker file (lines starting with '#'
    # are ignored). Set COVERAGE_FILE=app/data/sp500.txt to cover the S&P 500.
    # Regenerate that file with: python -m scripts.refresh_sp500
    coverage_file: str = ""

    # --- Runtime -----------------------------------------------------------
    run_scheduler: bool = False             # run the ingest loop inside the web process

    @property
    def coverage_list(self) -> list[str]:
        # A coverage file, when configured and non-empty, takes precedence.
        if self.coverage_file:
            try:
                with open(self.coverage_file) as f:
                    tickers = [
                        line.strip().upper()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                if tickers:
                    return tickers
            except OSError:
                pass  # fall back to the inline list
        return [t.strip().upper() for t in self.coverage_tickers.split(",") if t.strip()]

    @property
    def rapidapi_paid_set(self) -> set[str]:
        return {p.strip().upper() for p in self.rapidapi_paid_plans.split(",") if p.strip()}


settings = Settings()
