"""GET /me: the platform-authenticated caller's profile.

Every hit upserts con.app_user (api/auth.py resolves the caller from the
x-ms-client-principal / Easy Auth headers) so the profile stays current and
last_seen_at tracks activity; a plain UPDATE-then-INSERT is used rather than
MERGE to match the parameterized-cursor style already used across api/deps.py
and the other routers.
"""

from typing import Any

from fastapi import APIRouter, Depends

from api.auth import CurrentUser, require_user
from api.deps import drop_none, get_db

router = APIRouter()


@router.get("/me")
def get_me(
    user: CurrentUser = Depends(require_user), conn: Any = Depends(get_db)
) -> dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM con.app_user WHERE user_id = ?", [user.id])
    if cursor.fetchone():
        cursor.execute(
            "UPDATE con.app_user SET upn = ?, email = ?, display_name = ?, "
            "identity_provider = ?, last_seen_at = SYSUTCDATETIME() WHERE user_id = ?",
            [user.upn, user.email, user.name, user.provider, user.id],
        )
    else:
        cursor.execute(
            "INSERT INTO con.app_user (user_id, upn, email, display_name, identity_provider) "
            "VALUES (?, ?, ?, ?, ?)",
            [user.id, user.upn, user.email, user.name, user.provider],
        )
    conn.commit()
    return drop_none(
        {
            "id": user.id,
            "upn": user.upn,
            "email": user.email,
            "name": user.name,
            "provider": user.provider,
            "roles": user.roles,
        }
    )
