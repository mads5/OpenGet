# OpenGet

Reward open-source contributors from a community-funded pool. List your repo, donors fund a pool, contributors get paid based on their code quality.

## How It Works

1. **List Your Repo** — Sign in with GitHub, list your open-source repo. We discover all contributors automatically.
2. **Donate to the Pool** — Anyone can donate to a shared funding pool.
3. **Contributors Get Paid** — The pool is distributed using a two-tier model:
   - **Tier 1 (Repos):** Each repo gets a share based on `sqrt(stars) × log2(1 + contributors)` — so popular repos get more, but with diminishing returns so small repos still get meaningful funding.
   - **Tier 2 (Contributors):** Within each repo's share, contributors are paid based on code quality: commits, PRs merged, lines changed, code reviews, issues closed, and recency.

## Architecture

```
osspool-backend/     FastAPI + Celery + Redis
osspool-frontend/    Next.js 14 + Tailwind + shadcn/ui
supabase/            Database migrations (PostgreSQL)
```

## Quick Start

### 1. Database
Apply the migration in `supabase/migrations/` to your Supabase project via the SQL Editor.

### 2. Backend
```bash
cd osspool-backend
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn app.main:app --reload
```

### 3. Frontend
```bash
cd osspool-frontend
npm install
cp .env.example .env   # fill in your keys
npm run dev
```

### 4. Environment Variables

**Backend (.env):**
- `SUPABASE_URL` / `SUPABASE_KEY` — Supabase project URL and service role key
- `GITHUB_TOKEN` — GitHub Personal Access Token
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` — Stripe (optional for MVP)

**Frontend (.env):**
- `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` — Backend API URL (default: http://localhost:8000/api/v1)

## API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/repos` | GET | List repos sorted by stars |
| `/api/v1/repos/mine` | GET | Your GitHub repos (auth required) |
| `/api/v1/repos` | POST | List a repo |
| `/api/v1/contributors` | GET | Contributor leaderboard |
| `/api/v1/contributors/register` | POST | Register as contributor |
| `/api/v1/pool` | GET | Active funding pool |
| `/api/v1/pool/donate` | POST | Donate to pool |
| `/api/v1/payouts/earnings` | GET | Your earnings |
