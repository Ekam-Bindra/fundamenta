# Go-Live Runbook — Selling the Fundamentals API directly via Stripe

This runbook takes the project to **direct sales from your own page**: customers
mint a free API key, pay through a Stripe **Payment Link**, and a signature-
verified webhook auto-upgrades their key to `pro`. Your code already supports
this — see [app/routers/billing.py](app/routers/billing.py).

> **Honest tradeoff vs. RapidAPI** (read [RUNBOOK_RAPIDAPI.md](RUNBOOK_RAPIDAPI.md)
> first if you haven't): Stripe is a **payment rail, not a storefront**. It keeps
> more of each dollar (Stripe fee ≈ 2.9% + 30¢, US — *verify your current rate*;
> no marketplace revenue share), **but it does not bring you customers**. RapidAPI's
> marketplace is your no-ads distribution; with Stripe you must drive traffic to
> your page yourself (Phase 7 covers no-ad options). Many run **both**: RapidAPI
> for discovery, Stripe for higher-margin direct deals.

> **Accuracy note:** Stripe's dashboard labels shift over time and its fees are
> set by your account/region — verify both live. Steps that touch *this repo's*
> code/config are exact; verified against [app/routers/billing.py](app/routers/billing.py).

---

## How it works

```
 customer ─▶ your signup page ─▶ POST /v1/keys ───────────▶ gets key  sk_...
                  │
                  ▼  redirect to Payment Link with ?client_reference_id=sk_...
            Stripe Checkout ──pays──▶ Stripe
                  │
                  ▼  POST /webhooks/stripe   (checkout.session.completed)
            app/routers/billing.py: verify signature → look up key by
            client_reference_id → set tier=pro, store customer/subscription ids
```

Cancellation later arrives as `customer.subscription.deleted` (or an `updated`
event with status `canceled` / `unpaid` / `incomplete_expired`) → the key is
downgraded to `free`. Logic: [app/routers/billing.py:92](app/routers/billing.py).

> **Dependency:** the Stripe path uses **self-serve `X-API-Key`** auth, so
> `REQUIRE_RAPIDAPI` must stay **`false`** (the default). If you locked the origin
> to RapidAPI-only, Stripe customers' keys won't work.

---

## Prerequisites

- [ ] A Stripe account (start in **Test mode** — toggle in the dashboard).
- [ ] This repo deployed to a public HTTPS origin (Phase 1 of
      [RUNBOOK_RAPIDAPI.md](RUNBOOK_RAPIDAPI.md) — Neon + Render + GitHub Actions
      ingest). The webhook needs a public URL.
- [ ] `REQUIRE_RAPIDAPI=false` (default).
- [ ] (Recommended) the [Stripe CLI](https://docs.stripe.com/stripe-cli) for local
      webhook testing.

---

## Phase 1 — Deploy the origin

Identical to [RUNBOOK_RAPIDAPI.md](RUNBOOK_RAPIDAPI.md) Phase 1. End state:
`https://<your-service>.onrender.com/health` → `{"status":"ok"}` and the ingest
workflow has populated data. Leave `STRIPE_WEBHOOK_SECRET` blank for now — until
it's set, `POST /webhooks/stripe` returns `503 "Stripe billing not configured"`
by design ([app/routers/billing.py:80](app/routers/billing.py)).

---

## Phase 2 — Create the product, price, and Payment Link (Test mode)

In the Stripe Dashboard (**Test mode**):

1. **Products → Add product:** name "Company Fundamentals API — Pro", add a
   **recurring** price (e.g. $29/month). Copy the **Price ID** (`price_...`) →
   optionally set it as `STRIPE_PRO_PRICE_ID` on Render (informational only).
2. **Payment Links → New link →** select that price → create.
3. On the link's settings, ensure it can carry a **client reference ID** (Payment
   Links accept it as a URL parameter — see Phase 4). Optionally enable
   **promotion codes** and **customer portal** for self-service cancellation.
4. Copy the Payment Link URL (looks like `https://buy.stripe.com/test_xxx`).

> **Why a Payment Link (not custom Checkout code)?** Zero code, no Stripe SDK to
> install, hosted + PCI-handled by Stripe. The webhook does all the work on our
> side.

---

## Phase 3 — Configure the webhook

1. **Developers → Webhooks → Add endpoint.**
2. **Endpoint URL:** `https://<your-service>.onrender.com/webhooks/stripe`
3. **Events to send** (exactly the ones we handle):
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
4. Create it, then **reveal the Signing secret** (`whsec_...`).
5. Set `STRIPE_WEBHOOK_SECRET=<whsec_...>` on **Render** → redeploy.

The endpoint now verifies every event's `Stripe-Signature` (HMAC-SHA256, 5-min
tolerance) and rejects anything unsigned/forged with `400`
([verify_stripe_signature](app/routers/billing.py:30)).

