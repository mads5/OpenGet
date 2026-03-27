from fastapi import APIRouter, HTTPException, Query, Header
from uuid import UUID

from app.core.auth import get_auth_user
from app.services.contributor_service import ContributorService

router = APIRouter(prefix="/contributors", tags=["contributors"])


@router.get("")
async def list_contributors(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    service = ContributorService()
    return await service.get_contributor_leaderboard(page, per_page)


@router.get("/{contributor_id}")
async def get_contributor(contributor_id: UUID):
    service = ContributorService()
    detail = await service.get_contributor_detail(str(contributor_id))
    if not detail:
        raise HTTPException(status_code=404, detail="Contributor not found")
    return detail


@router.post("/register")
async def register_contributor(authorization: str | None = Header(None)):
    user = get_auth_user(authorization)
    if not user or not user.github_username:
        raise HTTPException(status_code=401, detail="Sign in with GitHub to register")

    service = ContributorService()
    try:
        return await service.register_contributor(user.id, user.github_username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
