"""
Graph API — đọc/ghi Neo4j nodes & edges từ Frontend.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies.auth import get_current_user
from app.db.postgres.session import get_db
from app.db.neo4j.session import get_neo4j_session

router = APIRouter(tags=["graph"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class NodeCreate(BaseModel):
    type: str  # person, location, skill, event, item
    name: str
    description: str = ""
    status: str | None = None  # chỉ dùng cho person


class NodeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class EdgeCreate(BaseModel):
    source: str  # node_id UUID
    target: str  # node_id UUID
    relationship: str  # e.g. KNOWS, ENEMY_OF


class NodeResponse(BaseModel):
    id: str
    type: str
    name: str
    description: str
    status: str | None = None


class EdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    relationship: str


class GraphResponse(BaseModel):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_id(clerk_id: str, db: AsyncSession) -> str:
    result = await db.execute(
        text("SELECT id FROM users WHERE clerk_id = :clerk_id"),
        {"clerk_id": clerk_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
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


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/graph", response_model=GraphResponse)
async def get_graph(
    project_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
):
    """Lấy toàn bộ nodes + edges của project từ Neo4j."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    # Fetch nodes
    node_result = await neo4j_session.run(
        """
        MATCH (n)
        WHERE n.project_id = $project_id AND n.node_id IS NOT NULL
        RETURN n.node_id AS id, labels(n)[0] AS label,
               n.name AS name, n.description AS description, n.status AS status
        """,
        project_id=project_id,
    )
    node_records = await node_result.data()

    nodes = [
        NodeResponse(
            id=r["id"],
            type=r["label"].lower() if r["label"] else "unknown",
            name=r["name"] or "",
            description=r["description"] or "",
            status=r["status"],
        )
        for r in node_records
    ]

    # Fetch edges
    edge_result = await neo4j_session.run(
        """
        MATCH (a)-[r]->(b)
        WHERE a.project_id = $project_id AND b.project_id = $project_id
          AND a.node_id IS NOT NULL AND b.node_id IS NOT NULL
          AND r.edge_id IS NOT NULL
        RETURN r.edge_id AS id, a.node_id AS source, b.node_id AS target,
               type(r) AS relationship
        """,
        project_id=project_id,
    )
    edge_records = await edge_result.data()

    edges = [
        EdgeResponse(
            id=r["id"],
            source=r["source"],
            target=r["target"],
            relationship=r["relationship"],
        )
        for r in edge_records
    ]

    return GraphResponse(nodes=nodes, edges=edges)


@router.post("/projects/{project_id}/graph/nodes", response_model=NodeResponse, status_code=201)
async def create_node(
    project_id: str,
    body: NodeCreate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
):
    """Tạo node thủ công vào Neo4j."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    node_id = str(uuid.uuid4())
    label = body.type.capitalize()  # person → Person

    props: dict = {
        "node_id": node_id,
        "project_id": project_id,
        "name": body.name,
        "description": body.description,
    }
    if body.status:
        props["status"] = body.status

    result = await neo4j_session.run(
        f"""
        CREATE (n:{label} $props)
        RETURN n.node_id AS id, labels(n)[0] AS label,
               n.name AS name, n.description AS description, n.status AS status
        """,
        props=props,
    )
    record = await result.single()

    return NodeResponse(
        id=record["id"],
        type=record["label"].lower() if record["label"] else body.type,
        name=record["name"] or "",
        description=record["description"] or "",
        status=record["status"],
    )


@router.patch("/projects/{project_id}/graph/nodes/{node_id}", response_model=NodeResponse)
async def update_node(
    project_id: str,
    node_id: str,
    body: NodeUpdate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
):
    """Update node properties."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    updates: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.status is not None:
        updates["status"] = body.status

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await neo4j_session.run(
        """
        MATCH (n {node_id: $node_id, project_id: $project_id})
        SET n += $updates
        RETURN n.node_id AS id, labels(n)[0] AS label,
               n.name AS name, n.description AS description, n.status AS status
        """,
        node_id=node_id,
        project_id=project_id,
        updates=updates,
    )
    record = await result.single()

    if not record:
        raise HTTPException(status_code=404, detail="Node not found")

    return NodeResponse(
        id=record["id"],
        type=record["label"].lower() if record["label"] else "unknown",
        name=record["name"] or "",
        description=record["description"] or "",
        status=record["status"],
    )


@router.delete("/projects/{project_id}/graph/nodes/{node_id}", status_code=204)
async def delete_node(
    project_id: str,
    node_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
):
    """Xóa node + tất cả edges liên quan."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    # Check exists first
    check = await neo4j_session.run(
        "MATCH (n {node_id: $node_id, project_id: $project_id}) RETURN n.node_id",
        node_id=node_id,
        project_id=project_id,
    )
    if not await check.single():
        raise HTTPException(status_code=404, detail="Node not found")

    await neo4j_session.run(
        "MATCH (n {node_id: $node_id, project_id: $project_id}) DETACH DELETE n",
        node_id=node_id,
        project_id=project_id,
    )
    return None


@router.post("/projects/{project_id}/graph/edges", response_model=EdgeResponse, status_code=201)
async def create_edge(
    project_id: str,
    body: EdgeCreate,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
):
    """Tạo relationship giữa 2 nodes."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    edge_id = str(uuid.uuid4())
    rel_type = body.relationship.upper().replace(" ", "_")

    result = await neo4j_session.run(
        f"""
        MATCH (a {{node_id: $source, project_id: $project_id}})
        MATCH (b {{node_id: $target, project_id: $project_id}})
        CREATE (a)-[r:{rel_type} {{edge_id: $edge_id, project_id: $project_id}}]->(b)
        RETURN r.edge_id AS id, a.node_id AS source, b.node_id AS target, type(r) AS relationship
        """,
        source=body.source,
        target=body.target,
        project_id=project_id,
        edge_id=edge_id,
    )
    record = await result.single()

    if not record:
        raise HTTPException(status_code=404, detail="Source or target node not found")

    return EdgeResponse(
        id=record["id"],
        source=record["source"],
        target=record["target"],
        relationship=record["relationship"],
    )


@router.delete("/projects/{project_id}/graph/edges/{edge_id}", status_code=204)
async def delete_edge(
    project_id: str,
    edge_id: str,
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    neo4j_session=Depends(get_neo4j_session),
):
    """Xóa một relationship."""
    user_id = await _get_user_id(payload["sub"], db)
    await _assert_project_owner(project_id, user_id, db)

    # Check exists
    check = await neo4j_session.run(
        "MATCH ()-[r {edge_id: $edge_id, project_id: $project_id}]->() RETURN r.edge_id",
        edge_id=edge_id,
        project_id=project_id,
    )
    if not await check.single():
        raise HTTPException(status_code=404, detail="Edge not found")

    await neo4j_session.run(
        "MATCH ()-[r {edge_id: $edge_id, project_id: $project_id}]->() DELETE r",
        edge_id=edge_id,
        project_id=project_id,
    )
    return None
