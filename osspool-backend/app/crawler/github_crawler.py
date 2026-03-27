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
    """Non-retryable GitHub API error (auth, not found, etc.)."""
    pass


class GitHubRateLimited(Exception):
    """Retryable rate-limit error."""
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

    def _cache_key(self, prefix: str, owner: str, repo: str, suffix: str = "") -> str:
        key = f"gh:{prefix}:{owner.lower()}/{repo.lower()}"
        if suffix:
            key += f":{suffix}"
        return key

    async def _get_cached(self, cache_key: str):
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Cache read error for {cache_key}: {e}")
        return None

    async def _set_cached(self, cache_key: str, data, ttl: int = CACHE_TTL) -> None:
        try:
            redis = await get_redis()
            await redis.set(cache_key, json.dumps(data, default=str), ex=ttl)
        except Exception as e:
            logger.warning(f"Cache write error for {cache_key}: {e}")

    async def _handle_response(self, response: httpx.Response) -> None:
        remaining = int(response.headers.get("x-ratelimit-remaining", "999"))
        if remaining <= self.settings.github_rate_limit_buffer and remaining > 0:
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
            raise GitHubAPIError(f"GitHub 404: Resource not found")

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError, GitHubRateLimited)),
    )
    async def _request_with_headers(
        self, client: httpx.AsyncClient, url: str, headers: dict
    ) -> dict | list:
        async with self._semaphore:
            response = await client.get(url, headers=headers)
            await self._handle_response(response)
            response.raise_for_status()
            return response.json()

    async def fetch_repo_stats(self, owner: str, repo: str) -> dict:
        cache_key = self._cache_key("repo", owner, repo)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        async with httpx.AsyncClient(base_url=self.settings.github_api_base, timeout=30) as client:
            repo_data, commits, issues = await asyncio.gather(
                self._request(client, f"/repos/{owner}/{repo}"),
                self._fetch_commit_frequency(client, owner, repo),
                self._fetch_issue_close_rate(client, owner, repo),
                return_exceptions=True,
            )

            if isinstance(repo_data, Exception):
                raise repo_data
            if isinstance(commits, Exception):
                logger.warning(f"Commit frequency fetch failed for {owner}/{repo}: {commits}")
                commits = 0.0
            if isinstance(issues, Exception):
                logger.warning(f"Issue close rate fetch failed for {owner}/{repo}: {issues}")
                issues = 0.0

            dependents = await self._fetch_dependents_count(client, owner, repo)

            stats = {
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("subscribers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "language": repo_data.get("language"),
                "description": repo_data.get("description"),
                "last_push_at": repo_data.get("pushed_at"),
                "created_at": repo_data.get("created_at"),
                "commit_frequency": commits,
                "issue_close_rate": issues,
                "dependents_count": dependents,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

            await self._set_cached(cache_key, stats)
            return stats

    async def _fetch_commit_frequency(
        self, client: httpx.AsyncClient, owner: str, repo: str
    ) -> float:
        cache_key = self._cache_key("commits", owner, repo)
        cached = await self._get_cached(cache_key)
        if cached and isinstance(cached, dict):
            return cached.get("frequency", 0.0)

        try:
            async with self._semaphore:
                response = await client.get(
                    f"/repos/{owner}/{repo}/stats/participation",
                    headers=self.headers,
                )

            if response.status_code == 202:
                logger.info(f"Participation stats computing for {owner}/{repo}, returning 0")
                return 0.0

            await self._handle_response(response)
            response.raise_for_status()
            data = response.json()

            weekly = data.get("all", [])
            if not weekly:
                return 0.0
            frequency = sum(weekly) / max(len(weekly), 1)
            await self._set_cached(cache_key, {"frequency": frequency})
            return frequency
        except GitHubAPIError:
            raise
        except Exception:
            logger.exception(f"Failed to fetch commit frequency for {owner}/{repo}")
            return 0.0

    async def _fetch_issue_close_rate(
        self, client: httpx.AsyncClient, owner: str, repo: str
    ) -> float:
        cache_key = self._cache_key("issues", owner, repo)
        cached = await self._get_cached(cache_key)
        if cached and isinstance(cached, dict):
            return cached.get("close_rate", 0.0)

        since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        try:
            closed = await self._request(
                client,
                f"/search/issues?q=repo:{owner}/{repo}+type:issue+closed:>={since}&per_page=1",
            )
            total = await self._request(
                client,
                f"/search/issues?q=repo:{owner}/{repo}+type:issue+created:>={since}&per_page=1",
            )

            closed_count = closed.get("total_count", 0)
            total_count = total.get("total_count", 0)
            rate = closed_count / max(total_count, 1)
            await self._set_cached(cache_key, {"close_rate": rate})
            return rate
        except GitHubAPIError:
            raise
        except Exception:
            logger.exception(f"Failed to fetch issue close rate for {owner}/{repo}")
            return 0.0

    async def _fetch_dependents_count(
        self, client: httpx.AsyncClient, owner: str, repo: str
    ) -> int:
        """
        Approximate dependents by searching for 'owner/repo' in package manifest files.
        Uses the full owner/repo to reduce false positives from common repo names.
        For production accuracy, integrate with a package registry API (npm, PyPI, etc.).
        """
        cache_key = self._cache_key("dependents", owner, repo)
        cached = await self._get_cached(cache_key)
        if cached and isinstance(cached, dict):
            return cached.get("count", 0)

        try:
            query = f'"{owner}/{repo}" in:file filename:package.json OR filename:requirements.txt'
            data = await self._request(
                client,
                f"/search/code?q={query}&per_page=1",
            )
            count = min(data.get("total_count", 0), 100_000)
            await self._set_cached(cache_key, {"count": count}, ttl=86400)
            return count
        except Exception:
            logger.exception(f"Failed to fetch dependents for {owner}/{repo}")
            return 0

    async def fetch_stars_history(self, owner: str, repo: str, days: int = 30) -> list[dict]:
        cache_key = self._cache_key("stars_history", owner, repo, str(days))
        cached = await self._get_cached(cache_key)
        if cached and isinstance(cached, list):
            return cached

        headers = {**self.headers, "Accept": "application/vnd.github.star+json"}
        async with httpx.AsyncClient(base_url=self.settings.github_api_base, timeout=30) as client:
            try:
                stars = await self._request_with_headers(
                    client,
                    f"/repos/{owner}/{repo}/stargazers?per_page=100&sort=created&direction=desc",
                    headers,
                )

                if not isinstance(stars, list):
                    return []

                cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                recent = []
                for s in stars:
                    starred_at = s.get("starred_at")
                    if not starred_at:
                        continue
                    try:
                        ts = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
                        if ts > cutoff:
                            recent.append(s)
                    except (ValueError, TypeError):
                        continue

                await self._set_cached(cache_key, recent, ttl=7200)
                return recent
            except Exception:
                logger.exception(f"Failed to fetch stars history for {owner}/{repo}")
                return []

    async def crawl_multiple(self, repos: list[tuple[str, str]]) -> dict[str, dict]:
        results = {}
        tasks = [self.fetch_repo_stats(owner, repo) for owner, repo in repos]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for (owner, repo), result in zip(repos, completed):
            key = f"{owner}/{repo}"
            if isinstance(result, Exception):
                logger.error(f"Failed to crawl {key}: {result}")
                results[key] = {"error": str(result)}
            else:
                results[key] = result

        return results
