# Fundamenta — company fundamentals as a service

[![CI](https://github.com/Ekam-Bindra/fundamenta/actions/workflows/ci.yml/badge.svg)](https://github.com/Ekam-Bindra/fundamenta/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

> **Open source (MIT).** A production-shaped **template for building a
> data-as-a-service API** — SEC company fundamentals is the reference
> implementation. Fork it, swap the data source, ship your own.

A small, autonomous **data API** you can run as a side-income business on **$0 of
infrastructure**. It serves clean, normalized **company fundamentals** (revenue,
net income, margins, YoY growth, ROE) derived from **SEC EDGAR** filings — the
kind of data that is free but genuinely painful to extract from raw XBRL, which
is exactly why people pay for a clean API.

It combines:

- **Data science** — an ingest → parse → enrich pipeline that pulls XBRL facts
  from SEC and computes per-fiscal-year metrics ([app/pipeline/](app/pipeline/)).
- **MIS / business** — API-key auth, per-tier rate limiting, **two live billing
  paths** (RapidAPI + Stripe), usage metering, and an operator dashboard with
  estimated MRR ([app/routers/dashboard.py](app/routers/dashboard.py)).

> **Honest expectation:** this repo gives you a real, listable, monetizable
> product in days. Revenue from organic/marketplace channels typically ramps
> over 2–6 months *after* launch. See **[PLAN.md](PLAN.md)** for the economics
> and the niche-validation framework if you want to swap in a different dataset.

## 🚀 Want to launch it?

Follow **[LAUNCH.md](LAUNCH.md)** — the step-by-step path from local code to a
deployed, billable API (Neon + Render + GitHub Actions + RapidAPI/Stripe), all
on free tiers.

## Runs with no database (zero-signup)

By default Fundamenta needs **no external database**. The pipeline exports a data
snapshot to [app/data/fundamentals.json](app/data/fundamentals.json) (committed to
the repo), and the app loads it on startup — so the API serves real data anywhere,
with nothing to sign up for. The daily GitHub Action regenerates and commits the
snapshot itself, keeping it fresh autonomously.

Tradeoff: product data works great this way, but **API keys / usage counters** need
a persistent writable DB, which an ephemeral free host doesn't provide — they reset
on restart. For a production business that must retain customers, set `DATABASE_URL`
to a real Postgres (see [LAUNCH.md](LAUNCH.md)). Until then, this is demo/portfolio-grade.

## Why this data sells

- **Source is free & public domain.** SEC EDGAR has no API key and permits
  programmatic access (just send a real `User-Agent` and stay under 10 req/s).
- **Cleaning is the value.** Companies report the same metric under different
  XBRL tags across years; we normalize that into one tidy table.
- **Recurring need.** Filings update quarterly, so customers keep calling.

## Architecture

```
        ┌─────────────────────┐      daily (GitHub Actions, free)
        │  app/pipeline/run   │◀───────────── cron ───────────────┐
        │  SEC EDGAR XBRL →   │                                   │
        │  parse → metrics    │                                   │
        └──────────┬──────────┘                                   │
                   │ writes                                       │
                   ▼                                              │
        ┌─────────────────────┐                                  │
        │   DB (SQLite / free  │                                  │
        │   Postgres: Neon)    │                                  │
        └──────────┬──────────┘                                  │
       reads       │                                             │
                   ▼                                             │
   customer ─▶ ┌──────────────────────┐    admin ─▶ /dashboard ─┘
  key / RapidAPI │  FastAPI (app/main)  │           (MRR, usage, coverage)
               │  /v1/companies/*     │
               └──────────────────────┘
                   ▲
   Stripe webhook ─┘  (POST /webhooks/stripe → auto-upgrade tier)
```

## Quickstart (local, no accounts needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m scripts.seed          # create tables + print demo API keys
SEC_USER_AGENT="Your Name you@example.com" python -m app.pipeline.run   # pull live SEC data
uvicorn app.main:app --reload   # serve the API
```

Then:

```bash
KEY=$(curl -s -X POST "http://localhost:8000/v1/keys?name=me" | python -c "import sys,json;print(json.load(sys.stdin)['api_key'])")

curl -H "X-API-Key: $KEY" "http://localhost:8000/v1/companies/AAPL"
curl -H "X-API-Key: $KEY" "http://localhost:8000/v1/companies/AAPL/fundamentals"
curl -H "X-API-Key: $KEY" "http://localhost:8000/v1/screen?min_revenue=100000000000&min_revenue_growth=0.1"

open "http://localhost:8000/dashboard?token=change-me"   # operator dashboard
```

Interactive docs: <http://localhost:8000/docs>.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/v1/companies` | key | List covered companies |
| `GET` | `/v1/companies/{ticker}` | key | Profile + latest fundamentals |
| `GET` | `/v1/companies/{ticker}/fundamentals` | key | Full annual time series |
| `GET` | `/v1/screen` | key | Screen by latest revenue / growth |
| `GET` | `/signup` | — | Public signup page: mint a free key + upgrade to Pro |
| `POST` | `/v1/keys` | — | Mint a free-tier key |
| `POST` | `/v1/keys/{id}/upgrade?token=` | admin | Manual tier bump |
| `POST` | `/webhooks/stripe` | signature | Stripe billing events → auto up/downgrade |
| `GET` | `/dashboard?token=` | admin | MIS dashboard |
| `GET` | `/health` | — | Liveness |

## Monetization — two live paths

**Option A — RapidAPI (recommended; zero billing code).** List the API on
[RapidAPI](https://rapidapi.com/provider). The marketplace charges customers,
proxies requests with a shared secret, and passes the subscriber's plan in
`X-RapidAPI-Subscription`. Set `RAPIDAPI_PROXY_SECRET` and the app trusts the
proxy, auto-provisions a key per subscriber, and maps the plan to free/pro
([app/auth.py](app/auth.py)). This is your **no-ads distribution channel**.

**Option B — Stripe (sell from your own page).** Create a recurring Price + a
**Payment Link** in Stripe with "client reference ID" enabled. Send buyers to it
with `?client_reference_id=<their API key>`. Set `STRIPE_WEBHOOK_SECRET`; on
payment, Stripe calls `POST /webhooks/stripe`, we verify the signature and flip
the key to `pro`. Cancellations downgrade automatically
([app/routers/billing.py](app/routers/billing.py)). No Stripe SDK needed.

**Step-by-step go-live runbooks:** [RUNBOOK_RAPIDAPI.md](RUNBOOK_RAPIDAPI.md) ·
[RUNBOOK_STRIPE.md](RUNBOOK_STRIPE.md). Set `REQUIRE_RAPIDAPI=true` to lock the
origin to the marketplace only (the Stripe path needs it left `false`).

## Coverage (how many companies)

Default: 20 large-cap tickers (`COVERAGE_TICKERS`) — fast first runs. To cover the
**full S&P 500** (~503 tickers), set `COVERAGE_FILE=app/data/sp500.txt`. Refresh
that list anytime from a public dataset:

```bash
python -m scripts.refresh_sp500   # regenerates app/data/sp500.txt
```

The deployed pipeline ([.github/workflows/ingest.yml](.github/workflows/ingest.yml))
already uses the S&P 500 file. A full run is slower and downloads much more from
SEC than the 20-ticker default, so it runs on the daily cron, not on every call.

## Tests

```bash
pytest -q   # 17 tests: pipeline math, config/coverage, auth (self-serve + RapidAPI), Stripe webhook, signup, API
```

## Deploy on free tiers

1. Free Postgres at [Neon](https://neon.tech) or [Supabase](https://supabase.com).
2. **Web API:** deploy to [Render](https://render.com) (free) via
   [render.yaml](render.yaml); set `DATABASE_URL`, `ADMIN_TOKEN`, and (when
   selling) `RAPIDAPI_PROXY_SECRET` / `STRIPE_WEBHOOK_SECRET`.
3. **Pipeline:** add `DATABASE_URL` + `SEC_USER_AGENT` as GitHub Actions secrets;
   the daily cron in [.github/workflows/ingest.yml](.github/workflows/ingest.yml)
   refreshes data for free.

## Swapping in a different niche

The engineering is niche-agnostic. To change data:
1. Replace the collector in [app/pipeline/ingest.py](app/pipeline/ingest.py).
2. Re-shape the product tables in [app/models.py](app/models.py) and the
   enrichment in [app/pipeline/enrich.py](app/pipeline/enrich.py).
3. Adjust the product routes in [app/routers/companies.py](app/routers/companies.py).
4. Auth, metering, billing, dashboard, deploy, and CI all stay the same.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). Found a security issue? Please follow
[SECURITY.md](SECURITY.md) rather than opening a public issue.

## License

[MIT](LICENSE) © Ekam Bindra.

Data is derived from public **SEC EDGAR** filings (U.S. government, public
domain). It is provided **as is**, without warranty, and is **not investment
advice**.
