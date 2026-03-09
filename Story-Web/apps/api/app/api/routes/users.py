"""
Users API — Đồng bộ user từ Clerk vào Postgres.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies.auth import get_current_user
from app.db.postgres.session import get_db
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync", response_model=UserResponse)
async def sync_user(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Đồng bộ user từ Clerk JWT vào Postgres.
    Upsert theo clerk_id (sub từ JWT payload).
    """
    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=400, detail="Invalid Clerk token: missing sub")

    email = payload.get("email", "")
    # Clerk JWT có thể chứa email trong primary_email_address hoặc email
    if not email:
        emails = payload.get("email_addresses", [])
        if emails:
            email = emails[0].get("email_address", "")

    result = await db.execute(
        text("""
            INSERT INTO users (id, clerk_id, email, created_at)
            VALUES (gen_random_uuid(), :clerk_id, :email, NOW())
            ON CONFLICT (clerk_id) DO UPDATE
                SET email = EXCLUDED.email
            RETURNING id, clerk_id, email, name, created_at
        """),
        {"clerk_id": clerk_id, "email": email},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="User sync failed")

    return UserResponse(
        id=str(row.id),
        clerk_id=row.clerk_id,
        email=row.email,
        name=row.name,
        created_at=row.created_at,
    )
