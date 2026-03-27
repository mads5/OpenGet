"""
OpenGet MVP Setup Script
========================
Seeds the database with demo data after you apply the SQL migration.

PREREQUISITES:
1. Apply supabase/migrations/20260327000000_initial_schema.sql via Supabase SQL Editor
2. Enable GitHub OAuth in Supabase Auth settings
3. Set SUPABASE_URL and SUPABASE_KEY environment variables (or edit below)
"""

import os
import json
import urllib.request
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "your-service-role-key")

SEED_REPOS = [
    {"github_url": "https://github.com/facebook/react", "owner": "facebook", "repo_name": "react", "full_name": "facebook/react", "description": "The library for web and native user interfaces", "language": "JavaScript", "stars": 225000, "forks": 46000},
    {"github_url": "https://github.com/vercel/next.js", "owner": "vercel", "repo_name": "next.js", "full_name": "vercel/next.js", "description": "The React Framework", "language": "JavaScript", "stars": 126000, "forks": 26800},
    {"github_url": "https://github.com/microsoft/vscode", "owner": "microsoft", "repo_name": "vscode", "full_name": "microsoft/vscode", "description": "Visual Studio Code", "language": "TypeScript", "stars": 165000, "forks": 29500},
    {"github_url": "https://github.com/torvalds/linux", "owner": "torvalds", "repo_name": "linux", "full_name": "torvalds/linux", "description": "Linux kernel source tree", "language": "C", "stars": 180000, "forks": 54000},
    {"github_url": "https://github.com/denoland/deno", "owner": "denoland", "repo_name": "deno", "full_name": "denoland/deno", "description": "A modern runtime for JavaScript and TypeScript", "language": "Rust", "stars": 97000, "forks": 5400},
    {"github_url": "https://github.com/tiangolo/fastapi", "owner": "tiangolo", "repo_name": "fastapi", "full_name": "tiangolo/fastapi", "description": "FastAPI framework, high performance", "language": "Python", "stars": 78000, "forks": 6600},
    {"github_url": "https://github.com/tailwindlabs/tailwindcss", "owner": "tailwindlabs", "repo_name": "tailwindcss", "full_name": "tailwindlabs/tailwindcss", "description": "A utility-first CSS framework", "language": "CSS", "stars": 83000, "forks": 4200},
    {"github_url": "https://github.com/golang/go", "owner": "golang", "repo_name": "go", "full_name": "golang/go", "description": "The Go programming language", "language": "Go", "stars": 124000, "forks": 17700},
]

SEED_CONTRIBUTORS = [
    {"github_username": "gaearon", "avatar_url": "https://avatars.githubusercontent.com/u/810438"},
    {"github_username": "timneutkens", "avatar_url": "https://avatars.githubusercontent.com/u/6324199"},
    {"github_username": "acdlite", "avatar_url": "https://avatars.githubusercontent.com/u/3624098"},
    {"github_username": "sebmarkbage", "avatar_url": "https://avatars.githubusercontent.com/u/63648"},
    {"github_username": "adamwathan", "avatar_url": "https://avatars.githubusercontent.com/u/4323180"},
    {"github_username": "bartlomieju", "avatar_url": "https://avatars.githubusercontent.com/u/12587960"},
]


def supabase_request(method, path, data=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  ERROR {e.code}: {e.read().decode()[:200]}")
        return None


def seed_data():
    print("\n--- Seeding Repos ---")
    # We need a dummy user to be the 'listed_by' user
    dummy_user = supabase_request("POST", "users", {
        "github_id": "seed-user",
        "github_username": "openget-seed",
        "display_name": "OpenGet Seed User",
    })
    if not dummy_user:
        print("  Could not create seed user. Tables may not exist yet.")
        return
    user_id = dummy_user[0]["id"] if isinstance(dummy_user, list) else dummy_user["id"]

    for repo in SEED_REPOS:
        repo["listed_by"] = user_id
        repo["contributor_count"] = 0
        result = supabase_request("POST", "repos", repo)
        status = "OK" if result else "FAILED"
        print(f"  {repo['full_name']}: {status}")

    print("\n--- Seeding Contributors ---")
    for c in SEED_CONTRIBUTORS:
        c["total_score"] = 0
        c["repo_count"] = 0
        result = supabase_request("POST", "contributors", c)
        status = "OK" if result else "FAILED"
        print(f"  {c['github_username']}: {status}")

    print("\n--- Seeding Pool ---")
    pool_data = {
        "name": "Q1 2026 Open Source Fund",
        "description": "Community donations to reward open source contributors",
        "total_amount_cents": 5000000,
        "donor_count": 342,
        "status": "active",
        "round_start": "2026-01-01T00:00:00Z",
        "round_end": "2026-03-31T23:59:59Z",
    }
    result = supabase_request("POST", "pool", pool_data)
    print(f"  Pool: {'OK' if result else 'FAILED'}")


def main():
    print("=" * 60)
    print("  OpenGet MVP Setup")
    print("=" * 60)
    print(f"\nSupabase URL: {SUPABASE_URL}")

    # Check if tables exist
    result = supabase_request("GET", "repos?select=id&limit=1")
    if result is None:
        print("""
ERROR: Could not access the 'repos' table.

You need to run the SQL migration first:
  1. Go to your Supabase Dashboard > SQL Editor
  2. Paste the contents of supabase/migrations/20260327000000_initial_schema.sql
  3. Run it
  4. Then re-run this script

ALSO:
1. ENABLE GITHUB OAUTH:
   - Go to: https://github.com/settings/developers
   - Click "New OAuth App"
   - Application name: OpenGet
   - Homepage URL: http://localhost:3000
   - Callback URL: {SUPABASE_URL}/auth/v1/callback
   - Copy the Client ID and Client Secret

2. In Supabase Dashboard > Authentication > Providers > GitHub:
   - Enable GitHub provider
   - Paste Client ID and Client Secret
""")
        return

    seed_data()
    print("\nDone! Start the frontend with: cd osspool-frontend && npm run dev")


if __name__ == "__main__":
    main()
