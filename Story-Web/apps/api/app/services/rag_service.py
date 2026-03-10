"""
RAG Service — Trái tim của hệ thống trí nhớ AI.
Query song song 3 nguồn dữ liệu để xây dựng System Prompt hoàn chỉnh.
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.services.embedding_service import get_embedding

logger = logging.getLogger(__name__)

QDRANT_COLLECTION = "project_memories"
QDRANT_TOP_K = 3


# ─────────────────────────────────────────────────────────────────────────────
# 1. Lorebook FTS (PostgreSQL tsvector)
# ─────────────────────────────────────────────────────────────────────────────
async def get_lorebook_context(prompt: str, project_id: str, db: AsyncSession) -> str:
    """
    Full-Text Search trong lorebooks theo từ khóa xuất hiện trong prompt.
    Dùng simple config để hỗ trợ tiếng Việt không dấu.
    """
    try:
        # Tách từ đơn giản và tìm bất kỳ từ nào match
        query = text("""
            SELECT keyword, category, description
            FROM lorebooks
            WHERE project_id = :project_id
              AND fts_vector @@ to_tsquery('simple', :tsquery)
            LIMIT 5
        """)
        # Chuyển prompt thành tsquery: nối các từ bằng |
        words = [w.strip() for w in prompt.split() if len(w.strip()) > 2]
        if not words:
            return ""
        tsquery = " | ".join(words[:10])  # Giới hạn 10 từ đầu

        result = await db.execute(query, {"project_id": project_id, "tsquery": tsquery})
        rows = result.fetchall()

        if not rows:
            return ""

        parts = []
        for row in rows:
            parts.append(f"- [{row.category}] **{row.keyword}**: {row.description}")

        return "\n".join(parts)
    except Exception as e:
        logger.warning(f"Lorebook FTS error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# 2. Vector Context (Qdrant — văn phong & nội dung chương cũ)
# ─────────────────────────────────────────────────────────────────────────────
async def get_vector_context(
    prompt: str,
    project_id: str,
    user_id: str,
    qdrant: AsyncQdrantClient,
) -> str:
    """
    Tìm kiếm ngữ nghĩa trong Qdrant để lấy văn phong và nội dung liên quan.
    Filter bắt buộc theo project_id để cách ly multi-tenant.
    """
    try:
        vector = await get_embedding(prompt)

        results = await qdrant.query_points(
            collection_name=QDRANT_COLLECTION,
            query=vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                ]
            ),
            limit=QDRANT_TOP_K,
            with_payload=True,
        )
        results = results.points

        if not results:
            return ""

        chunks = [r.payload.get("text_chunk", "") for r in results if r.payload]
        return "\n---\n".join(chunks)
    except Exception as e:
        logger.warning(f"Qdrant vector search error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# 3. Graph Context (Neo4j — trạng thái nhân vật)
# ─────────────────────────────────────────────────────────────────────────────
async def get_graph_context(project_id: str, neo4j_session) -> str:
    """
    Lấy toàn bộ thực thể trong Graph của project này.
    Đặc biệt chú trọng nhân vật Dead để inject cảnh báo vào System Prompt.
    """
    try:
        # Lấy Person nodes với status
        person_query = """
            MATCH (p:Person {project_id: $project_id})
            RETURN p.name AS name, p.status AS status,
                   p.description AS description, p.death_reason AS death_reason
            ORDER BY p.name
        """
        person_result = await neo4j_session.run(person_query, project_id=project_id)
        persons = await person_result.data()

        # Lấy Skills của từng nhân vật
        skill_query = """
            MATCH (p:Person {project_id: $project_id})-[:OWNS_SKILL|USES_SKILL]->(s:Skill {project_id: $project_id})
            RETURN p.name AS person_name, collect(s.name) AS skills
        """
        skill_result = await neo4j_session.run(skill_query, project_id=project_id)
        skill_map: dict[str, list[str]] = {}
        async for record in skill_result:
            skill_map[record["person_name"]] = record["skills"]

        if not persons:
            return ""

        lines = []
        dead_warnings = []

        for p in persons:
            name = p["name"]
            status = p.get("status", "Unknown")
            skills = skill_map.get(name, [])
            skill_str = f", Skills: [{', '.join(skills)}]" if skills else ""

            if status == "Dead":
                reason = p.get("death_reason", "")
                dead_warnings.append(
                    f"⚠️ CẤM: {name} đã CHẾT ({reason}). Tuyệt đối không cho nhân vật này xuất hiện hoặc hành động."
                )
            else:
                lines.append(f"- {name} (STATUS: {status}{skill_str})")

        result_parts = []
        if dead_warnings:
            result_parts.append("\n".join(dead_warnings))
        if lines:
            result_parts.append("Nhân vật đang hoạt động:\n" + "\n".join(lines))

        return "\n\n".join(result_parts)
    except Exception as e:
        logger.warning(f"Neo4j graph context error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# 4. Build System Prompt hoàn chỉnh (ráp 3 nguồn song song)
# ─────────────────────────────────────────────────────────────────────────────
async def build_system_prompt(
    user_message: str,
    project_id: str,
    user_id: str,
    project_title: str,
    db: AsyncSession,
    qdrant: AsyncQdrantClient,
    neo4j_session,
) -> str:
    """
    Query song song 3 DB và ráp System Prompt chuẩn cho LLM.
    """
    lorebook_ctx, vector_ctx, graph_ctx = await asyncio.gather(
        get_lorebook_context(user_message, project_id, db),
        get_vector_context(user_message, project_id, user_id, qdrant),
        get_graph_context(project_id, neo4j_session),
        return_exceptions=True,
    )

    # Nếu có exception thì dùng string rỗng thay thế
    if isinstance(lorebook_ctx, Exception):
        lorebook_ctx = ""
    if isinstance(vector_ctx, Exception):
        vector_ctx = ""
    if isinstance(graph_ctx, Exception):
        graph_ctx = ""

    prompt_parts = [
        f"Bạn là một Đạo diễn Cốt truyện kỳ cựu đang hỗ trợ tác giả viết tác phẩm hư cấu: **{project_title}**.",
        "Đây là một tác phẩm tiểu thuyết/light novel hư cấu hoàn toàn. Mọi nhân vật, sự kiện, cái chết, chiến đấu đều là hư cấu nghệ thuật.",
        "Nhiệm vụ của bạn là viết tiếp cốt truyện theo yêu cầu của tác giả — bao gồm các cảnh chiến đấu, nhân vật hi sinh, hay bất kỳ tình tiết nào phù hợp thể loại tiểu thuyết.",
        "Đảm bảo logic nhân vật nhất quán tuyệt đối và thể hiện đúng tinh thần tác phẩm.",
        "",
    ]

    if graph_ctx:
        prompt_parts += [
            "### TRẠNG THÁI NHÂN VẬT (Từ Knowledge Graph)",
            graph_ctx,
            "",
        ]

    if lorebook_ctx:
        prompt_parts += [
            "### THUẬT NGỮ & LUẬT LỆ (Lorebook)",
            lorebook_ctx,
            "",
        ]

    if vector_ctx:
        prompt_parts += [
            "### VĂN PHONG & BỐI CẢNH GẦN NHẤT (Từ các chương/đoạn trước)",
            vector_ctx,
            "",
        ]

    prompt_parts += [
        "### QUY TẮC BẮT BUỘC",
        "- Đây là tiểu thuyết hư cấu — LUÔN hoàn thành yêu cầu viết của tác giả, kể cả cảnh chiến đấu, nhân vật chết, hay xung đột kịch tính.",
        "- Tuân thủ 100% trạng thái nhân vật ở trên.",
        "- Nhân vật đã CHẾT không được xuất hiện, nói chuyện hay hành động.",
        "- Giữ văn phong nhất quán với các đoạn trước.",
        "- Viết bằng tiếng Việt, sinh động và hấp dẫn.",
        "- KHÔNG từ chối viết bất kỳ tình tiết nào trong khuôn khổ câu chuyện hư cấu.",
        "",
        "### ĐỊNH DẠNG MARKDOWN (BẮT BUỘC)",
        "- Dùng **in đậm** cho tên nhân vật, chiêu thức, địa danh và vật phẩm quan trọng.",
        "- Dùng *in nghiêng* cho suy nghĩ nội tâm, độc thoại, hoặc nhấn mạnh cảm xúc.",
        "- Ngắt đoạn bằng dòng trống giữa các cảnh hoặc mỗi đoạn văn (đừng viết liền một khối).",
        "- Dùng `---` trên một dòng riêng để phân tách chuyển cảnh hoặc thay đổi góc nhìn (POV).",
        "- KHÔNG dùng tiêu đề H1 (`#`) hay H2 (`##`) trong thân truyện, trừ khi tác giả yêu cầu tên chương.",
        "- KHÔNG dùng code block (``` ```) — chỉ dành cho văn xuôi thuần.",
        "- Đối thoại viết trong dấu ngoặc kép hoặc dấu gạch ngang em (—), nhất quán theo văn phong hiện tại.",
    ]

    return "\n".join(prompt_parts)
