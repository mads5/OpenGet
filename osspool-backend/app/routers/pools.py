from fastapi import APIRouter, HTTPException, Query, Header
from uuid import UUID

from app.core.supabase import get_supabase_admin
from app.schemas.pools import (
    PoolCreate,
    PoolUpdate,
    PoolResponse,
    PoolListResponse,
    DonationCreate,
    DonationResponse,
    PoolProgressResponse,
)
from app.services.pool_service import PoolService

router = APIRouter(prefix="/pools", tags=["pools"])


def _get_user_id_from_token(authorization: str | None) -> str | None:
    """Extract user ID from Supabase JWT via the admin client."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    try:
        from supabase import create_client
        from app.core.config import get_settings
        settings = get_settings()
        client = create_client(settings.supabase_url, settings.supabase_key)
        user_response = client.auth.get_user(token)
        return str(user_response.user.id) if user_response.user else None
    except Exception:
        return None


@router.get("", response_model=PoolListResponse)
async def list_pools(
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    service = PoolService()
    return await service.list_pools(status, page, per_page)


@router.get("/{pool_id}", response_model=PoolProgressResponse)
async def get_pool(pool_id: UUID):
    service = PoolService()
    pool = await service.get_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    donations = await service.get_pool_donations(pool_id)
    funding_pct = (
        (pool["current_amount_cents"] + pool["matched_pool_cents"])
        / max(pool["target_amount_cents"], 1)
        * 100
    )
    return {
        "pool": pool,
        "funding_percentage": round(funding_pct, 2),
        "donations": donations,
    }


@router.post("", response_model=PoolResponse, status_code=201)
async def create_pool(pool: PoolCreate):
    service = PoolService()
    data = {
        **pool.model_dump(mode="json"),
        "current_amount_cents": 0,
        "matched_pool_cents": 0,
        "status": "active",
        "donor_count": 0,
        "project_count": 0,
    }
    return await service.create_pool(data)


@router.patch("/{pool_id}", response_model=PoolResponse)
async def update_pool(pool_id: UUID, update: PoolUpdate):
    service = PoolService()
    pool = await service.get_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = service.db.table("money_pools").update(data).eq("id", str(pool_id)).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update pool")
    return result.data[0]


@router.post("/{pool_id}/donate", response_model=DonationResponse, status_code=201)
async def donate_to_pool(
    pool_id: UUID,
    donation: DonationCreate,
    authorization: str | None = Header(None),
):
    donor_id = _get_user_id_from_token(authorization)
    if not donor_id:
        raise HTTPException(status_code=401, detail="Authentication required to donate")

    service = PoolService()
    try:
        data = {
            **donation.model_dump(mode="json"),
            "pool_id": str(pool_id),
            "project_id": str(donation.project_id),
            "donor_id": donor_id,
        }
        return await service.add_donation(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{pool_id}/distribute")
async def distribute_pool(pool_id: UUID):
    service = PoolService()
    try:
        distributions = await service.distribute_pool(pool_id)
        return {"distributions": distributions, "count": len(distributions)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
