"""
Projects API — CRUD dự án truyện.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies.auth import get_current_user
from app.db.postgres.session import get_db
from app.db.neo4j.session import get_neo4j_session
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_internal_user_id(clerk_id: str, db: AsyncSession) -> str:
    """Lấy UUID nội bộ của user từ clerk_id."""
    result = await db.execute(
        text("SELECT id FROM users WHERE clerk_id = :clerk_id"),
        {"clerk_id": clerk_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found. Call /users/sync first.")
    return str(row.id)


@router.get("", response_model=list[ProjectListResponse])
async def list_projects(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liệt kê tất cả projects của user (chưa bị soft-delete)."""
    user_id = await _get_internal_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            SELECT id, title, description, created_at, updated_at
            FROM projects
            WHERE user_id = :user_id AND (is_deleted IS NOT TRUE)
            ORDER BY created_at DESC
        """),
        {"user_id": user_id},
    )
    rows = result.fetchall()
    return [
        ProjectListResponse(
            id=str(r.id),
            title=r.title,
            description=r.description,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tạo project mới."""
    user_id = await _get_internal_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            INSERT INTO projects (id, user_id, title, description, created_at, updated_at)
            VALUES (gen_random_uuid(), :user_id, :title, :description, NOW(), NOW())
            RETURNING id, user_id, title, description, created_at, updated_at
        """),
        {"user_id": user_id, "title": body.title, "description": body.description or ""},
    )
    row = result.fetchone()
    return ProjectResponse(
        id=str(row.id),
        user_id=str(row.user_id),
        title=row.title,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lấy chi tiết một project."""
    user_id = await _get_internal_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            SELECT id, user_id, title, description, created_at, updated_at
            FROM projects
            WHERE id = :project_id AND user_id = :user_id AND (is_deleted IS NOT TRUE)
        """),
        {"project_id": project_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        id=str(row.id),
        user_id=str(row.user_id),
        title=row.title,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật title / description của project."""
    user_id = await _get_internal_user_id(payload["sub"], db)

    updates: dict = {}
    if body.title is not None:
        updates["title"] = body.title
    if body.description is not None:
        updates["description"] = body.description

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    params = {"project_id": project_id, "user_id": user_id, **updates}

    result = await db.execute(
        text(f"""
            UPDATE projects
            SET {set_clause}, updated_at = NOW()
            WHERE id = :project_id AND user_id = :user_id AND (is_deleted IS NOT TRUE)
            RETURNING id, user_id, title, description, created_at, updated_at
        """),
        params,
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.commit()
    return ProjectResponse(
        id=str(row.id),
        user_id=str(row.user_id),
        title=row.title,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ProjectStats(BaseModel):
    character_count: int
    chapter_count: int
    lorebook_count: int
    chat_count: int


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
):
    """Lấy số liệu thống kê của project (dashboard metrics)."""
    user_id = await _get_internal_user_id(payload["sub"], db)

    # Verify ownership
    check = await db.execute(
        text("SELECT id FROM projects WHERE id = :project_id AND user_id = :user_id AND (is_deleted IS NOT TRUE)"),
        {"project_id": project_id, "user_id": user_id},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")

    # Postgres counts (chapter, lorebook, chat)
    counts = await db.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM chapters   WHERE project_id = :pid AND (is_deleted IS NOT TRUE)) AS chapter_count,
                (SELECT COUNT(*) FROM lorebooks  WHERE project_id = :pid) AS lorebook_count,
                (SELECT COUNT(*) FROM chats      WHERE project_id = :pid AND (is_deleted IS NOT TRUE)) AS chat_count
        """),
        {"pid": project_id},
    )
    row = counts.fetchone()

    # Neo4j character count (Person nodes)
    char_count = 0
    try:
        result = await neo4j_session.run(
            "MATCH (n:Person {project_id: $project_id}) RETURN count(n) AS cnt",
            project_id=project_id,
        )
        record = await result.single()
        if record:
            char_count = record["cnt"]
    except Exception:
        pass

    return ProjectStats(
        character_count=char_count,
        chapter_count=row.chapter_count if row else 0,
        lorebook_count=row.lorebook_count if row else 0,
        chat_count=row.chat_count if row else 0,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete project. Trigger background job dọn Neo4j + Qdrant.
    """
    user_id = await _get_internal_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            UPDATE projects
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE id = :project_id AND user_id = :user_id AND (is_deleted IS NOT TRUE)
            RETURNING id
        """),
        {"project_id": project_id, "user_id": user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")

    # Trigger Celery cleanup task
    try:
        from app.workers.tasks import cleanup_deleted_project
        cleanup_deleted_project.delay(project_id, user_id)
    except Exception:
        pass  # Celery unavailable — cleanup sẽ chạy sau

    return None
