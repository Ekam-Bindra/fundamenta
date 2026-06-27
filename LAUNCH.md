# Launch Checklist — from finished code to live, paying API

This is the linear path from "the code works on my laptop" to "it's deployed and
can charge customers." Every service used is **free**. Budget ~2–3 hours of
setup, mostly clicking through dashboards.

**Accounts you'll create (all free):** GitHub, [Neon](https://neon.tech) (Postgres),
[Render](https://render.com) (hosting), and **RapidAPI** and/or **Stripe** for billing.

> Detailed billing steps live in [RUNBOOK_RAPIDAPI.md](RUNBOOK_RAPIDAPI.md) and
> [RUNBOOK_STRIPE.md](RUNBOOK_STRIPE.md). This file is the spine that orders them.

---

## Step 0 — Run it locally (10 min, no accounts)

Confirms the whole thing works before you deploy anything.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.seed                                   # prints demo API keys
SEC_USER_AGENT="Your Name you@example.com" python -m app.pipeline.run
uvicorn app.main:app --reload
```

Open and verify:
- <http://localhost:8000/docs> — interactive API
- <http://localhost:8000/signup> — public signup page
- `http://localhost:8000/dashboard?token=change-me` — operator dashboard (shows companies covered)

Run the tests once: `pytest -q` → **17 passed**.

---

## Step 1 — Push to GitHub (10 min)

Render and the data pipeline both pull from GitHub.

```bash
git init -b main
git add -A
git commit -m "Company Fundamentals API"
# create the repo (GitHub CLI), or make one on github.com and use its URL:
gh repo create company-fundamentals-api --private --source=. --push
```

> `.env` and `*.db` are already git-ignored, so no secrets/data get committed.

---

## Step 2 — Free Postgres on Neon (10 min)

1. Create a project at [neon.tech](https://neon.tech).
2. Copy the **connection string** (looks like
   `postgresql://user:pass@ep-xxx.aws.neon.tech/dbname?sslmode=require`).
3. Keep it handy — this is your `DATABASE_URL`. (The Postgres driver is already
   in [requirements.txt](requirements.txt).)

---

## Step 3 — Deploy the API on Render (15 min)

1. Generate a strong admin token:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. On [Render](https://render.com): **New → Blueprint**, select your GitHub repo
   (it reads [render.yaml](render.yaml)).
3. Set environment variables in the Render dashboard:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | your Neon string (Step 2) |
   | `ADMIN_TOKEN` | the token from Step 3.1 |
   | `RUN_SCHEDULER` | `false` |
   | `RAPIDAPI_PROXY_SECRET` | *(blank for now — Step 5A)* |
   | `STRIPE_WEBHOOK_SECRET` | *(blank for now — Step 5B)* |

4. Deploy. Confirm `https://<your-service>.onrender.com/health` → `{"status":"ok"}`.

> Free Render services **sleep** after ~15 min idle (cold start 30–60s). Fine to
> start; add a free [UptimeRobot](https://uptimerobot.com) ping on `/health` later.

---

## Step 4 — Load the data (10 min)

The API is live but empty until the pipeline runs against Neon.

1. In the GitHub repo: **Settings → Secrets and variables → Actions → New secret**:
   - `DATABASE_URL` = the same Neon string
   - `SEC_USER_AGENT` = `"Your Name you@example.com"` (**required** — SEC blocks anonymous bots)
2. **Actions tab → "ingest" workflow → Run workflow** (don't wait for the daily cron).
3. The deployed workflow covers the **full S&P 500** ([ingest.yml](.github/workflows/ingest.yml))
   — the first run takes several minutes and downloads a lot from SEC. To start
   smaller, edit that file to remove the `COVERAGE_FILE` line (falls back to 20 tickers).
4. Verify: `https://<your-service>.onrender.com/dashboard?token=<ADMIN_TOKEN>` shows
   "Companies covered" > 0.

You now have a **live, public, working data API.** Everything below is monetization.

---

## Step 5 — Turn on billing (pick one or both)

| | **RapidAPI** (Step 5A) | **Stripe** (Step 5B) |
|---|---|---|
| Brings you customers? | ✅ marketplace search | ❌ you drive traffic |
| Keeps more per $? | ~ platform rev-share | ✅ ~payment fee only |
| Best for | discovery, fastest first sale | higher-margin direct deals |

**Recommendation:** start with **RapidAPI** (it's your no-ads distribution), add
Stripe later if you want a direct channel. Many run both.

### Step 5A — RapidAPI
Follow [RUNBOOK_RAPIDAPI.md](RUNBOOK_RAPIDAPI.md). The essentials:
1. Create the API (base URL = your Render URL; add the 4 `/v1/...` endpoints).
2. Copy RapidAPI's **proxy secret** → set `RAPIDAPI_PROXY_SECRET` on Render → redeploy.
3. Define plans (BASIC free, PRO paid) — tiers map automatically.
4. Subscribe to your own API and run the 4 verification checks. Publish.
5. *(Optional)* Set `REQUIRE_RAPIDAPI=true` on Render to refuse all non-marketplace traffic.

### Step 5B — Stripe (direct sales via your `/signup` page)
Follow [RUNBOOK_STRIPE.md](RUNBOOK_STRIPE.md). The essentials (keep `REQUIRE_RAPIDAPI=false`):
1. Create a recurring Price + a **Payment Link** in Stripe.
2. Add a webhook to `https://<your-service>.onrender.com/webhooks/stripe`
   (events: `checkout.session.completed`, `customer.subscription.deleted`,
   `customer.subscription.updated`); copy its `whsec_...`.
3. On Render set `STRIPE_WEBHOOK_SECRET=<whsec_...>` and
   `STRIPE_PAYMENT_LINK=<your link>` → redeploy.
4. Send buyers to `https://<your-service>.onrender.com/signup`. Test with card
   `4242 4242 4242 4242`; confirm the key flips to `pro` on the dashboard.

---

## Step 6 — Get traffic without ads

- **RapidAPI listing** is itself discovery — invest in its description, examples, tags.
- **Free tier as funnel:** `/signup` lets people succeed before paying.
- **SEO/content:** a page like "free SEC fundamentals API", endpoint docs.
- **Be where devs are:** Show HN, relevant subreddits, free API directories.

---

## Step 7 — Operate (ongoing)

| Task | How |
|---|---|
| Watch revenue/usage | `…/dashboard?token=…` |
| Keep data fresh | the daily "ingest" Action stays green |
| Keep origin awake | UptimeRobot on `/health` |
| Refresh the S&P 500 list | `python -m scripts.refresh_sp500`, commit |
| Expand/trim coverage | edit `COVERAGE_FILE` / `COVERAGE_TICKERS` |
| Support customers | reply on RapidAPI / your support email |

---

## Reality check

These steps build and launch the **machine**. Revenue from organic/marketplace
channels typically ramps over **2–6 months**, and scales more by **listing more
datasets** (each a copy of this template) than by one going viral. Price the paid
tier in the $10–50/mo range to start; raise it once you have reviews and usage.

---

## Quick reference — environment variables

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | Render + Actions | Neon Postgres connection |
| `ADMIN_TOKEN` | Render | Protects `/dashboard` + admin routes |
| `SEC_USER_AGENT` | Actions | Required by SEC (your name + email) |
| `COVERAGE_FILE` | Actions (preset) | `app/data/sp500.txt` for S&P 500 |
| `RAPIDAPI_PROXY_SECRET` | Render | Enables/trusts the RapidAPI path |
| `REQUIRE_RAPIDAPI` | Render | `true` = marketplace-only |
| `STRIPE_WEBHOOK_SECRET` | Render | Enables `POST /webhooks/stripe` |
| `STRIPE_PAYMENT_LINK` | Render | Shows the upgrade button on `/signup` |
