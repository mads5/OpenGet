# OpenGet — Fund Open-Source Contributors

**OpenGet** is a platform that rewards the people who build open source. Contributors list their repos, donors fund a shared pool, and the platform distributes money to contributors weekly — based on the quality and impact of their code.

If you believe the people behind open source deserve to get paid, this is how.

[Live App](http://localhost:3000) · [API Docs](http://localhost:8000/docs) · [GitHub](https://github.com/mads5/OpenGet)

## How it works (short)

```
  GitHub Repos                    Donors (worldwide)
       │                                │
       │  list repo                     │  donate (USD/EUR/INR/...)
       ▼                                ▼
┌─────────────────────────────────────────────┐
│                  OpenGet                    │
│                                             │
│   ┌───────────┐    ┌──────────────────┐     │
│   │  GitHub    │    │  Funding Pool    │     │
│   │  Crawler   │    │  (monthly round) │     │
│   └─────┬─────┘    └────────┬─────────┘     │
│         │                   │               │
│         ▼                   ▼               │
│   ┌─────────────────────────────────┐       │
│   │     Two-Tier Distribution       │       │
│   │                                 │       │
│   │  Tier 1: Pool → Repos          │       │
│   │    sqrt(stars) × log2(contribs) │       │
│   │                                 │       │
│   │  Tier 2: Repo Share → People   │       │
│   │    commits, PRs, reviews, LOC   │       │
│   └───────────────┬─────────────────┘       │
│                   │                         │
│                   ▼                         │
│           Weekly Payouts                    │
│     (Stripe Connect → bank account)         │
└─────────────────────────────────────────────┘
```

## Highlights

- **List your repo** — sign in with GitHub, pick a repo. OpenGet discovers all contributors automatically via the GitHub API.
- **Global funding pool** — donors contribute monthly to a shared pool. Supports 9+ currencies (USD, EUR, GBP, INR, JPY, CAD, AUD, SGD, BRL).
- **UPI QR for India** — Indian donors can scan a Razorpay UPI QR code with Google Pay, PhonePe, Paytm, or any UPI app.
- **Card payments worldwide** — Stripe Checkout with automatic payment method detection (Visa, Mastercard, Amex, SEPA, iDEAL, and more).
- **Fair distribution** — Tier 1 gives repos a share based on `sqrt(stars) × log2(1 + contributor_count)` so small projects still get meaningful funding. Tier 2 pays contributors by quality: commits, PRs merged, lines changed, code reviews, issues closed, and recency.
- **Weekly payouts** — contributors connect Stripe and receive payouts in their local bank currency. Stripe handles conversion automatically.
- **Deduplication** — each repo is listed once. If multiple contributors list the same repo, all of them receive payouts.
- **GitHub OAuth** — sign in with your GitHub account. No extra passwords.

## Quick start

### 1. Database (Supabase)

Create a [Supabase](https://supabase.com) project and run the migrations via the SQL Editor:

```
supabase/migrations/20260327000000_initial_schema.sql
supabase/migrations/20260327000001_add_donation_currency.sql
```

### 2. Backend

Runtime: **Python 3.11+**

```bash
cd osspool-backend
pip install -r requirements.txt
cp .env.example .env   # fill in your keys (see Environment Variables below)
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Frontend

Runtime: **Node 18+**

```bash
cd osspool-frontend
npm install
cp .env.example .env   # fill in your keys (see Environment Variables below)
npm run dev
```

Frontend runs at `http://localhost:3000`.

## Environment variables

### Backend (`osspool-backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (for admin operations) |
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token (for crawling repos/contributors) |
| `STRIPE_SECRET_KEY` | No | Stripe secret key for card payments |
| `STRIPE_WEBHOOK_SECRET` | No | Stripe webhook signing secret |
| `STRIPE_CURRENCY` | No | Default currency for pool display (default: `usd`) |
| `RAZORPAY_KEY_ID` | No | Razorpay key ID for UPI QR payments (India) |
| `RAZORPAY_KEY_SECRET` | No | Razorpay key secret |
| `REDIS_URL` | No | Redis URL for caching (default: `redis://localhost:6379/0`) |
| `CELERY_BROKER_URL` | No | Celery broker (default: `redis://localhost:6379/1`) |
| `CELERY_RESULT_BACKEND` | No | Celery result backend (default: `redis://localhost:6379/2`) |

### Frontend (`osspool-frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon/public key |
| `NEXT_PUBLIC_API_URL` | No | Backend API URL (default: `http://localhost:8000/api/v1`) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | No | Stripe publishable key (for Checkout redirect) |
| `NEXT_PUBLIC_CURRENCY` | No | Display currency for pool totals (default: `usd`) |

## Architecture

```
osspool-backend/          Python — FastAPI + Supabase + Stripe + Razorpay
  app/
    core/                 Config, auth, Redis, Supabase client, Stripe init
    crawler/              GitHub API crawler (repos, contributors, stats)
    routers/              API route handlers (repos, contributors, pool, payouts)
    schemas/              Pydantic request/response models (repos, contributors, pools, payouts)
    services/             Business logic (pool distribution, payouts, scoring)
    tasks/                Background tasks (contributor fetching via Celery or inline)

osspool-frontend/         TypeScript — Next.js 14 + Tailwind + shadcn/ui
  src/
    app/                  Pages (home, donate, repos, contributors, dashboard)
    components/           Reusable UI components (layout, pool, repos, contributors, ui)
    lib/                  API client, Supabase client, utilities

supabase/
  migrations/             PostgreSQL schema (users, repos, contributors, pool, donations, payouts)

docker-compose.yml        Full-stack orchestration (optional)
```

## API reference

### Repos

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/api/v1/repos` | No | List all repos, sorted by stars (descending) |
| `GET` | `/api/v1/repos/mine` | Yes | List your GitHub repos (for the "list a repo" flow) |
| `GET` | `/api/v1/repos/{id}` | No | Get repo details |
| `GET` | `/api/v1/repos/{id}/contributors` | No | Get contributors for a specific repo |
| `POST` | `/api/v1/repos` | Yes | List a new repo (GitHub URL). Contributors are fetched in the background. |

### Contributors

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/api/v1/contributors` | No | Contributor leaderboard (sorted by score) |
| `GET` | `/api/v1/contributors/{id}` | No | Contributor detail with per-repo breakdown |
| `POST` | `/api/v1/contributors/register` | Yes | Register as a contributor (links your GitHub to receive payouts) |

### Pool & donations

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/api/v1/pool` | No | Get the active monthly funding pool |
| `GET` | `/api/v1/pool/{id}` | No | Pool detail with recent donations |
| `POST` | `/api/v1/pool/create-checkout-session` | Yes | Create a Stripe Checkout session (card payments) |
| `POST` | `/api/v1/pool/create-upi-qr` | Yes | Generate a Razorpay UPI QR code (INR only) |
| `GET` | `/api/v1/pool/upi-qr-status/{qr_id}` | No | Poll UPI QR payment status |
| `POST` | `/api/v1/pool/donate` | Yes | Record a donation directly (fallback if Stripe is not configured) |

### Payouts

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/api/v1/payouts/earnings` | Yes | Your earnings and payout history |
| `POST` | `/api/v1/payouts/stripe-connect` | Yes | Start Stripe Connect onboarding (to receive payouts) |

### Webhooks

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/v1/payouts/webhook` | Stripe webhook (`checkout.session.completed`) |
| `POST` | `/api/v1/pool/razorpay-webhook` | Razorpay webhook (`qr_code.credited`) |

## Distribution algorithm

OpenGet uses a **two-tier distribution model** to split the monthly pool fairly:

### Tier 1 — Pool to repos

Each listed repo receives a share proportional to:

```
weight = sqrt(stars) × log2(1 + contributor_count)
```

- `sqrt(stars)` gives diminishing returns for mega-popular repos, so smaller projects still get meaningful funding.
- `log2(1 + contributor_count)` rewards repos with active contributor communities.

### Tier 2 — Repo share to contributors

Within each repo's allocation, contributors are paid based on a **weighted quality score**:

| Metric | What it measures |
|--------|------------------|
| Commits | Number of commits authored |
| PRs merged | Pull requests merged into the repo |
| Lines added/changed | Volume of code contributed |
| Code reviews | Pull requests reviewed |
| Issues closed | Issues resolved |
| Recency | How recently the contributor was active (recent = higher weight) |

Each metric is normalized and combined into a single score per contributor per repo. Contributors active in multiple repos receive payouts from each.

## Payment methods

| Method | Currency | Provider | How it works |
|--------|----------|----------|--------------|
| Credit/Debit card | All supported | Stripe Checkout | Redirects to Stripe, auto-detects best methods per customer |
| UPI QR code | INR | Razorpay | Generates a scannable QR — works with Google Pay, PhonePe, Paytm, BHIM |
| SEPA / iDEAL / Bancontact | EUR | Stripe (auto) | Shown automatically for EUR payments |
| GrabPay / PayNow | SGD | Stripe (auto) | Shown automatically for SGD payments |
| Pix / Boleto | BRL | Stripe (auto) | Shown automatically for BRL payments |

Pool totals are normalized to USD using approximate exchange rates. Stripe settles in the platform's local currency.

## Database schema

```
users                   GitHub OAuth users (id, github_username, stripe_connect_account_id)
repos                   Listed GitHub repos (github_url, stars, forks, contributor_count)
contributors            Unique GitHub contributors (github_username, total_score, user_id)
repo_contributors       Per-repo contribution metrics (commits, prs_merged, lines_added, score)
pool                    Monthly funding pools (total_amount_cents, donor_count, status)
donations               Individual donations (amount_cents, currency, donor_id, pool_id)
payouts                 Distributed payouts to contributors (amount_cents, status, stripe_transfer_id)
```

Row-Level Security (RLS) is enabled on all tables. The service role key is used for admin operations; public reads are allowed for repos, contributors, and pool data.

## Docker (optional)

```bash
docker-compose up --build
```

This starts the backend (port 8000), frontend (port 3000), Redis, Celery worker, and Celery beat scheduler.

For local development, running the backend and frontend directly (without Docker) is simpler and recommended.

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), React, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python 3.11+, FastAPI, Pydantic, httpx |
| Database | Supabase (PostgreSQL) with Row-Level Security |
| Auth | Supabase Auth with GitHub OAuth |
| Payments | Stripe Checkout + Stripe Connect (worldwide), Razorpay QR (India UPI) |
| Background jobs | Celery + Redis (optional — runs inline if unavailable) |
| Caching | Redis (optional — degrades gracefully) |
| GitHub data | GitHub REST API with tenacity retry + rate-limit handling |

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Run the backend and frontend locally to verify
5. Open a pull request

## License

Apache 2.0 — see [LICENSE](LICENSE).
