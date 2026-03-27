"""
Shared auth helpers: extract user info from Supabase JWT and ensure user row exists.
"""
import logging
from dataclasses import dataclass

from app.core.supabase import get_supabase_admin

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    id: str
    github_username: str | None
    email: str | None
    avatar_url: str | None
    github_id: str | None


def get_auth_user(authorization: str | None) -> AuthUser | None:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    try:
        from supabase import create_client
        from app.core.config import get_settings
        settings = get_settings()
        client = create_client(settings.supabase_url, settings.supabase_key)
        user_response = client.auth.get_user(token)
        if not user_response.user:
            return None
        u = user_response.user
        meta = u.user_metadata or {}
        auth_user = AuthUser(
            id=str(u.id),
            github_username=meta.get("user_name"),
            email=u.email,
            avatar_url=meta.get("avatar_url"),
            github_id=meta.get("provider_id", str(u.id)),
        )
        _ensure_user_row(auth_user)
        return auth_user
    except Exception:
        logger.exception("Failed to get auth user from token")
        return None


def _ensure_user_row(user: AuthUser) -> None:
    """Upsert the user into the public.users table so FK constraints are satisfied."""
    try:
        db = get_supabase_admin()
        db.table("users").upsert(
            {
                "id": user.id,
                "github_id": user.github_id or user.id,
                "github_username": user.github_username or "unknown",
                "avatar_url": user.avatar_url,
                "display_name": user.github_username,
                "email": user.email,
            },
            on_conflict="id",
        ).execute()
    except Exception:
        logger.exception("Failed to ensure user row exists")