---

## Phase 4 — The signup → pay flow (built in)

The linkage between a paying customer and their API key is the
**`client_reference_id`** — the customer's API key string. This is handled by the
**built-in `GET /signup` page** ([app/routers/signup.py](app/routers/signup.py),
[app/templates/signup.html](app/templates/signup.html)); you don't write any HTML.

**To activate it:** set `STRIPE_PAYMENT_LINK=<your Payment Link URL>` on Render
and redeploy. Then send buyers to `https://<your-service>.onrender.com/signup`.

What the page does:
1. Visitor clicks **Generate free API key** → it calls `POST /v1/keys` and shows
   the key (with a copy button and a ready-to-run `curl` example), warning them
   to save it — it's their `X-API-Key`.
2. The **Upgrade to Pro** button activates, pointing at your Payment Link with
   `?client_reference_id=<their key>` appended (URL-encoded). Our `sk_...` keys
   are URL-safe, satisfying Stripe's `client_reference_id` rules.
3. They pay → `checkout.session.completed` fires → the webhook flips that key to
   `pro`.

If `STRIPE_PAYMENT_LINK` is unset, `/signup` still works as a free-key page (the
upgrade button is hidden) — handy before billing is live. Covered by
`test_signup_page_renders` in [tests/test_api.py](tests/test_api.py).

---

## Phase 5 — Test end-to-end in Test mode

**Option A — locally with the Stripe CLI (fastest):**

```bash
# terminal 1: run the API with the CLI's webhook secret
stripe listen --forward-to localhost:8000/webhooks/stripe
# copy the whsec_... it prints, then:
STRIPE_WEBHOOK_SECRET=whsec_xxx uvicorn app.main:app --reload

# terminal 2: mint a key, then simulate the purchase event for it
KEY=$(curl -s -X POST "localhost:8000/v1/keys?name=cli-test" | python -c "import sys,json;print(json.load(sys.stdin)['api_key'])")
stripe trigger checkout.session.completed \
  --add checkout_session:client_reference_id="$KEY"
# verify the upgrade:
open "http://localhost:8000/dashboard?token=change-me"   # the key should now be 'pro'
```

**Option B — real test checkout:** open your signup page, click through, pay with
the Stripe **test card `4242 4242 4242 4242`** (any future expiry, any CVC). Then:

- [ ] Webhook delivery shows `200` in **Developers → Webhooks → your endpoint**.
- [ ] On `…/dashboard?token=…`, the key's tier is `pro` and **Estimated MRR** rose.
- [ ] Calling a product route with that key returns the higher (`pro`) rate limit.
- [ ] In Stripe, **cancel** the test subscription → a `subscription.deleted`/
      `updated` event arrives → the key downgrades to `free` on the dashboard.

These mirror the automated coverage in `test_webhook_upgrades_key_on_checkout_completed`
([tests/test_billing.py](tests/test_billing.py)) — run `pytest -q` anytime.

---

## Phase 6 — Go live

