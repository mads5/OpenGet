from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Header
from uuid import UUID

from app.core.supabase import get_supabase_admin
from app.core.auth import get_auth_user
from app.crawler.github_crawler import GitHubCrawler, GitHubAPIError
from app.schemas.repos import RepoResponse, RepoListResponse, ListRepoRequest, GitHubRepoInfo
from app.tasks.crawler_tasks import run_fetch_repo_contributors_bg

router = APIRouter(prefix="/repos", tags=["repos"])


@router.get("", response_model=RepoListResponse)
async def list_repos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    language: str | None = None,
):
    db = get_supabase_admin()
    query = db.table("repos").select("*", count="exact")
    if language:
        query = query.eq("language", language)

    offset = (page - 1) * per_page
    result = query.order("stars", desc=True).range(offset, offset + per_page - 1).execute()
    return {
        "repos": result.data or [],
        "total": result.count or 0,
        "page": page,
        "per_page": per_page,
    }


@router.get("/mine", response_model=list[GitHubRepoInfo])
async def my_github_repos(authorization: str | None = Header(None)):
    user = get_auth_user(authorization)
    if not user or not user.github_username:
        raise HTTPException(status_code=401, detail="Sign in to view your repos")

    crawler = GitHubCrawler()
    try:
        github_repos = await crawler.fetch_user_repos(user.github_username)
    except GitHubAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))

    db = get_supabase_admin()
    listed_urls = set()
    listed_result = db.table("repos").select("github_url").execute()
    for r in listed_result.data or []:
        listed_urls.add(r["github_url"])

    response = []
    for r in github_repos:
        response.append({
            **r,
            "already_listed": r["html_url"] in listed_urls,
        })
    return response


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repo(repo_id: UUID):
    db = get_supabase_admin()
    result = db.table("repos").select("*").eq("id", str(repo_id)).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Repo not found")
    return result.data


@router.get("/{repo_id}/contributors")
async def get_repo_contributors(repo_id: UUID):
    db = get_supabase_admin()
    result = (
        db.table("repo_contributors")
        .select("*, contributors(github_username, avatar_url, total_score, user_id)")
        .eq("repo_id", str(repo_id))
        .order("score", desc=True)
        .execute()
    )
    entries = []
    for rc in result.data or []:
        c_info = rc.pop("contributors", {}) or {}
        entries.append({
            **rc,
            "github_username": c_info.get("github_username", ""),
            "avatar_url": c_info.get("avatar_url"),
            "is_registered": c_info.get("user_id") is not None,
        })
    return {"contributors": entries}


@router.post("", response_model=RepoResponse, status_code=201)
async def list_repo(
    body: ListRepoRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    user = get_auth_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to list a repo")

    github_url = str(body.github_url).rstrip("/")
    db = get_supabase_admin()

    existing = db.table("repos").select("*").eq("github_url", github_url).execute()
    if existing.data:
        return existing.data[0]

    parts = github_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    owner = parts[-2]
    repo_name = parts[-1]

    crawler = GitHubCrawler()
    try:
        info = await crawler.fetch_repo_info(owner, repo_name)
    except GitHubAPIError as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch repo: {e}")

    data = {
        "github_url": github_url,
        "owner": info["owner"],
        "repo_name": info["name"],
        "full_name": info["full_name"],
        "description": info.get("description"),
        "language": info.get("language"),
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "listed_by": user.id,
        "contributor_count": 0,
    }

    result = db.table("repos").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to list repo")

    repo_row = result.data[0]

    background_tasks.add_task(run_fetch_repo_contributors_bg, repo_row["id"])

    return repo_row
