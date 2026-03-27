import asyncio
import logging

from app.core.celery_app import celery
from app.core.supabase import get_supabase_admin
from app.crawler.github_crawler import GitHubCrawler

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def crawl_single_project(self, project_id: str):
    try:
        db = get_supabase_admin()
        project = db.table("projects").select("*").eq("id", project_id).single().execute()
        if not project.data:
            logger.error(f"Project {project_id} not found")
            return

        url = project.data["github_url"]
        parts = url.rstrip("/").split("/")
        if len(parts) < 2:
            logger.error(f"Invalid GitHub URL for project {project_id}: {url}")
            return
        owner, repo = parts[-2], parts[-1]

        crawler = GitHubCrawler()
        stats = _run_async(crawler.fetch_repo_stats(owner, repo))
        stars_history = _run_async(crawler.fetch_stars_history(owner, repo, days=30))

        stars_growth = len(stars_history)

        update_data = {
            "stars": stats.get("stars", 0),
            "forks": stats.get("forks", 0),
            "watchers": stats.get("watchers", 0),
            "open_issues": stats.get("open_issues", 0),
            "commit_frequency": stats.get("commit_frequency", 0),
            "dependents_count": stats.get("dependents_count", 0),
            "download_count": stats.get("download_count", 0),
            "issue_close_rate": stats.get("issue_close_rate", 0),
            "stars_growth_rate": stars_growth,
            "last_commit_at": stats.get("last_push_at"),
            "description": stats.get("description"),
            "language": stats.get("language"),
        }

        db.table("projects").update(update_data).eq("id", project_id).execute()
        logger.info(f"Crawled project {project_id}: {owner}/{repo}")
        return {"project_id": project_id, "stats": update_data}

    except Exception as exc:
        logger.exception(f"Failed to crawl project {project_id}")
        raise self.retry(exc=exc)


@celery.task
def crawl_all_projects():
    db = get_supabase_admin()
    result = db.table("projects").select("id").eq("is_active", True).execute()
    projects = result.data or []

    for project in projects:
        crawl_single_project.delay(project["id"])

    logger.info(f"Queued crawl for {len(projects)} projects")
    return {"queued": len(projects)}
