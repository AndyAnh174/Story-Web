"""
Lorebooks API — CRUD từ điển thuật ngữ / luật lệ của từng project.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies.auth import get_current_user
from app.db.postgres.session import get_db
from app.schemas.lorebook import LorebookCreate, LorebookUpdate, LorebookResponse

router = APIRouter(tags=["lorebooks"])


async def _get_user_id(clerk_id: str, db: AsyncSession) -> str:
    result = await db.execute(
        text("SELECT id FROM users WHERE clerk_id = :clerk_id"),
        {"clerk_id": clerk_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found. Call /users/sync first.")
    return str(row.id)


async def _assert_project_owner(project_id: str, user_id: str, db: AsyncSession):
    result = await db.execute(
        text("""
            SELECT id FROM projects
            WHERE id = :project_id AND user_id = :user_id AND (is_deleted IS NOT TRUE)
        """),
        {"project_id": project_id, "user_id": user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/projects/{project_id}/lorebooks", response_model=list[LorebookResponse])
async def list_lorebooks(
    project_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liệt kê tất cả lorebook entries của project."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    result = await db.execute(
        text("""
            SELECT id, project_id, keyword, category, description, created_at, updated_at
            FROM lorebooks
            WHERE project_id = :project_id
            ORDER BY category, keyword
        """),
        {"project_id": project_id},
    )
    rows = result.fetchall()
    return [
        LorebookResponse(
            id=str(r.id),
            project_id=str(r.project_id),
            keyword=r.keyword,
            category=r.category,
            description=r.description,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/projects/{project_id}/lorebooks", response_model=LorebookResponse, status_code=201)
async def create_lorebook(
    project_id: str,
    body: LorebookCreate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo lorebook entry mới.
    fts_vector được cập nhật tự động bởi trigger trong Postgres.
    """
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    result = await db.execute(
        text("""
            INSERT INTO lorebooks (id, project_id, keyword, category, description, created_at, updated_at)
            VALUES (gen_random_uuid(), :project_id, :keyword, :category, :description, NOW(), NOW())
            RETURNING id, project_id, keyword, category, description, created_at, updated_at
        """),
        {
            "project_id": project_id,
            "keyword": body.keyword,
            "category": body.category,
            "description": body.description,
        },
    )
    row = result.fetchone()
    return LorebookResponse(
        id=str(row.id),
        project_id=str(row.project_id),
        keyword=row.keyword,
        category=row.category,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.patch("/lorebooks/{lorebook_id}", response_model=LorebookResponse)
async def update_lorebook(
    lorebook_id: str,
    body: LorebookUpdate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật lorebook entry (partial update)."""
    user_id = await _get_user_id(payload["sub"], db)

    # Xác nhận quyền sở hữu qua join
    check = await db.execute(
        text("""
            SELECT l.id FROM lorebooks l
            JOIN projects p ON p.id = l.project_id
            WHERE l.id = :lorebook_id AND p.user_id = :user_id
        """),
        {"lorebook_id": lorebook_id, "user_id": user_id},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Lorebook entry not found")

    # Build SET clause động (chỉ update field được gửi)
    updates = {}
    if body.keyword is not None:
        updates["keyword"] = body.keyword
    if body.category is not None:
        updates["category"] = body.category
    if body.description is not None:
        updates["description"] = body.description

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["lorebook_id"] = lorebook_id

    result = await db.execute(
        text(f"""
            UPDATE lorebooks
            SET {set_clause}, updated_at = NOW()
            WHERE id = :lorebook_id
            RETURNING id, project_id, keyword, category, description, created_at, updated_at
        """),
        updates,
    )
    row = result.fetchone()
    return LorebookResponse(
        id=str(row.id),
        project_id=str(row.project_id),
        keyword=row.keyword,
        category=row.category,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete("/lorebooks/{lorebook_id}", status_code=204)
async def delete_lorebook(
    lorebook_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hard delete lorebook entry."""
    user_id = await _get_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            DELETE FROM lorebooks
            WHERE id = :lorebook_id
              AND project_id IN (
                  SELECT id FROM projects WHERE user_id = :user_id
              )
            RETURNING id
        """),
        {"lorebook_id": lorebook_id, "user_id": user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Lorebook entry not found")
    return None
