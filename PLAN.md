# Implementation Plan — Data API as a side-income business

Constraints this plan optimizes for (your stated choices):
**free tiers only · real side income · solo developer · ~5-week MVP.**

> **Status:** the shipped reference build is a **Company Fundamentals API on SEC
> EDGAR** with both billing paths wired (RapidAPI marketplace + Stripe webhook).
> The sections below remain the framework for validating/swapping niches — the
> code is niche-agnostic, so most of this applies to whatever you sell.

---

## 0. The honest economics (read this first)

- **No advertising ≠ no distribution.** Your distribution is the **RapidAPI
  marketplace** (developers search it for data) plus **API docs/SEO**. That is a
  legitimate "no paid ads" channel, but it is competitive — you win by serving
  data that is *annoying to collect yourself* and *clean*.
- **Timeline reality:** the 5 weeks below produce a deployed, listable product.
  Expect first dollars in **weeks-to-months**, not days. Revenue compounds with
  reviews, ranking, and the number of distinct datasets you list.
- **Realistic early target (unverified, illustrative):** a single well-chosen
  API on RapidAPI commonly does **$0–50/mo** for months, then **$50–500/mo** if
  it fills a real gap. Income scales by *listing more APIs*, not by one going
  viral. Treat the platform here as a factory for producing many small APIs.

---

## 1. Niche selection — the make-or-break step

The code is done; **picking what to sell is the actual work.** Do this in Week 1.

### Demand-validation checklist (a niche must pass ≥3)
- [ ] People **already ask** for this data (search RapidAPI, Reddit, Stack
      Overflow, "is there an API for X").
- [ ] The raw source is **annoying to collect** (scattered, messy, paginated,
      rate-limited) — your cleaning *is* the value.
- [ ] It is **legal & ToS-friendly** to redistribute (public/open data, or an
      API whose terms allow it). Avoid scraping sites that forbid it.
- [ ] It **changes over time**, so customers need to keep calling (recurring
      revenue), not buy once.
- [ ] Existing APIs are **missing, expensive, or low-quality** (room to compete).

### Candidate niches (free/legal sources, ranked by my read)
| Niche | Free source | Why it can sell | Watch-out |
|---|---|---|---|
| **Gov / regulatory data** ✅ shipped | SEC EDGAR, FDA, data.gov | Clean structured access is genuinely painful | Volume/parsing work |
| **Tech-trend signals** | Hacker News API | Devs/VCs/marketers want momentum signals | Must prove the signal is useful |
| **Public transit (GTFS)** | Agency GTFS feeds | App devs need normalized multi-city data | Per-agency licensing |
| **Air quality / weather-derived indices** | OpenAQ, Open-Meteo | Enriched indices add value over raw feeds | Base data is free → must enrich |
| **Open sports / esports stats** | Public league/stat APIs | Hobby-dev demand, fantasy apps | Check each source's terms |
| **Crypto on-chain metrics** | Public RPC / explorers | Big dev audience | Crowded; differentiate hard |

> Pick **one** to start. The reference build is a working template for any of them.

---

## 2. Free-tier stack (all $0)

| Concern | Choice | Cost |
|---|---|---|
| Language/web | Python + FastAPI | $0 |
| Local DB | SQLite | $0 |
| Prod DB | Neon or Supabase Postgres (free tier) | $0 |
| API hosting | Render free web service (or Fly.io free allowance) | $0 |
| Scheduled pipeline | GitHub Actions cron | $0 |
| CI/tests | GitHub Actions | $0 |
| Distribution + billing | RapidAPI marketplace | $0 to list (rev-share) |
| Direct billing (optional) | Stripe (pay-as-you-go) | $0 fixed |

---

## 3. Five-week build plan

| Week | Goal | Key tasks | Definition of done |
|---|---|---|---|
| **1** | Validate + design | Run the validation checklist on 3 niches; pick one; confirm source terms; design endpoints + schema | A one-paragraph "why this niche" + endpoint list |
| **2** | Data pipeline (DS) | Build the collector; cleaning/enrichment; schedule it; backfill history | `python -m app.pipeline.run` populates the DB on a cron |
| **3** | API + auth (eng) | Endpoints, API-key auth, per-tier rate limits, free/pro tiers; deploy to Render + Neon | Live URL serving real data behind keys |
| **4** | MIS + monetization | Dashboard (usage, MRR); list on RapidAPI; wire upgrade webhook; write API docs | Listed, payable, observable |
| **5** | Harden + iterate | Tests, monitoring/alerting, error handling, a generous free tier as the on-ramp, gather first-user feedback | CI green; first external caller |

---

## 4. Monetization mechanics (already scaffolded)

- **Free tier** (`FREE_DAILY_LIMIT`, default 100/day): the on-ramp; gets you
  listed and indexed, lets devs try before buying.
- **Pro tier** (`PRO_DAILY_LIMIT`, `PRO_PRICE_USD`, default $25/mo): the revenue.
- Enforcement lives in [app/auth.py](app/auth.py); upgrades happen via
  `POST /v1/keys/{id}/upgrade` ([app/routers/keys.py](app/routers/keys.py)),
  which you call from your **RapidAPI or Stripe webhook** on successful payment.
- The dashboard's **estimated MRR = pro customers × price**
  ([app/routers/dashboard.py](app/routers/dashboard.py)) is your north-star metric.

**Scaling the business = listing more niches**, each a copy of this template with
a different collector. Five small APIs at $100/mo each beats betting on one.

---

## 5. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Chosen niche has no demand | No revenue | Validate **before** Week 2; be willing to drop it |
| Source API changes / blocks you | Pipeline breaks | Pick stable public sources; add monitoring + alerts in Week 5 |
| ToS / licensing violation | Legal + takedown | Only redistribute data you're allowed to; document the source's terms |
| Free-tier host sleeps | Cold-start latency | Acceptable early; upgrade only once revenue justifies it |
| Commoditized data | Race to the bottom | Compete on cleaning/enrichment/uptime, not raw access |

---

## 6. Human dependencies (block *revenue*, not the *build*)

| Dependency | Blocks | You can still… |
|---|---|---|
| RapidAPI provider account | Listing/selling | Build + run the whole API locally |
| Stripe account (if direct) | Direct billing | Use RapidAPI's billing instead |
| Neon/Supabase + Render signup | Public deploy | Develop entirely on SQLite |
| Domain (optional) | Branding | Use the platform-provided URL |
