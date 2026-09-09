# Security Policy

## Supported versions

This project is pre-1.0 in spirit; only the latest `main` is supported. Please
run the most recent commit before reporting an issue.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Instead, report privately via either:

1. **GitHub private vulnerability reporting** — the repository's **Security** tab
   → **Report a vulnerability** (preferred).
2. **Email** — bindra.ekams@gmail.com

Please include: a description of the issue, steps to reproduce, the affected
version/commit, and any suggested fix. We aim to acknowledge reports within a
few days and will keep you updated on remediation.

## Notes for self-hosters

This is a template; a deployment's security depends on how you configure it:

- **Change `ADMIN_TOKEN`** from the default — it protects the dashboard and
  admin endpoints.
- Keep secrets (`DATABASE_URL`, `STRIPE_WEBHOOK_SECRET`, `RAPIDAPI_PROXY_SECRET`)
  in environment variables, never in the repo. `.env` is git-ignored.
- The Stripe webhook is signature-verified; the RapidAPI path is gated by a
  shared proxy secret. Set these before exposing billing publicly.
