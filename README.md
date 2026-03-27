# OSSPool

Open-source project funding platform with quadratic funding distribution. Ranks projects by real-world impact metrics and distributes pooled donations using quadratic funding — where many small donations have outsized matched impact.

## Architecture

```
osspool-backend/     FastAPI + Celery + Redis
osspool-frontend/    Next.js 14 + Tailwind + shadcn/ui
supabase/            Database migrations & RLS policies
docker-compose.yml   Full-stack orchestration
```

## Backend Stack

- **FastAPI** — async REST API with Pydantic validation
- **Supabase** — PostgreSQL database with Row-Level Security
- **Celery + Redis** — task queue for crawling & ranking computation
- **httpx** — async GitHub API crawler with rate-limit handling
- **Stripe Connect** — payout processing to maintainers

### API Endpoints

| Route | Description |
|---|---|
| `GET /api/v1/rankings/leaderboard` | Leaderboard with period toggle |
| `GET /api/v1/projects` | List/search projects |
| `POST /api/v1/projects` | Register a project |
| `GET /api/v1/pools` | List funding pools |
| `POST /api/v1/pools/{id}/donate` | Donate to a pool |
| `POST /api/v1/payouts/connect/onboard` | Stripe Connect onboarding |
| `GET /api/v1/payouts/earnings/{user_id}` | Maintainer earnings |

### Ranking Algorithm

Projects scored with weighted metrics:
- **Dependent packages** (30%) — how many projects depend on this
- **Download velocity** (25%) — package download momentum
- **Commit recency** (20%) — how recently maintained
- **Issue close rate** (15%) — responsiveness to issues
- **Stars growth rate** (10%) — community adoption velocity

Time-decay is applied per period (daily rankings weight recent activity much more heavily than all-time).

## Frontend Stack

- **Next.js 14** App Router
- **Tailwind CSS** + **shadcn/ui** components
- **Supabase Auth** with GitHub OAuth
- Leaderboard, project detail, pool progress, maintainer dashboard

## Quick Start

```bash
# 1. Clone and configure
cp osspool-backend/.env.example osspool-backend/.env
cp osspool-frontend/.env.example osspool-frontend/.env
# Fill in your Supabase, GitHub, Stripe, and Redis credentials

# 2. Run the Supabase migration
# Apply supabase/migrations/20260327000000_initial_schema.sql to your Supabase project

# 3. Start everything
docker-compose up --build

# Backend:  http://localhost:8000
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

## Development (without Docker)

```bash
# Backend
cd osspool-backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Celery worker
celery -A app.core.celery_app:celery worker --loglevel=info

# Frontend
cd osspool-frontend
npm install
npm run dev
```

## License

See [LICENSE](LICENSE).
