import asyncio
import logging

from app.core.supabase import get_supabase_admin
from app.crawler.github_crawler import GitHubCrawler
from app.services.contributor_service import ContributorService
from app.core.celery_app import celery

logger = logging.getLogger(__name__)


async def _fetch_repo_contributors(repo_id: str) -> dict:
    db = get_supabase_admin()
    repo_result = db.table("repos").select("*").eq("id", repo_id).single().execute()
    if not repo_result.data:
        return {"error": "Repo not found"}

    repo = repo_result.data
    owner = repo["owner"]
    repo_name = repo["repo_name"]

    crawler = GitHubCrawler()

    gh_contributors = await crawler.fetch_repo_contributors(owner, repo_name)
    if not gh_contributors:
        return {"repo_id": repo_id, "contributors_added": 0}

    count = 0
    for gh_c in gh_contributors:
        login = gh_c["login"]

        existing = db.table("contributors").select("id").eq("github_username", login).execute()
        if existing.data:
            contributor_id = existing.data[0]["id"]
        else:
            insert_result = db.table("contributors").insert({
                "github_username": login,
                "github_id": str(gh_c.get("id", "")),
                "avatar_url": gh_c.get("avatar_url"),
                "total_score": 0,
                "repo_count": 0,
            }).execute()
            if not insert_result.data:
                continue
            contributor_id = insert_result.data[0]["id"]

        rc_existing = (
            db.table("repo_contributors")
            .select("id")
            .eq("repo_id", repo_id)
            .eq("contributor_id", contributor_id)
            .execute()
        )

        try:
            stats = await crawler.fetch_contributor_stats(owner, repo_name, login)
        except Exception as e:
            logger.warning(f"Failed to fetch stats for {login} in {owner}/{repo_name}: {e}")
            stats = {"commits": gh_c.get("contributions", 0)}

        rc_data = {
            "repo_id": repo_id,
            "contributor_id": contributor_id,
            "commits": stats.get("commits", gh_c.get("contributions", 0)),
            "prs_merged": stats.get("prs_merged", 0),
            "lines_added": stats.get("lines_added", 0),
            "lines_removed": stats.get("lines_removed", 0),
            "reviews": stats.get("reviews", 0),
            "issues_closed": stats.get("issues_closed", 0),
            "last_contribution_at": stats.get("last_contribution_at"),
            "score": 0,
        }

        if rc_existing.data:
            db.table("repo_contributors").update(rc_data).eq("id", rc_existing.data[0]["id"]).execute()
        else:
            db.table("repo_contributors").insert(rc_data).execute()
            count += 1

    db.table("repos").update({
        "contributor_count": len(gh_contributors),
        "contributors_fetched_at": "now()",
    }).eq("id", repo_id).execute()

    service = ContributorService()
    await service.recompute_scores_for_repo(repo_id)
    await service.recompute_total_scores()

    return {"repo_id": repo_id, "contributors_added": count, "total": len(gh_contributors)}


async def _recompute_all() -> dict:
    db = get_supabase_admin()
    repos = db.table("repos").select("id").execute()
    service = ContributorService()

    for r in repos.data or []:
        await service.recompute_scores_for_repo(r["id"])

    await service.recompute_total_scores()
    return {"repos_processed": len(repos.data or [])}


async def run_fetch_repo_contributors_bg(repo_id: str) -> None:
    """Background task: fetch contributors via Celery or inline async."""
    if celery is not None:
        try:
            celery.send_task("fetch_repo_contributors", args=[repo_id])
            return
        except Exception as e:
            logger.warning(f"Celery dispatch failed, running inline: {e}")

    try:
        await _fetch_repo_contributors(repo_id)
    except Exception:
        logger.exception("Background contributor fetch failed for repo %s", repo_id)


if celery is not None:
    @celery.task(name="fetch_repo_contributors")
    def fetch_repo_contributors_task(repo_id: str) -> dict:
        return asyncio.get_event_loop().run_until_complete(
            _fetch_repo_contributors(repo_id)
        )

    @celery.task(name="recompute_all_scores")
    def recompute_all_scores_task() -> dict:
        return asyncio.get_event_loop().run_until_complete(_recompute_all())
