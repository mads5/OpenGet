from pydantic import BaseModel, HttpUrl
from datetime import datetime
from uuid import UUID


class ListRepoRequest(BaseModel):
    github_url: HttpUrl


class RepoResponse(BaseModel):
    id: UUID
    github_url: str
    owner: str
    repo_name: str
    full_name: str
    description: str | None = None
    language: str | None = None
    stars: int = 0
    forks: int = 0
    listed_by: UUID
    contributor_count: int = 0
    contributors_fetched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepoListResponse(BaseModel):
    repos: list[RepoResponse]
    total: int
    page: int
    per_page: int


class GitHubRepoInfo(BaseModel):
    """A repo returned from GitHub API for the 'list your repos' flow."""
    full_name: str
    html_url: str
    description: str | None = None
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    already_listed: bool = False
