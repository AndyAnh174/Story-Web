"""
Context Extractor — Bóc tách thực thể từ nội dung truyện và cập nhật Neo4j.
Chạy ngầm sau mỗi lần tác giả "Chốt" nội dung.
"""
import json
import logging
import re
from app.services.ai_service import generate_once

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """Bạn là một hệ thống phân tích cốt truyện. Hãy đọc đoạn văn sau và trích xuất thông tin theo format JSON CHÍNH XÁC.

ĐOẠN VĂN:
{content}

Hãy trả về JSON với cấu trúc SAU (chỉ JSON, không giải thích thêm):
{{
  "new_characters": [
    {{"name": "string", "description": "string"}}
  ],
  "new_skills": [
    {{"name": "string", "used_by": "string", "description": "string"}}
  ],
  "character_status_changes": [
    {{"name": "string", "old_status": "Alive|Unknown", "new_status": "Dead|Alive", "reason": "string"}}
  ],
  "new_events": [
    {{"name": "string", "participants": ["string"], "outcome": "string"}}
  ],
  "new_locations": [
    {{"name": "string", "description": "string"}}
  ]
}}

Nếu không có dữ liệu cho một mục, để array rỗng []. Chỉ trả về JSON."""


async def extract_entities(content: str, project_id: str) -> dict:
    """
    Dùng LLM để bóc tách thực thể mới từ nội dung vừa được chốt.
    Return dict JSON với các thực thể được phân loại.
    """
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(content=content[:3000])  # Giới hạn context

    try:
        raw_output = await generate_once(prompt)

        # Tách JSON khỏi text thừa nếu có
        json_match = re.search(r'\{[\s\S]*\}', raw_output)
        if not json_match:
            logger.warning("Entity extractor: LLM không trả về JSON hợp lệ")
            return _empty_extraction()

        return json.loads(json_match.group())
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Entity extraction failed: {e}")
        return _empty_extraction()


def _empty_extraction() -> dict:
    return {
        "new_characters": [],
        "new_skills": [],
        "character_status_changes": [],
        "new_events": [],
        "new_locations": [],
    }


async def update_neo4j_from_extraction(extracted: dict, project_id: str, neo4j_session) -> None:
    """
    Cập nhật Neo4j dựa trên kết quả extraction.
    BẮT BUỘC gắn project_id vào mọi Node và Relationship.
    """
    try:
        # 1. Tạo nhân vật mới
        for char in extracted.get("new_characters", []):
            await neo4j_session.run(
                """
                MERGE (p:Person {name: $name, project_id: $project_id})
                ON CREATE SET p.description = $description, p.status = 'Alive', p.created_at = datetime()
                ON MATCH SET p.description = coalesce($description, p.description)
                """,
                name=char["name"],
                project_id=project_id,
                description=char.get("description", ""),
            )

        # 2. Tạo skill mới + nối quan hệ với nhân vật
        for skill in extracted.get("new_skills", []):
            await neo4j_session.run(
                """
                MERGE (s:Skill {name: $name, project_id: $project_id})
                ON CREATE SET s.description = $description, s.created_at = datetime()
                """,
                name=skill["name"],
                project_id=project_id,
                description=skill.get("description", ""),
            )
            if skill.get("used_by"):
                await neo4j_session.run(
                    """
                    MATCH (p:Person {name: $person_name, project_id: $project_id})
                    MATCH (s:Skill {name: $skill_name, project_id: $project_id})
                    MERGE (p)-[:OWNS_SKILL {project_id: $project_id}]->(s)
                    """,
                    person_name=skill["used_by"],
                    skill_name=skill["name"],
                    project_id=project_id,
                )

        # 3. Cập nhật trạng thái nhân vật (sống/chết)
        for change in extracted.get("character_status_changes", []):
            if change.get("new_status") == "Dead":
                await neo4j_session.run(
                    """
                    MATCH (p:Person {name: $name, project_id: $project_id})
                    SET p.status = 'Dead', p.death_reason = $reason, p.died_at = datetime()
                    """,
                    name=change["name"],
                    project_id=project_id,
                    reason=change.get("reason", ""),
                )
            elif change.get("new_status") == "Alive":
                await neo4j_session.run(
                    """
                    MATCH (p:Person {name: $name, project_id: $project_id})
                    SET p.status = 'Alive'
                    """,
                    name=change["name"],
                    project_id=project_id,
                )

        # 4. Tạo Event nodes
        for event in extracted.get("new_events", []):
            await neo4j_session.run(
                """
                MERGE (e:Event {name: $name, project_id: $project_id})
                ON CREATE SET e.outcome = $outcome, e.created_at = datetime()
                """,
                name=event["name"],
                project_id=project_id,
                outcome=event.get("outcome", ""),
            )
            for participant in event.get("participants", []):
                await neo4j_session.run(
                    """
                    MATCH (p:Person {name: $person_name, project_id: $project_id})
                    MATCH (e:Event {name: $event_name, project_id: $project_id})
                    MERGE (p)-[:PARTICIPATED_IN {project_id: $project_id}]->(e)
                    """,
                    person_name=participant,
                    event_name=event["name"],
                    project_id=project_id,
                )

        # 5. Tạo Location nodes
        for loc in extracted.get("new_locations", []):
            await neo4j_session.run(
                """
                MERGE (l:Location {name: $name, project_id: $project_id})
                ON CREATE SET l.description = $description, l.created_at = datetime()
                """,
                name=loc["name"],
                project_id=project_id,
                description=loc.get("description", ""),
            )

        logger.info(f"Neo4j updated for project {project_id}: "
                    f"{len(extracted.get('new_characters', []))} chars, "
                    f"{len(extracted.get('new_skills', []))} skills, "
                    f"{len(extracted.get('character_status_changes', []))} status changes")

    except Exception as e:
        logger.error(f"Neo4j update failed for project {project_id}: {e}")
        raise
