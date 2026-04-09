import asyncio
import logging
from datetime import datetime, timezone, date
from calendar import monthrange

from app.core.supabase import get_supabase_admin
from app.crawler.github_crawler import GitHubCrawler
from app.services.contributor_service import ContributorService
from app.services.pool_service import PoolService
from app.services.payout_service import PayoutService
from app.core.celery_app import celery

logger = logging.getLogger(__name__)


# =========================================================================
# Original: fetch contributors for a repo
# =========================================================================

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

        existing = (
            db.table("contributors")
            .select("id")
            .eq("github_username", login)
            .execute()
        )
        if existing.data:
            contributor_id = existing.data[0]["id"]
        else:
            insert_result = (
                db.table("contributors")
                .insert(
                    {
                        "github_username": login,
                        "github_id": str(gh_c.get("id", "")),
                        "avatar_url": gh_c.get("avatar_url"),
                        "total_score": 0,
                        "repo_count": 0,
                        "total_contributions": 0,
                    }
                )
                .execute()
            )
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
            logger.warning(
                "Failed to fetch stats for %s in %s/%s: %s",
                login, owner, repo_name, e,
            )
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
            db.table("repo_contributors").update(rc_data).eq(
                "id", rc_existing.data[0]["id"]
            ).execute()
        else:
            db.table("repo_contributors").insert(rc_data).execute()
            count += 1

    db.table("repos").update(
        {
            "contributor_count": len(gh_contributors),
            "contributors_fetched_at": "now()",
        }
    ).eq("id", repo_id).execute()

    service = ContributorService()
    await service.recompute_scores_for_repo(repo_id)
    await service.recompute_total_scores()

    return {
        "repo_id": repo_id,
        "contributors_added": count,
        "total": len(gh_contributors),
    }


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
            logger.warning("Celery dispatch failed, running inline: %s", e)

    try:
        await _fetch_repo_contributors(repo_id)
    except Exception:
        logger.exception("Background contributor fetch failed for repo %s", repo_id)


# =========================================================================
# Friday: calculate weekly scores
# =========================================================================

async def _calculate_weekly_scores() -> dict:
    """Refresh repo scores from GitHub and recompute all contributor scores."""
    db = get_supabase_admin()
    crawler = GitHubCrawler()
    service = ContributorService()

    repos = db.table("repos").select("id, owner, repo_name").execute()
    repos_list = repos.data or []
    month = datetime.now(timezone.utc).strftime("%Y-%m")

    repos_updated = 0
    for repo in repos_list:
        try:
            info = await crawler.fetch_repo_info(repo["owner"], repo["repo_name"])
            stars = info.get("stargazers_count", 0)
            forks = info.get("forks_count", 0)
            repo_score = stars + forks

            db.table("repos").update(
                {"stars": stars, "forks": forks, "repo_score": repo_score}
            ).eq("id", repo["id"]).execute()
            repos_updated += 1
        except Exception:
            logger.exception(
                "Failed to refresh repo %s/%s", repo["owner"], repo["repo_name"]
            )

        # Recompute per-repo contributor scores
        await service.recompute_scores_for_repo(repo["id"])

        # Fetch monthly PR stats for each contributor in this repo
        rc_result = (
            db.table("repo_contributors")
            .select("contributor_id")
            .eq("repo_id", repo["id"])
            .execute()
        )
        for rc in rc_result.data or []:
            cid = rc["contributor_id"]
            c_row = (
                db.table("contributors")
                .select("github_username")
                .eq("id", cid)
                .single()
                .execute()
            )
            username = (c_row.data or {}).get("github_username")
            if not username:
                continue

            try:
                monthly = await crawler.fetch_monthly_pr_stats(
                    repo["owner"], repo["repo_name"], username, month
                )
            except Exception:
                logger.warning(
                    "Monthly PR fetch failed for %s in %s/%s",
                    username, repo["owner"], repo["repo_name"],
                )
                continue

            # Upsert monthly_contributor_stats
            existing_mcs = (
                db.table("monthly_contributor_stats")
                .select("id")
                .eq("contributor_id", cid)
                .eq("repo_id", repo["id"])
                .eq("month", month)
                .execute()
            )
            mcs_data = {
                "contributor_id": cid,
                "repo_id": repo["id"],
                "month": month,
                "prs_raised": monthly.get("prs_raised", 0),
                "prs_merged": monthly.get("prs_merged", 0),
            }
            if existing_mcs.data:
                db.table("monthly_contributor_stats").update(mcs_data).eq(
                    "id", existing_mcs.data[0]["id"]
                ).execute()
            else:
                db.table("monthly_contributor_stats").insert(mcs_data).execute()

    # Update total_contributions for each contributor (sum of all commits)
    contributors = db.table("contributors").select("id").execute()
    for c in contributors.data or []:
        rc_all = (
            db.table("repo_contributors")
            .select("commits")
            .eq("contributor_id", c["id"])
            .execute()
        )
        total = sum(r.get("commits", 0) for r in (rc_all.data or []))
        db.table("contributors").update({"total_contributions": total}).eq(
            "id", c["id"]
        ).execute()

    # Recompute global 4-factor scores
    processed = await service.recompute_all_monthly_scores(month)

    # Ensure a collecting pool exists for next month
    pool_service = PoolService()
    await pool_service.ensure_collecting_pool()

    return {
        "repos_updated": repos_updated,
        "contributors_scored": processed,
        "month": month,
    }