1. Flip the Stripe Dashboard to **Live mode**.
2. Recreate the **product/price/Payment Link** in Live mode (test-mode objects
   don't carry over). Update your signup page's `PAYMENT_LINK`.
3. Create a **Live-mode webhook** at the same `/webhooks/stripe` URL; copy its
   **live** `whsec_...` and update `STRIPE_WEBHOOK_SECRET` on Render → redeploy.
4. Do one real low-value purchase (or a $0 trial) to confirm the live path, then
   refund it from the dashboard.

---

## Phase 7 — Distribution without ads (the part Stripe doesn't do for you)

Stripe gave you a checkout, not customers. To get traffic for free:

- **Free tier as the funnel** — `POST /v1/keys` gives a usable free key; let people
  succeed before asking for money.
- **SEO content** — "free SEC fundamentals API", comparison posts, endpoint docs
  pages indexable by Google.
- **Developer directories** — list on free API directories (e.g. PublicAPIs,
  API directories, ProductHunt, Show HN).
- **Answer where buyers ask** — relevant subreddits / StackOverflow / Discords,
  with a genuine solution (not spam).
- **Also list on RapidAPI** — run both channels; the marketplace's search is the
  cheapest distribution you'll get. See [RUNBOOK_RAPIDAPI.md](RUNBOOK_RAPIDAPI.md).

---

## Phase 8 — Post-launch operations

| Concern | How | Where |
|---|---|---|
| Revenue & active subs | Estimated MRR, pro customers | `…/dashboard?token=…` + Stripe dashboard |
| Webhook health | Delivery attempts/failures, retries | Stripe → Developers → Webhooks |
| Failed renewals (dunning) | Stripe Smart Retries; optionally handle `invoice.payment_failed` | Stripe Billing settings |
| Self-service cancel/update | Enable the **Customer Portal** | Stripe → Settings → Billing |
| Refunds / disputes | Issue from dashboard; key auto-downgrades on subscription end | Stripe |
| Data freshness | Daily ingest cron green | GitHub Actions |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `503 Stripe billing not configured` | `STRIPE_WEBHOOK_SECRET` unset on origin | Set it on Render (use the secret matching test/live mode) → redeploy |
| `400 Invalid signature` | Wrong secret, or body altered by a proxy | Use the exact `whsec_` for that mode; ensure raw body isn't rewritten (Render is fine) |
| Webhook `200` but key not upgraded | `client_reference_id` missing or didn't match a key | Confirm the Payment Link carried `?client_reference_id=sk_...` and that key exists in the **same** DB the webhook writes to |
| `client_reference_id` rejected by Stripe | Illegal characters / >200 chars | Our `sk_...` keys are URL-safe and short — don't wrap/encode them beyond `encodeURIComponent` |
| Test worked, live didn't | Using test-mode secret/link in live | Recreate product/link/webhook in Live mode; swap to live `whsec_` |
| Cancellation didn't downgrade | Event type not subscribed, or sub id mismatch | Subscribe `customer.subscription.deleted` + `updated`; the key must have `stripe_subscription_id` set (it's stored on upgrade) |

---

## Security & idempotency notes

- **Signature is mandatory.** The endpoint refuses unsigned/forged events (`400`)
  and is disabled until `STRIPE_WEBHOOK_SECRET` is set (`503`). Never disable this.
- **Raw body matters.** We verify against the exact bytes Stripe sent
  (`await request.body()`); don't put a body-rewriting middleware in front.
- **Idempotent by design.** Stripe retries deliveries; re-applying "set tier=pro"
  or "set tier=free" is safe, so duplicate events cause no harm.
- **Secrets live in env**, never in git (`.env` is gitignored).

---

## Final go-live checklist

- [ ] Origin deployed; `/health` green; data populated; `REQUIRE_RAPIDAPI=false`.
- [ ] **Live** product + recurring price + Payment Link created.
- [ ] **Live** webhook on `/webhooks/stripe` with the 3 events; `STRIPE_WEBHOOK_SECRET` set on Render.
- [ ] Signup page mints a key and redirects with `client_reference_id`.
- [ ] One real purchase upgrades the key to `pro`; cancel downgrades it.
- [ ] Customer Portal enabled; refund path understood.
- [ ] A distribution plan in motion (Phase 7) — Stripe won't bring traffic.
