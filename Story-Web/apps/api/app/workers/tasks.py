"""
Celery Tasks — Entity Extraction + Project Cleanup.
"""
import asyncio
import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Chạy coroutine trong Celery (sync context)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def extract_and_update(self, content: str, project_id: str):
    """
    Sau khi AI stream xong:
    1. Extract entities từ nội dung mới (LLM structured output)
    2. Cập nhật Neo4j graph
    3. Embed content → upsert vào Qdrant
    """
    try:
        _run_async(_extract_and_update_async(content, project_id))
    except Exception as exc:
        logger.error(f"extract_and_update failed for project {project_id}: {exc}")
        raise self.retry(exc=exc)


async def _extract_and_update_async(content: str, project_id: str):
    from app.services.context_extractor import extract_entities, update_neo4j_from_extraction
    from app.services.embedding_service import get_embedding
    from app.db.neo4j.session import neo4j_db
    from app.db.qdrant.session import qdrant_db
    from qdrant_client.models import PointStruct
    import uuid

    # 1. Entity extraction
    extracted = await extract_entities(content, project_id)

    # 2. Neo4j update — luôn tạo kết nối mới (tránh lỗi asyncio event loop reuse trên Windows)
    from neo4j import AsyncGraphDatabase
    from app.core.config import settings
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    try:
        async with neo4j_driver.session() as neo4j_session:
            await update_neo4j_from_extraction(extracted, project_id, neo4j_session)
    finally:
        await neo4j_driver.close()

    # 3. Embed + upsert vào Qdrant (non-critical — không retry nếu embed server offline)
    try:
        if not qdrant_db.client:
            qdrant_db.connect()
        if not qdrant_db.client:
            raise RuntimeError("Qdrant client not initialized")
        vector = await get_embedding(content[:2000])
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "project_id": project_id,
                "text_chunk": content[:2000],
            },
        )
        await qdrant_db.client.upsert(
            collection_name="project_memories",
            points=[point],
        )
        logger.info(f"Qdrant upsert done for project {project_id}")
    except Exception as e:
        logger.warning(f"Qdrant embedding skipped (embed server unavailable): {e}")

    logger.info(f"extract_and_update done for project {project_id}")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_deleted_project(self, project_id: str, user_id: str):
    """
    Khi project bị soft-delete:
    1. Xoá toàn bộ vectors trong Qdrant
    2. Xoá toàn bộ nodes/edges trong Neo4j
    3. Hard-delete project trong Postgres (CASCADE)
    """
    try:
        _run_async(_cleanup_async(project_id, user_id))
    except Exception as exc:
        logger.error(f"cleanup_deleted_project failed for {project_id}: {exc}")
        raise self.retry(exc=exc)


async def _cleanup_async(project_id: str, user_id: str):
    from app.db.neo4j.session import neo4j_db
    from app.db.qdrant.session import qdrant_db
    from app.db.postgres.session import AsyncSessionLocal
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from sqlalchemy import text

    # 1. Qdrant: xoá toàn bộ vectors của project
    if not qdrant_db.client:
        qdrant_db.connect()
    await qdrant_db.client.delete(
        collection_name="project_memories",
        points_selector=Filter(
            must=[FieldCondition(key="project_id", match=MatchValue(value=project_id))]
        ),
    )

    # 2. Neo4j: DETACH DELETE toàn bộ nodes của project
    if not neo4j_db.driver:
        await neo4j_db.connect()
    async with neo4j_db.driver.session() as neo4j_session:
        await neo4j_session.run(
            "MATCH (n {project_id: $project_id}) DETACH DELETE n",
            project_id=project_id,
        )

    # 3. Postgres: hard-delete (CASCADE sẽ xoá chats, messages, lorebooks)
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM projects WHERE id = :project_id AND user_id = :user_id"),
            {"project_id": project_id, "user_id": user_id},
        )
        await db.commit()

    logger.info(f"Cleanup done for project {project_id}")
