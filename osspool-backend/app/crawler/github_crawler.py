import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import get_settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

CACHE_TTL = 3600


class GitHubAPIError(Exception):
    pass


class GitHubRateLimited(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after:.0f}s")


class GitHubCrawler:
    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._semaphore = asyncio.Semaphore(10)

    def _cache_key(self, prefix: str, *parts: str) -> str:
        joined = "/".join(p.lower() for p in parts)
        return f"gh:{prefix}:{joined}"

    async def _get_cached(self, cache_key: str):
        try:
            redis = await get_redis()
            if redis is None:
                return None
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error for {cache_key}: {e}")
        return None

    async def _set_cached(self, cache_key: str, data, ttl: int = CACHE_TTL) -> None:
        try:
            redis = await get_redis()
            if redis is None:
                return
            await redis.set(cache_key, json.dumps(data, default=str), ex=ttl)
        except Exception as e:
            logger.warning(f"Cache write error for {cache_key}: {e}")

    async def _handle_response(self, response: httpx.Response) -> None:
        remaining = int(response.headers.get("x-ratelimit-remaining", "999"))
        if 0 < remaining <= self.settings.github_rate_limit_buffer:
            reset_ts = int(response.headers.get("x-ratelimit-reset", "0"))
            if reset_ts > 0:
                wait_seconds = max(
                    (datetime.fromtimestamp(reset_ts, tz=timezone.utc) - datetime.now(timezone.utc)).total_seconds(),
                    1,
                )
                logger.warning(f"Rate limit low ({remaining} left), sleeping {wait_seconds:.0f}s")
                await asyncio.sleep(wait_seconds)

        if response.status_code == 403:
            is_rate_limit = remaining == 0 or "rate limit" in response.text.lower()
            if is_rate_limit:
                reset_ts = int(response.headers.get("x-ratelimit-reset", "0"))
                retry_after = max(
                    (datetime.fromtimestamp(reset_ts, tz=timezone.utc) - datetime.now(timezone.utc)).total_seconds(),
                    60,
                ) if reset_ts > 0 else 60
                raise GitHubRateLimited(retry_after)
            raise GitHubAPIError(f"GitHub 403: {response.text[:200]}")

        if response.status_code == 401:
            raise GitHubAPIError("GitHub 401: Invalid or expired token")

        if response.status_code == 404:
            raise GitHubAPIError("GitHub 404: Resource not found")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError, GitHubRateLimited)),
    )
    async def _request(self, client: httpx.AsyncClient, url: str) -> dict | list:
        async with self._semaphore:
            response = await client.get(url, headers=self.headers)
            await self._handle_response(response)
            response.raise_for_status()
            return response.json()

    # -------------------------------------------------------------------------
    # Fetch user's repos (for the "list your repo" flow)
    # -------------------------------------------------------------------------
    async def fetch_user_repos(self, username: str) -> list[dict]:
        cache_key = self._cache_key("user_repos", username)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        repos = []
        async with httpx.AsyncClient(base_url=self.settings.github_api_base, timeout=30) as client:
            page = 1
            while True:
                data = await self._request(
                    client,
                    f"/users/{username}/repos?sort=stars&direction=desc&per_page=100&page={page}&type=owner",
                )
                if not data:
                    break
                for r in data:
                    repos.append({
                        "full_name": r["full_name"],
                        "html_url": r["html_url"],
                        "description": r.get("description"),
                        "language": r.get("language"),
                        "stargazers_count": r.get("stargazers_count", 0),
                        "forks_count": r.get("forks_count", 0),
                    })
                if len(data) < 100:
                    break
                page += 1

        repos.sort(key=lambda r: r["stargazers_count"], reverse=True)
        await self._set_cached(cache_key, repos, ttl=600)
        return repos

    # -------------------------------------------------------------------------
    # Fetch repo basic info
    # -------------------------------------------------------------------------
    async def fetch_repo_info(self, owner: str, repo: str) -> dict:
        cache_key = self._cache_key("repo_info", owner, repo)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        async with httpx.AsyncClient(base_url=self.settings.github_api_base, timeout=30) as client:
            data = await self._request(client, f"/repos/{owner}/{repo}")
            info = {
                "full_name": data["full_name"],
                "html_url": data["html_url"],
                "description": data.get("description"),
                "language": data.get("language"),
                "stargazers_count": data.get("stargazers_count", 0),
                "forks_count": data.get("forks_count", 0),
                "owner": data["owner"]["login"],
                "name": data["name"],
            }
            await self._set_cached(cache_key, info)
            return info

    # -------------------------------------------------------------------------
    # Fetch repo contributors (GitHub contributors endpoint with commit counts)
    # -------------------------------------------------------------------------
    async def fetch_repo_contributors(self, owner: str, repo: str) -> list[dict]:
        cache_key = self._cache_key("contributors", owner, repo)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        contributors = []
        async with httpx.AsyncClient(base_url=self.settings.github_api_base, timeout=30) as client:
            page = 1
            while True:
                try:
                    data = await self._request(
                        client,
                        f"/repos/{owner}/{repo}/contributors?per_page=100&page={page}",
                    )
                except GitHubAPIError:
                    break

                if not data or not isinstance(data, list):
                    break

                for c in data:
                    if c.get("type") == "Bot":
                        continue
                    contributors.append({
                        "login": c["login"],
                        "id": c.get("id"),
                        "avatar_url": c.get("avatar_url"),
                        "contributions": c.get("contributions", 0),
                    })

                if len(data) < 100:
                    break
                page += 1

        await self._set_cached(cache_key, contributors, ttl=3600)
        return contributors

    # -------------------------------------------------------------------------
    # Fetch detailed contributor stats for a specific contributor in a repo
    # -------------------------------------------------------------------------
    async def fetch_contributor_stats(
        self, owner: str, repo: str, username: str
    ) -> dict:
        cache_key = self._cache_key("contributor_stats", owner, repo, username)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        stats = {
            "commits": 0,
            "prs_merged": 0,
            "lines_added": 0,
            "lines_removed": 0,
            "reviews": 0,
            "issues_closed": 0,
            "last_contribution_at": None,
        }

        async with httpx.AsyncClient(base_url=self.settings.github_api_base, timeout=30) as client:
            prs_result, issues_result, commits_result = await asyncio.gather(
                self._fetch_prs_merged(client, owner, repo, username),
                self._fetch_issues_closed(client, owner, repo, username),
                self._fetch_commit_details(client, owner, repo, username),
                return_exceptions=True,
            )

            if not isinstance(commits_result, Exception):
                stats["commits"] = commits_result.get("count", 0)
                stats["lines_added"] = commits_result.get("lines_added", 0)
                stats["lines_removed"] = commits_result.get("lines_removed", 0)
                stats["last_contribution_at"] = commits_result.get("last_date")
            else:
                logger.warning(f"Commits fetch failed for {username} in {owner}/{repo}: {commits_result}")

            if not isinstance(prs_result, Exception):
                stats["prs_merged"] = prs_result.get("count", 0)
                stats["reviews"] = prs_result.get("reviews", 0)
            else:
                logger.warning(f"PRs fetch failed for {username} in {owner}/{repo}: {prs_result}")

            if not isinstance(issues_result, Exception):
                stats["issues_closed"] = issues_result.get("count", 0)
            else:
                logger.warning(f"Issues fetch failed for {username} in {owner}/{repo}: {issues_result}")

        await self._set_cached(cache_key, stats, ttl=3600)
        return stats

    async def _fetch_commit_details(
        self, client: httpx.AsyncClient, owner: str, repo: str, username: str
    ) -> dict:
        try:
            search_data = await self._request(
                client,
                f"/search/commits?q=repo:{owner}/{repo}+author:{username}&sort=author-date&order=desc&per_page=5",
            )
            count = search_data.get("total_count", 0)
            lines_added = 0
            lines_removed = 0
            last_date = None

            items = search_data.get("items", [])
            if items:
                last_date = items[0].get("commit", {}).get("author", {}).get("date")
                for item in items[:3]:
                    sha = item.get("sha")
                    if sha:
                        try:
                            commit_data = await self._request(
                                client, f"/repos/{owner}/{repo}/commits/{sha}"
                            )
                            commit_stats = commit_data.get("stats", {})
                            lines_added += commit_stats.get("additions", 0)
                            lines_removed += commit_stats.get("deletions", 0)
                        except Exception:
                            pass

                if lines_added > 0 and count > 3:
                    avg_add = lines_added / min(len(items), 3)
                    avg_del = lines_removed / min(len(items), 3)
                    lines_added = int(avg_add * count)
                    lines_removed = int(avg_del * count)

            return {"count": count, "lines_added": lines_added, "lines_removed": lines_removed, "last_date": last_date}
        except Exception:
            logger.exception(f"Failed to fetch commit details for {username} in {owner}/{repo}")
            return {"count": 0, "lines_added": 0, "lines_removed": 0, "last_date": None}

    async def _fetch_prs_merged(
        self, client: httpx.AsyncClient, owner: str, repo: str, username: str
    ) -> dict:
        try:
            data = await self._request(
                client,
                f"/search/issues?q=repo:{owner}/{repo}+author:{username}+type:pr+is:merged&per_page=1",
            )
            pr_count = data.get("total_count", 0)

            review_data = await self._request(
                client,
                f"/search/issues?q=repo:{owner}/{repo}+reviewed-by:{username}+type:pr&per_page=1",
            )
            review_count = review_data.get("total_count", 0)

            return {"count": pr_count, "reviews": review_count}
        except Exception:
            logger.exception(f"Failed to fetch PR stats for {username} in {owner}/{repo}")
            return {"count": 0, "reviews": 0}

    async def _fetch_issues_closed(
        self, client: httpx.AsyncClient, owner: str, repo: str, username: str
    ) -> dict:
        try:
            data = await self._request(
                client,
                f"/search/issues?q=repo:{owner}/{repo}+author:{username}+type:issue+is:closed&per_page=1",
            )
            return {"count": data.get("total_count", 0)}
        except Exception:
            logger.exception(f"Failed to fetch issues for {username} in {owner}/{repo}")
            return {"count": 0}
