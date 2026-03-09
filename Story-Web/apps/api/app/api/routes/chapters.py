"""
Chapters API — "Chốt nội dung" flow.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies.auth import get_current_user
from app.db.postgres.session import get_db
from app.schemas.chapter import ChapterCreate, ChapterUpdate, ChapterResponse

router = APIRouter(tags=["chapters"])


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


@router.get("/projects/{project_id}/chapters", response_model=list[ChapterResponse])
async def list_chapters(
    project_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liệt kê tất cả chapters của project theo order_index tăng dần."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    result = await db.execute(
        text("""
            SELECT id, project_id, title, content, order_index, created_at, updated_at
            FROM chapters
            WHERE project_id = :project_id AND (is_deleted IS NOT TRUE)
            ORDER BY order_index ASC
        """),
        {"project_id": project_id},
    )
    rows = result.fetchall()
    return [
        ChapterResponse(
            id=str(r.id),
            project_id=str(r.project_id),
            title=r.title,
            content=r.content,
            order_index=r.order_index,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/projects/{project_id}/chapters", response_model=ChapterResponse, status_code=201)
async def create_chapter(
    project_id: str,
    body: ChapterCreate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo chapter mới = "Chốt nội dung".
    Sau khi INSERT → trigger Celery entity extraction.
    """
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    result = await db.execute(
        text("""
            INSERT INTO chapters (id, project_id, title, content, order_index, created_at, updated_at)
            VALUES (gen_random_uuid(), :project_id, :title, :content, :order_index, NOW(), NOW())
            RETURNING id, project_id, title, content, order_index, created_at, updated_at
        """),
        {
            "project_id": project_id,
            "title": body.title,
            "content": body.content,
            "order_index": body.order_index,
        },
    )
    row = result.fetchone()
    await db.commit()

    # Trigger Celery entity extraction for chapter content
    try:
        from app.workers.tasks import extract_and_update
        extract_and_update.delay(body.content, project_id)
    except Exception:
        pass  # Celery unavailable — skip

    return ChapterResponse(
        id=str(row.id),
        project_id=str(row.project_id),
        title=row.title,
        content=row.content,
        order_index=row.order_index,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.patch("/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: str,
    body: ChapterUpdate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật title / content / order_index của chapter."""
    user_id = await _get_user_id(payload["sub"], db)

    # Validate ownership via join
    check = await db.execute(
        text("""
            SELECT ch.id FROM chapters ch
            JOIN projects p ON p.id = ch.project_id
            WHERE ch.id = :chapter_id AND p.user_id = :user_id
              AND (ch.is_deleted IS NOT TRUE)
        """),
        {"chapter_id": chapter_id, "user_id": user_id},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Chapter not found")

    updates: dict = {}
    if body.title is not None:
        updates["title"] = body.title
    if body.content is not None:
        updates["content"] = body.content
    if body.order_index is not None:
        updates["order_index"] = body.order_index

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    params = {"chapter_id": chapter_id, **updates}

    result = await db.execute(
        text(f"""
            UPDATE chapters
            SET {set_clause}, updated_at = NOW()
            WHERE id = :chapter_id
            RETURNING id, project_id, title, content, order_index, created_at, updated_at
        """),
        params,
    )
    row = result.fetchone()
    await db.commit()

    return ChapterResponse(
        id=str(row.id),
        project_id=str(row.project_id),
        title=row.title,
        content=row.content,
        order_index=row.order_index,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete("/chapters/{chapter_id}", status_code=204)
async def delete_chapter(
    chapter_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete chapter."""
    user_id = await _get_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            UPDATE chapters ch
            SET is_deleted = TRUE, updated_at = NOW()
            FROM projects p
            WHERE ch.id = :chapter_id
              AND ch.project_id = p.id
              AND p.user_id = :user_id
              AND (ch.is_deleted IS NOT TRUE)
            RETURNING ch.id
        """),
        {"chapter_id": chapter_id, "user_id": user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Chapter not found")

    await db.commit()
    return None
