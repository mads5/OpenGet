"""
OSSPool MVP Setup Script
========================
Applies the Supabase migration and seeds realistic project data.

Usage:
  python setup_mvp.py

Requirements:
  - Supabase project with the database password
  - pip install psycopg2-binary
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from uuid import uuid4


SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://raeozfqmzqroqcdyndat.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY",
    "sb_publishable_byRVA-eKVyDt9xUSsJkxsg_zFXz1QHE"
)

MIGRATION_FILE = os.path.join(
    os.path.dirname(__file__),
    "supabase", "migrations", "20260327000000_initial_schema.sql"
)


SEED_PROJECTS = [
    {"name": "React", "github_url": "https://github.com/facebook/react", "owner": "facebook", "language": "JavaScript",
     "description": "The library for web and native user interfaces",
     "stars": 231000, "forks": 47200, "watchers": 6700, "open_issues": 920, "commit_frequency": 18.4,
     "dependents_count": 92000, "download_count": 24000000, "issue_close_rate": 0.87, "stars_growth_rate": 320},
    {"name": "Next.js", "github_url": "https://github.com/vercel/next.js", "owner": "vercel", "language": "JavaScript",
     "description": "The React Framework for the Web",
     "stars": 128000, "forks": 27400, "watchers": 1400, "open_issues": 3200, "commit_frequency": 32.1,
     "dependents_count": 45000, "download_count": 8500000, "issue_close_rate": 0.72, "stars_growth_rate": 210},
    {"name": "Vue.js", "github_url": "https://github.com/vuejs/core", "owner": "vuejs", "language": "TypeScript",
     "description": "The Progressive JavaScript Framework",
     "stars": 48000, "forks": 8300, "watchers": 580, "open_issues": 620, "commit_frequency": 12.8,
     "dependents_count": 38000, "download_count": 5200000, "issue_close_rate": 0.91, "stars_growth_rate": 95},
    {"name": "Svelte", "github_url": "https://github.com/sveltejs/svelte", "owner": "sveltejs", "language": "JavaScript",
     "description": "Cybernetically enhanced web apps",
     "stars": 81000, "forks": 4300, "watchers": 850, "open_issues": 310, "commit_frequency": 14.2,
     "dependents_count": 12000, "download_count": 2800000, "issue_close_rate": 0.89, "stars_growth_rate": 140},
    {"name": "Tailwind CSS", "github_url": "https://github.com/tailwindlabs/tailwindcss", "owner": "tailwindlabs", "language": "TypeScript",
     "description": "A utility-first CSS framework",
     "stars": 85000, "forks": 4300, "watchers": 580, "open_issues": 95, "commit_frequency": 8.5,
     "dependents_count": 52000, "download_count": 12000000, "issue_close_rate": 0.95, "stars_growth_rate": 180},
    {"name": "PyTorch", "github_url": "https://github.com/pytorch/pytorch", "owner": "pytorch", "language": "Python",
     "description": "Tensors and dynamic neural networks with strong GPU acceleration",
     "stars": 86000, "forks": 23000, "watchers": 1600, "open_issues": 14000, "commit_frequency": 95.2,
     "dependents_count": 28000, "download_count": 9500000, "issue_close_rate": 0.68, "stars_growth_rate": 250},
    {"name": "TensorFlow", "github_url": "https://github.com/tensorflow/tensorflow", "owner": "tensorflow", "language": "C++",
     "description": "An Open Source Machine Learning Framework",
     "stars": 188000, "forks": 74200, "watchers": 7900, "open_issues": 2400, "commit_frequency": 42.8,
     "dependents_count": 35000, "download_count": 7200000, "issue_close_rate": 0.74, "stars_growth_rate": 110},
    {"name": "FastAPI", "github_url": "https://github.com/fastapi/fastapi", "owner": "fastapi", "language": "Python",
     "description": "High performance, easy to learn, fast to code, ready for production",
     "stars": 82000, "forks": 7100, "watchers": 540, "open_issues": 480, "commit_frequency": 6.3,
     "dependents_count": 18000, "download_count": 4800000, "issue_close_rate": 0.82, "stars_growth_rate": 190},
    {"name": "Django", "github_url": "https://github.com/django/django", "owner": "django", "language": "Python",
     "description": "The Web framework for perfectionists with deadlines",
     "stars": 82000, "forks": 32000, "watchers": 2300, "open_issues": 310, "commit_frequency": 22.4,
     "dependents_count": 62000, "download_count": 6800000, "issue_close_rate": 0.93, "stars_growth_rate": 85},
    {"name": "Express", "github_url": "https://github.com/expressjs/express", "owner": "expressjs", "language": "JavaScript",
     "description": "Fast, unopinionated, minimalist web framework for Node.js",
     "stars": 66000, "forks": 17000, "watchers": 2100, "open_issues": 210, "commit_frequency": 3.1,
     "dependents_count": 85000, "download_count": 32000000, "issue_close_rate": 0.78, "stars_growth_rate": 45},
    {"name": "Rust", "github_url": "https://github.com/rust-lang/rust", "owner": "rust-lang", "language": "Rust",
     "description": "Empowering everyone to build reliable and efficient software",
     "stars": 101000, "forks": 13000, "watchers": 1500, "open_issues": 9800, "commit_frequency": 120.5,
     "dependents_count": 75000, "download_count": 3200000, "issue_close_rate": 0.81, "stars_growth_rate": 160},
    {"name": "Node.js", "github_url": "https://github.com/nodejs/node", "owner": "nodejs", "language": "JavaScript",
     "description": "Node.js JavaScript runtime",
     "stars": 110000, "forks": 32000, "watchers": 3000, "open_issues": 1600, "commit_frequency": 38.7,
     "dependents_count": 95000, "download_count": 45000000, "issue_close_rate": 0.76, "stars_growth_rate": 75},
    {"name": "Vite", "github_url": "https://github.com/vitejs/vite", "owner": "vitejs", "language": "TypeScript",
     "description": "Next generation frontend tooling",
     "stars": 70000, "forks": 6400, "watchers": 440, "open_issues": 520, "commit_frequency": 10.8,
     "dependents_count": 42000, "download_count": 15000000, "issue_close_rate": 0.85, "stars_growth_rate": 200},
    {"name": "PostgreSQL", "github_url": "https://github.com/postgres/postgres", "owner": "postgres", "language": "C",
     "description": "The world's most advanced open source relational database",
     "stars": 17000, "forks": 4800, "watchers": 660, "open_issues": 0, "commit_frequency": 55.3,
     "dependents_count": 120000, "download_count": 8000000, "issue_close_rate": 0.96, "stars_growth_rate": 40},
    {"name": "Kubernetes", "github_url": "https://github.com/kubernetes/kubernetes", "owner": "kubernetes", "language": "Go",
     "description": "Production-Grade Container Orchestration",
     "stars": 113000, "forks": 40000, "watchers": 3200, "open_issues": 2100, "commit_frequency": 68.2,
     "dependents_count": 55000, "download_count": 3500000, "issue_close_rate": 0.88, "stars_growth_rate": 95},
    {"name": "Prisma", "github_url": "https://github.com/prisma/prisma", "owner": "prisma", "language": "TypeScript",
     "description": "Next-generation ORM for Node.js & TypeScript",
     "stars": 41000, "forks": 1600, "watchers": 260, "open_issues": 3400, "commit_frequency": 15.6,
     "dependents_count": 22000, "download_count": 6200000, "issue_close_rate": 0.71, "stars_growth_rate": 110},
    {"name": "TypeScript", "github_url": "https://github.com/microsoft/TypeScript", "owner": "microsoft", "language": "TypeScript",
     "description": "TypeScript is a superset of JavaScript that compiles to clean JavaScript output",
     "stars": 103000, "forks": 12500, "watchers": 2100, "open_issues": 5800, "commit_frequency": 28.9,
     "dependents_count": 110000, "download_count": 55000000, "issue_close_rate": 0.79, "stars_growth_rate": 120},
    {"name": "Lodash", "github_url": "https://github.com/lodash/lodash", "owner": "lodash", "language": "JavaScript",
     "description": "A modern JavaScript utility library delivering modularity, performance & extras",
     "stars": 60000, "forks": 7100, "watchers": 940, "open_issues": 75, "commit_frequency": 0.8,
     "dependents_count": 180000, "download_count": 58000000, "issue_close_rate": 0.45, "stars_growth_rate": 10},
    {"name": "ESLint", "github_url": "https://github.com/eslint/eslint", "owner": "eslint", "language": "JavaScript",
     "description": "Find and fix problems in your JavaScript code",
     "stars": 25500, "forks": 4600, "watchers": 350, "open_issues": 110, "commit_frequency": 8.4,
     "dependents_count": 95000, "download_count": 42000000, "issue_close_rate": 0.92, "stars_growth_rate": 35},
    {"name": "Transformers", "github_url": "https://github.com/huggingface/transformers", "owner": "huggingface", "language": "Python",
     "description": "State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX",
     "stars": 140000, "forks": 28000, "watchers": 1200, "open_issues": 1400, "commit_frequency": 52.1,
     "dependents_count": 15000, "download_count": 12000000, "issue_close_rate": 0.83, "stars_growth_rate": 380},
]


WEIGHTS = {
    "dependents": 0.30,
    "downloads": 0.25,
    "commit_recency": 0.20,
    "issue_close": 0.15,
    "stars_growth": 0.10,
}


def compute_score(project, max_vals):
    dep = (project["dependents_count"] / max(max_vals["dependents_count"], 1)) * WEIGHTS["dependents"] * 100
    dl = (project["download_count"] / max(max_vals["download_count"], 1)) * WEIGHTS["downloads"] * 100
    commit = (project["commit_frequency"] / max(max_vals["commit_frequency"], 1)) * WEIGHTS["commit_recency"] * 100
    close = (project["issue_close_rate"] / max(max_vals["issue_close_rate"], 1)) * WEIGHTS["issue_close"] * 100
    growth = (project["stars_growth_rate"] / max(max_vals["stars_growth_rate"], 1)) * WEIGHTS["stars_growth"] * 100
    return {
        "total": round(dep + dl + commit + close + growth, 2),
        "breakdown": {
            "dependents_score": round(dep, 1),
            "download_velocity_score": round(dl, 1),
            "commit_recency_score": round(commit, 1),
            "issue_close_rate_score": round(close, 1),
            "stars_growth_score": round(growth, 1),
            "time_decay_factor": 1.0,
        },
    }


def supabase_request(method, table, data=None, query=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if query:
        url += f"?{query}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode()) if resp.read() else None
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"  API Error {e.code}: {body_text[:200]}")
        return None


def check_tables_exist():
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/projects?select=id&limit=1",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Accept": "application/json",
            }
        )
        resp = urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        body = e.read().decode()
        if "PGRST" in body:
            return False
        return True


def seed_data():
    print("\n--- Seeding Projects ---")
    project_ids = {}
    for p in SEED_PROJECTS:
        row = {
            "github_url": p["github_url"],
            "name": p["name"],
            "description": p["description"],
            "language": p["language"],
            "owner_github_id": p["owner"],
            "is_active": True,
            "stars": p["stars"],
            "forks": p["forks"],
            "watchers": p["watchers"],
            "open_issues": p["open_issues"],
            "commit_frequency": p["commit_frequency"],
            "dependents_count": p["dependents_count"],
            "download_count": p["download_count"],
            "issue_close_rate": p["issue_close_rate"],
            "stars_growth_rate": p["stars_growth_rate"],
            "last_commit_at": datetime.now(timezone.utc).isoformat(),
        }

        url = f"{SUPABASE_URL}/rest/v1/projects"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates",
        }
        body = json.dumps(row).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req)
            result = json.loads(resp.read().decode())
            if result and len(result) > 0:
                project_ids[p["name"]] = result[0]["id"]
                print(f"  + {p['name']} ({result[0]['id'][:8]}...)")
            else:
                print(f"  ? {p['name']} - no ID returned")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if "duplicate" in error_body.lower() or "23505" in error_body:
                print(f"  = {p['name']} (already exists)")
                try:
                    fetch_req = urllib.request.Request(
                        f"{SUPABASE_URL}/rest/v1/projects?github_url=eq.{urllib.parse.quote(p['github_url'])}&select=id",
                        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Accept": "application/json"},
                    )
                    fetch_resp = urllib.request.urlopen(fetch_req)
                    existing = json.loads(fetch_resp.read().decode())
                    if existing:
                        project_ids[p["name"]] = existing[0]["id"]
                except Exception:
                    pass
            else:
                print(f"  ! {p['name']} failed: {error_body[:150]}")

    if not project_ids:
        print("\nNo projects were inserted. Check your Supabase key permissions.")
        print("You may need the service_role key (not the anon/publishable key).")
        return

    print(f"\n--- Computing Rankings ({len(project_ids)} projects) ---")
    max_vals = {
        "dependents_count": max(p["dependents_count"] for p in SEED_PROJECTS),
        "download_count": max(p["download_count"] for p in SEED_PROJECTS),
        "commit_frequency": max(p["commit_frequency"] for p in SEED_PROJECTS),
        "issue_close_rate": max(p["issue_close_rate"] for p in SEED_PROJECTS),
        "stars_growth_rate": max(p["stars_growth_rate"] for p in SEED_PROJECTS),
    }

    scored = []
    for p in SEED_PROJECTS:
        if p["name"] not in project_ids:
            continue
        score = compute_score(p, max_vals)
        scored.append({**p, **score, "project_id": project_ids[p["name"]]})

    scored.sort(key=lambda x: x["total"], reverse=True)

    for period in ["daily", "weekly", "monthly", "yearly", "all_time"]:
        print(f"\n  Period: {period}")
        for rank, entry in enumerate(scored, 1):
            row = {
                "project_id": entry["project_id"],
                "project_name": entry["name"],
                "github_url": entry["github_url"],
                "rank": rank,
                "total_score": entry["total"],
                "breakdown": json.dumps(entry["breakdown"]),
                "period": period,
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }
            url = f"{SUPABASE_URL}/rest/v1/rankings"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }
            req = urllib.request.Request(url, data=json.dumps(row).encode(), headers=headers, method="POST")
            try:
                urllib.request.urlopen(req)
                if rank <= 3:
                    print(f"    #{rank} {entry['name']} (score: {entry['total']})")
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                print(f"    ! #{rank} {entry['name']} failed: {error_body[:100]}")

    print("\n--- Creating Funding Pool ---")
    pool = {
        "name": "Q1 2026 Funding Round",
        "description": "Quarterly quadratic funding pool for critical open-source infrastructure",
        "target_amount_cents": 5000000,
        "current_amount_cents": 3250000,
        "matched_pool_cents": 1875000,
        "status": "active",
        "start_date": "2026-01-01T00:00:00+00:00",
        "end_date": "2026-03-31T23:59:59+00:00",
        "match_ratio": 1.5,
        "donor_count": 1842,
        "project_count": len(project_ids),
    }
    url = f"{SUPABASE_URL}/rest/v1/money_pools"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    req = urllib.request.Request(url, data=json.dumps(pool).encode(), headers=headers, method="POST")
    try:
        urllib.request.urlopen(req)
        print("  + Q1 2026 Funding Round created")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  ! Pool creation failed: {error_body[:150]}")

    print("\n=== Setup Complete ===")
    print(f"  {len(project_ids)} projects seeded")
    print(f"  {len(scored) * 5} ranking entries created (5 periods)")
    print(f"  1 funding pool created")


def main():
    print("=" * 60)
    print("  OSSPool MVP Setup")
    print("=" * 60)
    print(f"\nSupabase URL: {SUPABASE_URL}")

    tables_exist = check_tables_exist()

    if not tables_exist:
        print("\n" + "!" * 60)
        print("  DATABASE TABLES NOT FOUND")
        print("!" * 60)
        print(f"""
You need to run the SQL migration first:

  1. Open the Supabase SQL Editor:
     https://supabase.com/dashboard/project/raeozfqmzqroqcdyndat/sql/new

  2. Copy the ENTIRE contents of:
     {MIGRATION_FILE}

  3. Paste it into the SQL Editor and click "Run"

  4. Re-run this script: python setup_mvp.py
""")
        print("TIP: You can also set SUPABASE_KEY to your service_role key")
        print("     for full insert permissions (find it in Project Settings > API)")
        sys.exit(1)

    print("\nTables found! Seeding data...")
    seed_data()

    print(f"""
=== Next Steps ===

1. ENABLE GITHUB OAUTH:
   - Go to: https://github.com/settings/developers
   - Click "New OAuth App"
   - Application name: OSSPool
   - Homepage URL: http://localhost:3000
   - Callback URL: {SUPABASE_URL}/auth/v1/callback
   - Copy the Client ID and Client Secret

   - Go to: https://supabase.com/dashboard/project/raeozfqmzqroqcdyndat/auth/providers
   - Find "GitHub" and enable it
   - Paste the Client ID and Client Secret
   - Save

2. VISIT YOUR APP:
   http://localhost:3000
""")


if __name__ == "__main__":
    import urllib.parse
    main()