# =========================================================================
# Saturday: distribute weekly pool
# =========================================================================

async def _distribute_weekly_pool() -> dict:
    pool_service = PoolService()
    try:
        distributions = await pool_service.distribute_weekly(is_month_end=False)
        return {
            "status": "distributed",
            "repo_distributions": len(distributions),
        }
    except ValueError as e:
        logger.warning("Weekly distribution skipped: %s", e)
        return {"status": "skipped", "reason": str(e)}


# =========================================================================
# Sunday: process weekly payouts (Stripe transfers)
# =========================================================================

async def _process_weekly_payouts() -> dict:
    db = get_supabase_admin()
    payout_service = PayoutService()

    pending = (
        db.table("payouts")
        .select("id, amount_cents")
        .eq("status", "pending")
        .execute()
    )
    payouts = pending.data or []

    processed = 0
    failed = 0
    skipped = 0

    for p in payouts:
        if p["amount_cents"] < 50:
            skipped += 1
            continue
        try:
            await payout_service.process_payout(p["id"])
            processed += 1
        except Exception:
            logger.exception("Failed to process payout %s", p["id"])
            failed += 1

    return {"processed": processed, "failed": failed, "skipped": skipped}


# =========================================================================
# Month-end: finalize pool
# =========================================================================

async def _finalize_monthly_pool() -> dict:
    """Run daily at 23:55; only acts on the last day of the month."""
    today = date.today()
    _, last_day = monthrange(today.year, today.month)

    if today.day != last_day:
        return {"status": "not_last_day", "day": today.day, "last_day": last_day}

    pool_service = PoolService()
    result = await pool_service.finalize_month()
    return result


# =========================================================================
# Celery task wrappers
# =========================================================================

def _run_async(coro):
    """Run an async coroutine in a sync context (Celery worker)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


if celery is not None:

    @celery.task(name="fetch_repo_contributors")
    def fetch_repo_contributors_task(repo_id: str) -> dict:
        return _run_async(_fetch_repo_contributors(repo_id))

    @celery.task(name="recompute_all_scores")
    def recompute_all_scores_task() -> dict:
        return _run_async(_recompute_all())

    @celery.task(name="calculate_weekly_scores")
    def calculate_weekly_scores_task() -> dict:
        return _run_async(_calculate_weekly_scores())

    @celery.task(name="distribute_weekly_pool")
    def distribute_weekly_pool_task() -> dict:
        return _run_async(_distribute_weekly_pool())

    @celery.task(name="process_weekly_payouts")
    def process_weekly_payouts_task() -> dict:
        return _run_async(_process_weekly_payouts())

    @celery.task(name="finalize_monthly_pool")
    def finalize_monthly_pool_task() -> dict:
        return _run_async(_finalize_monthly_pool())
