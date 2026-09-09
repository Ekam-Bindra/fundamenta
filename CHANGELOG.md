# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims
to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]
- Open-source project health: LICENSE (MIT), CONTRIBUTING, CODE_OF_CONDUCT,
  SECURITY, issue/PR templates, ruff + pre-commit config, README badges.

## [1.0.0] - 2026-09-08
### Added
- FastAPI service exposing SEC company fundamentals: `/v1/companies`,
  `/v1/companies/{ticker}`, `/v1/companies/{ticker}/fundamentals`, `/v1/screen`.
- Data pipeline: SEC EDGAR XBRL ingest → per-fiscal-year metrics
  (net margin, revenue growth, ROE).
- API-key auth with per-tier daily rate limits; operator dashboard with
  estimated MRR.
- Two billing paths: RapidAPI proxy (marketplace) and Stripe webhook.
- Public `/signup` page and a self-serve free-key flow.
- **Zero-signup mode:** committed data snapshot (`app/data/fundamentals.json`)
  loaded on startup; the daily GitHub Action refreshes and commits it — no
  external database required.
- S&P 500 coverage via `app/data/sp500.txt` (refreshable with
  `python -m scripts.refresh_sp500`).
- Free-tier deploy config (Render + optional Neon Postgres) and CI.

### Fixed
- Scheduled ingest no longer crashes when `DATABASE_URL` is unset (empty value
  falls back to SQLite; the CI job skips cleanly without `SEC_USER_AGENT`).
