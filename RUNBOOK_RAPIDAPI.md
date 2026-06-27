# Go-Live Runbook — Listing the Fundamentals API on RapidAPI

This runbook takes the project from "runs locally" to "publicly listed and able
to charge customers" via the [RapidAPI](https://rapidapi.com) marketplace.
RapidAPI is the **no-ads distribution channel**: developers discover your API by
searching the marketplace, and RapidAPI handles auth, quotas, and billing for
you. Your code already supports this (see [app/auth.py](app/auth.py)).

> **What this runbook does NOT require:** a Stripe account, a payment page, or
> any ad spend. RapidAPI is the storefront and the cashier.

> **Accuracy note:** RapidAPI's dashboard labels and exact menu paths change over
> time, and its revenue-share percentage is set by your provider agreement —
> verify both in the live UI. Every step below is described by the *outcome* so
> it survives UI changes. Steps that touch *this repo's* code/config are exact.

---

## How it works (the one paragraph to internalize)

```
 developer ──HTTPS──▶ RapidAPI proxy ──HTTPS──▶ your Render origin (this app)
                         │  adds headers:           │
                         │   X-RapidAPI-Proxy-Secret │  app/auth.py verifies the
                         │   X-RapidAPI-User         │  secret, identifies the
                         │   X-RapidAPI-Subscription │  user, maps plan→tier,
                         └───────────────────────────┘  auto-provisions a key
   RapidAPI bills the developer and pays you the remainder.
```

