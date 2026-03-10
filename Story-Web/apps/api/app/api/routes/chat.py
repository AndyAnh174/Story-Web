"""
Chat API — SSE Streaming endpoint + quản lý chat sessions.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from qdrant_client import AsyncQdrantClient

from app.api.dependencies.auth import get_current_user
from app.db.postgres.session import get_db, AsyncSessionLocal
from app.db.neo4j.session import get_neo4j_session
from app.db.qdrant.session import get_qdrant_client
from app.schemas.chat import (
    ChatCreate, ChatUpdate, ChatResponse,
    ChatMessageResponse, StreamChatRequest,
)
from app.services.rag_service import build_system_prompt
from app.services.ai_service import stream_chat

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


async def _get_user_id(clerk_id: str, db: AsyncSession) -> str:
    result = await db.execute(
        text("SELECT id FROM users WHERE clerk_id = :clerk_id"),
        {"clerk_id": clerk_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found. Call /users/sync first.")
    return str(row.id)


async def _assert_project_owner(project_id: str, user_id: str, db: AsyncSession) -> str:
    """Xác nhận project thuộc về user, trả về project title."""
    result = await db.execute(
        text("""
            SELECT title FROM projects
            WHERE id = :project_id AND user_id = :user_id AND (is_deleted IS NOT TRUE)
        """),
        {"project_id": project_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return row.title


# ─── Chat Sessions ────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/chats", response_model=list[ChatResponse])
async def list_chats(
    project_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liệt kê tất cả chat sessions của một project."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    result = await db.execute(
        text("""
            SELECT id, project_id, title, created_at, updated_at
            FROM chats
            WHERE project_id = :project_id AND (is_deleted IS NOT TRUE)
            ORDER BY created_at DESC
        """),
        {"project_id": project_id},
    )
    rows = result.fetchall()
    return [
        ChatResponse(
            id=str(r.id),
            project_id=str(r.project_id),
            title=r.title,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/projects/{project_id}/chats", response_model=ChatResponse, status_code=201)
async def create_chat(
    project_id: str,
    body: ChatCreate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tạo chat session mới cho project."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    result = await db.execute(
        text("""
            INSERT INTO chats (id, project_id, title, created_at, updated_at)
            VALUES (gen_random_uuid(), :project_id, :title, NOW(), NOW())
            RETURNING id, project_id, title, created_at, updated_at
        """),
        {"project_id": project_id, "title": body.title},
    )
    row = result.fetchone()
    return ChatResponse(
        id=str(row.id),
        project_id=str(row.project_id),
        title=row.title,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ─── Delete Chat ──────────────────────────────────────────────────────────────

@router.delete("/chats/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete một chat session."""
    user_id = await _get_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            UPDATE chats c
            SET is_deleted = TRUE, updated_at = NOW()
            FROM projects p
            WHERE c.id = :chat_id
              AND c.project_id = p.id
              AND p.user_id = :user_id
              AND (c.is_deleted IS NOT TRUE)
            RETURNING c.id
        """),
        {"chat_id": chat_id, "user_id": user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Chat not found")

    await db.commit()
    return None


# ─── Rename Chat ──────────────────────────────────────────────────────────────

@router.patch("/chats/{chat_id}", response_model=ChatResponse)
async def rename_chat(
    chat_id: str,
    body: ChatUpdate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Đổi tên chat session."""
    user_id = await _get_user_id(payload["sub"], db)

    result = await db.execute(
        text("""
            UPDATE chats c
            SET title = :title, updated_at = NOW()
            FROM projects p
            WHERE c.id = :chat_id
              AND c.project_id = p.id
              AND p.user_id = :user_id
              AND (c.is_deleted IS NOT TRUE)
            RETURNING c.id, c.project_id, c.title, c.created_at, c.updated_at
        """),
        {"chat_id": chat_id, "user_id": user_id, "title": body.title.strip()},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Chat not found")

    await db.commit()
    return ChatResponse(
        id=str(row.id),
        project_id=str(row.project_id),
        title=row.title,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ─── Messages ─────────────────────────────────────────────────────────────────

@router.get("/chats/{chat_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    chat_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lấy toàn bộ messages trong một chat session."""
    user_id = await _get_user_id(payload["sub"], db)

    # Xác nhận chat thuộc về user (qua join)
    check = await db.execute(
        text("""
            SELECT c.id FROM chats c
            JOIN projects p ON p.id = c.project_id
            WHERE c.id = :chat_id AND p.user_id = :user_id
              AND (c.is_deleted IS NOT TRUE)
        """),
        {"chat_id": chat_id, "user_id": user_id},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Chat not found")

    result = await db.execute(
        text("""
            SELECT id, chat_id, role, content, created_at
            FROM chat_messages
            WHERE chat_id = :chat_id
            ORDER BY created_at ASC
        """),
        {"chat_id": chat_id},
    )
    rows = result.fetchall()
    return [
        ChatMessageResponse(
            id=str(r.id),
            chat_id=str(r.chat_id),
            role=r.role,
            content=r.content,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ─── SSE Streaming — Core Endpoint ────────────────────────────────────────────

@router.post("/chats/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    body: StreamChatRequest,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
    qdrant: AsyncQdrantClient = Depends(get_qdrant_client),
):
    """
    SSE Streaming endpoint — trái tim của hệ thống.
    1. Build system prompt từ RAG (3 nguồn song song)
    2. Stream phản hồi từ LLM
    3. Lưu messages vào Postgres
    4. Trigger Celery entity extraction
    """
    user_id = await _get_user_id(payload["sub"], db)

    # Lấy project_id và title từ chat
    chat_row = await db.execute(
        text("""
            SELECT c.project_id, p.title AS project_title
            FROM chats c
            JOIN projects p ON p.id = c.project_id
            WHERE c.id = :chat_id AND p.user_id = :user_id
              AND (c.is_deleted IS NOT TRUE) AND (p.is_deleted IS NOT TRUE)
        """),
        {"chat_id": chat_id, "user_id": user_id},
    )
    chat_info = chat_row.fetchone()
    if not chat_info:
        raise HTTPException(status_code=404, detail="Chat not found")

    project_id = str(chat_info.project_id)
    project_title = chat_info.project_title

    # Lưu user message vào DB
    await db.execute(
        text("""
            INSERT INTO chat_messages (id, chat_id, role, content, created_at)
            VALUES (gen_random_uuid(), :chat_id, 'user', :content, NOW())
        """),
        {"chat_id": chat_id, "content": body.content},
    )
    await db.commit()

    async def event_generator():
        full_response = []

        try:
            # Dùng session MỚI vì session từ Depends đã bị đóng khi StreamingResponse được tạo
            async with AsyncSessionLocal() as gen_db:
                # Build system prompt qua RAG
                system_prompt = await build_system_prompt(
                    user_message=body.content,
                    project_id=project_id,
                    user_id=user_id,
                    project_title=project_title,
                    db=gen_db,
                    qdrant=qdrant,
                    neo4j_session=neo4j_session,
                )

            # Gắn custom system prompt của tác giả (nếu có)
            if body.custom_system_prompt and body.custom_system_prompt.strip():
                system_prompt += f"\n\n### HƯỚNG DẪN RIÊNG CỦA TÁC GIẢ\n{body.custom_system_prompt.strip()}"

            # Stream từ LLM (ngoài DB session để tránh timeout)
            async for chunk in stream_chat(system_prompt, body.content, model=body.model):
                full_response.append(chunk)
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Lưu AI response
            ai_content = "".join(full_response)
            if ai_content:
                async with AsyncSessionLocal() as save_db:
                    await save_db.execute(
                        text("""
                            INSERT INTO chat_messages (id, chat_id, role, content, created_at)
                            VALUES (gen_random_uuid(), :chat_id, 'ai', :content, NOW())
                        """),
                        {"chat_id": chat_id, "content": ai_content},
                    )
                    await save_db.commit()

            # Trigger Celery entity extraction (background)
            try:
                from app.workers.tasks import extract_and_update
                extract_and_update.delay(ai_content, project_id)
            except Exception:
                pass  # Celery unavailable — skip

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Stream error for chat {chat_id}: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
