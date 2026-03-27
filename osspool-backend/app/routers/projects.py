from fastapi import APIRouter, HTTPException, Query, Header
from uuid import UUID

from app.core.supabase import get_supabase_admin
from app.schemas.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from app.tasks.crawler_tasks import crawl_single_project

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    language: str | None = None,
    search: str | None = None,
):
    db = get_supabase_admin()
    query = db.table("projects").select("*", count="exact").eq("is_active", True)

    if language:
        query = query.eq("language", language)
    if search:
        query = query.ilike("name", f"%{search}%")

    offset = (page - 1) * per_page
    result = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

    return {
        "projects": result.data or [],
        "total": result.count or 0,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID):
    db = get_supabase_admin()
    result = db.table("projects").select("*").eq("id", str(project_id)).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return result.data


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    authorization: str | None = Header(None),
):
    db = get_supabase_admin()

    existing = (
        db.table("projects")
        .select("id")
        .eq("github_url", str(project.github_url))
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Project already registered")

    parts = str(project.github_url).rstrip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    owner_github_id = parts[-2]

    data = {
        **project.model_dump(mode="json"),
        "github_url": str(project.github_url),
        "owner_github_id": owner_github_id,
        "is_active": True,
    }
    result = db.table("projects").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create project")

    project_row = result.data[0]

    user_result = db.table("users").select("id").eq("github_username", owner_github_id).execute()
    if user_result.data:
        db.table("project_owners").insert({
            "project_id": project_row["id"],
            "user_id": user_result.data[0]["id"],
            "role": "owner",
        }).execute()

    crawl_single_project.delay(str(project_row["id"]))
    return project_row


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, update: ProjectUpdate):
    db = get_supabase_admin()
    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.table("projects").update(data).eq("id", str(project_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return result.data[0]


@router.post("/{project_id}/crawl")
async def trigger_crawl(project_id: UUID):
    task = crawl_single_project.delay(str(project_id))
    return {"task_id": task.id, "status": "queued"}