Your origin trusts a request **only** if `X-RapidAPI-Proxy-Secret` matches
`RAPIDAPI_PROXY_SECRET`. The plan name in `X-RapidAPI-Subscription` decides the
tier: anything in `RAPIDAPI_PAID_PLANS` (`PRO,ULTRA,MEGA,CUSTOM`) → `pro`
(`PRO_DAILY_LIMIT`), everything else (RapidAPI's free `BASIC` plan) → `free`
(`FREE_DAILY_LIMIT`). Logic: [app/auth.py:51](app/auth.py) `_rapidapi_tier` /
`_provision_rapidapi_key`.

---

## Prerequisites

- [ ] A RapidAPI account, then access the **Provider** side (provider dashboard /
      "My APIs" / "Add New API").
- [ ] This repo deployed to a public HTTPS origin (Phase 1 below).
- [ ] A free managed Postgres (Neon or Supabase) — SQLite does not survive a
      multi-instance / restart-y free host.
- [ ] A real `SEC_USER_AGENT` value (your name + email) — SEC blocks anonymous bots.

---

## Phase 1 — Deploy the origin publicly

The origin must be live and serving real data *before* you point RapidAPI at it.

### 1.1 Create the database
1. Create a free Postgres at [Neon](https://neon.tech) (or Supabase).
2. Copy the connection string → this is your `DATABASE_URL`
   (`postgresql://user:pass@host/db`).

### 1.2 Deploy the web service (Render free tier)
1. Push this repo to GitHub.
2. On [Render](https://render.com): **New → Blueprint**, point at the repo;
   it reads [render.yaml](render.yaml).
3. Set environment variables in the Render dashboard:
   | Var | Value |
   |---|---|
   | `DATABASE_URL` | your Neon URL |
   | `ADMIN_TOKEN` | a long random string (protects `/dashboard`) |
   | `RAPIDAPI_PROXY_SECRET` | leave blank for now — filled in Phase 3 |
   | `RUN_SCHEDULER` | `false` (the pipeline runs in GitHub Actions) |
4. Deploy. Confirm: `https://<your-service>.onrender.com/health` → `{"status":"ok"}`.

### 1.3 Schedule the data pipeline (free)
1. In the GitHub repo: **Settings → Secrets and variables → Actions** → add
   `DATABASE_URL` (same Neon URL) and `SEC_USER_AGENT` ("Your Name you@email.com").
2. **Actions tab → "ingest" workflow → Run workflow** to populate data now
   (don't wait for the daily cron in [.github/workflows/ingest.yml](.github/workflows/ingest.yml)).
3. Confirm data is live:
   `curl https://<your-service>.onrender.com/v1/companies` should return `401`
   (auth required = good), and the admin dashboard
   `…/dashboard?token=<ADMIN_TOKEN>` should show "Companies covered" > 0.

> **Render free tier sleeps** after ~15 min idle (cold start ~30–60s). RapidAPI's
> first call after idle may be slow or time out. Mitigations: (a) accept it
> early; (b) add a free uptime pinger (e.g. UptimeRobot) hitting `/health` every
> 5 min; (c) upgrade Render once revenue justifies it.

---

## Phase 2 — Create the API on RapidAPI

In the **Provider Dashboard → Add New API**:

1. **Name:** e.g. "Company Fundamentals API (SEC EDGAR)".
2. **Short description:** "Clean, normalized US company fundamentals — revenue,
   margins, YoY growth, ROE — parsed from SEC EDGAR filings. No XBRL wrangling."
3. **Category:** Finance / Data.
4. **Base URL:** `https://<your-service>.onrender.com`
5. Add each endpoint (method, path, params, an example response). Pull example
   payloads straight from your live origin:

   | Method | Path | Key params |
   |---|---|---|
   | GET | `/v1/companies` | `limit` |
   | GET | `/v1/companies/{ticker}` | `ticker` |
   | GET | `/v1/companies/{ticker}/fundamentals` | `ticker` |
   | GET | `/v1/screen` | `min_revenue`, `min_revenue_growth`, `limit` |

   Do **not** add `/v1/keys`, `/dashboard`, or `/webhooks/*` to the RapidAPI
   listing — those are origin-only management routes.

> Tip: generate example responses with a real call (use a self-serve key against
> your origin) and paste the JSON into RapidAPI's example field — good examples
> materially increase conversion.

---

## Phase 3 — Wire the proxy-secret (the security gate)

This is the step that makes RapidAPI's identity trustworthy.

1. In the API's **Security / settings**, find the **secret header** value RapidAPI
   injects on every proxied request. It is sent as header
   **`X-RapidAPI-Proxy-Secret`** (confirm the exact name shown in your dashboard).
2. Copy that secret → set it as `RAPIDAPI_PROXY_SECRET` in **Render** → redeploy.
3. Verify the gate works (see Phase 5).

> **If your dashboard names the plan header differently** than
> `X-RapidAPI-Subscription`, change the param name `x_rapidapi_subscription` in
> [app/auth.py:74](app/auth.py) to match — this is the one integration point that
> varies by account/version.

---

## Phase 4 — Define plans & pricing

Create subscription plans in **Plans & Pricing**. A proven starting structure:

| RapidAPI plan | Price | RapidAPI quota | Maps to (our tier) | Our daily limit |
|---|---|---|---|---|
| **BASIC** (free) | $0 | e.g. 100 req/day, hard limit | `free` | `FREE_DAILY_LIMIT` (100) |
| **PRO** | e.g. $29/mo | e.g. 10,000 req/day | `pro` | `PRO_DAILY_LIMIT` (10,000) |
| **ULTRA** | e.g. $99/mo | e.g. 100,000 req/day | `pro` | (raise limit — see note) |

**Tier mapping is automatic:** RapidAPI sends the plan name in
`X-RapidAPI-Subscription`; `BASIC` → `free`, and `PRO/ULTRA/MEGA/CUSTOM` → `pro`
(config `RAPIDAPI_PAID_PLANS`). No code change needed to add a paid tier whose
name is already in that list.

**Make RapidAPI the source of truth for quotas.** RapidAPI enforces the billable
limit; our internal limit is only a backstop (per RapidAPI user, per day). So set
`PRO_DAILY_LIMIT` in Render **at or above your highest paid plan's daily quota**
(e.g. `100000`) so your backstop never blocks a paying customer before RapidAPI's
meter does. Keep `FREE_DAILY_LIMIT` aligned with the BASIC quota.

**Pricing strategy (realistic):** price the paid plan in the $10–50/mo range to
start; you can raise once you have reviews and usage. Add a generous BASIC tier —
it's your funnel and your marketplace-SEO signal.

---

## Phase 5 — Test as a real subscriber (before publishing)

1. From the **consumer** side of RapidAPI, find your (still private) API and
   **subscribe to BASIC**.
2. Use RapidAPI's built-in "Test Endpoint" console, or copy the generated code
   snippet. A direct call looks like:

   ```bash
   curl "https://<your-rapidapi-host>/v1/companies/AAPL" \
     -H "X-RapidAPI-Key: <your-consumer-key>" \
     -H "X-RapidAPI-Host: <your-rapidapi-host>"
   ```
   (RapidAPI adds `X-RapidAPI-Proxy-Secret`, `X-RapidAPI-User`, and
   `X-RapidAPI-Subscription` server-side — you never send those.)

3. **Verify the gate & mapping:**
   - [ ] Call via RapidAPI on BASIC → `200`, and on your `…/dashboard` the key
         `rapidapi:<user>` appears with tier `free`.
   - [ ] Calling your **origin directly** without the secret →
         `401` (no key) — confirms direct traffic can't impersonate RapidAPI.
   - [ ] Calling your origin directly *with a wrong* `X-RapidAPI-Proxy-Secret` →
         `403` ("Invalid RapidAPI proxy secret").
   - [ ] Upgrade your test subscription to **PRO** → next call provisions/updates
         the key to tier `pro` automatically (verify on the dashboard).

If all four pass, the integration is correct.

---

## Phase 6 — Listing quality (this is your marketing, since there are no ads)

Inside the marketplace, a good listing *is* your distribution. Invest here:

- [ ] **Clear name + one-line value prop** ("SEC fundamentals without the XBRL").
- [ ] **Long description**: what data, source (SEC EDGAR), coverage (N tickers),
      update cadence (daily), and 2–3 concrete use cases (fintech dashboards,
      screeners, research bots).
- [ ] **Working examples for every endpoint** (paste real JSON).
- [ ] **A short "Getting started" tutorial** in the API's docs section.
- [ ] **Logo + category + tags** (finance, stocks, fundamentals, SEC, edgar) —
      tags drive in-marketplace search discovery.
- [ ] Set a **support email**.

---

## Phase 7 — Publish

1. Set the API visibility to **Public**.
2. Submit for review if your account requires it; address any feedback.
3. Once public, share the marketplace URL in places your buyers already are
   (relevant subreddits, dev forums, a "Built with" note) — still no paid ads.

---

## Phase 8 — Post-launch operations

| Concern | How | Where |
|---|---|---|
| Revenue & usage | Watch estimated MRR, calls, customers by tier | `…/dashboard?token=…` |
| Data freshness | Daily cron must stay green | GitHub Actions → "ingest" |
| Origin uptime | `/health` monitor + alert | UptimeRobot (free) |
| SEC compliance | Keep `SEC_USER_AGENT` real; stay <10 req/s (we sleep 0.2s/call) | [app/pipeline/ingest.py](app/pipeline/ingest.py) |
| Grow coverage | Set `COVERAGE_FILE=app/data/sp500.txt` (S&P 500), or edit `COVERAGE_TICKERS`; refresh via `python -m scripts.refresh_sp500` | env on Render + Actions |
| Support | Respond to RapidAPI messages/reviews quickly | RapidAPI inbox |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every RapidAPI call → `403 Invalid RapidAPI proxy secret` | `RAPIDAPI_PROXY_SECRET` on Render ≠ RapidAPI's secret | Copy the exact secret from RapidAPI security settings; redeploy |
| RapidAPI calls → `401 Missing X-API-Key` | Proxy secret header not arriving (name mismatch) | Confirm header name; adjust `x_rapidapi_proxy_secret` param in [app/auth.py](app/auth.py) |
| Paid subscriber still rate-limited as free | Plan name not in `RAPIDAPI_PAID_PLANS`, or `PRO_DAILY_LIMIT` too low | Add the plan name to `RAPIDAPI_PAID_PLANS`; raise `PRO_DAILY_LIMIT` ≥ plan quota |
| First call after idle times out | Render free tier cold start | Add `/health` pinger or upgrade Render |
| `/v1/companies` returns empty / 404 for tickers | Pipeline never ran against prod DB | Run the "ingest" workflow; confirm `DATABASE_URL` matches between Render and Actions |
| SEC pipeline 403/blocked | Missing/!real `SEC_USER_AGENT` | Set a real name+email; keep request rate low |

---

## Appendix — Optional hardening: RapidAPI-only origin (built in)

By default the origin also accepts **self-serve `X-API-Key`** traffic (a second
sales channel). For a **RapidAPI-exclusive** launch — rejecting any direct origin
traffic so nobody bypasses RapidAPI's billing — this is now a one-line config:

**Set `REQUIRE_RAPIDAPI=true` on Render.** Any request without a RapidAPI proxy
secret then returns `403 "Access via the RapidAPI marketplace only"`. The guard
lives at the top of `get_api_key` in [app/auth.py](app/auth.py); it's covered by
`test_require_rapidapi_blocks_direct_traffic` in
[tests/test_api.py](tests/test_api.py).

Leave it `false` (the default) if you also sell direct via Stripe — see
[app/routers/billing.py](app/routers/billing.py).

| `REQUIRE_RAPIDAPI` | Self-serve `X-API-Key` | RapidAPI traffic |
|---|---|---|
| `false` (default) | ✅ allowed | ✅ allowed |
| `true` | 🚫 `403` | ✅ allowed |

---

## Final go-live checklist

- [ ] Origin deployed; `/health` green; data populated (dashboard shows coverage).
- [ ] `RAPIDAPI_PROXY_SECRET` set on Render and matches RapidAPI.
- [ ] API created on RapidAPI with base URL + all 4 product endpoints + examples.
- [ ] Plans defined; quotas aligned with `FREE_DAILY_LIMIT` / `PRO_DAILY_LIMIT`.
- [ ] All four Phase-5 verification checks pass.
- [ ] Listing has description, examples, tutorial, logo, tags, support email.
- [ ] Daily ingest workflow green; uptime monitor on `/health`.
- [ ] API set to Public.
