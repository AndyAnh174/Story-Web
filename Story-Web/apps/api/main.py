from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client.models import Distance, VectorParams

from app.core.config import settings
from app.db.neo4j.session import neo4j_db
from app.db.qdrant.session import qdrant_db
from app.db.postgres.session import engine

from app.api.routes import users, projects, chat, lorebooks, chapters, graph

logger = logging.getLogger(__name__)

QDRANT_COLLECTION = "project_memories"
VECTOR_SIZE = 1024  # bge-m3:567m output dimension


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    await neo4j_db.connect()
    qdrant_db.connect()

    # Khởi tạo Qdrant collection nếu chưa tồn tại
    try:
        existing = await qdrant_db.client.get_collections()
        names = [c.name for c in existing.collections]
        if QDRANT_COLLECTION not in names:
            await qdrant_db.client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Qdrant collection '{QDRANT_COLLECTION}' created.")
        else:
            logger.info(f"Qdrant collection '{QDRANT_COLLECTION}' already exists.")
    except Exception as e:
        logger.warning(f"Qdrant collection init skipped: {e}")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await neo4j_db.close()
    qdrant_db.close()
    await engine.dispose()


app = FastAPI(
    title="Story AI Platform API",
    version="1.0.0",
    description="Backend for AI Co-Authoring SaaS",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://truyen.andyanh.id.vn:8981",
        "https://truyen.andyanh.id.vn",
        "https://truyen.andyanh.id.vn:8981",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = settings.API_V1_STR  # /api/v1

app.include_router(users.router, prefix=PREFIX)
app.include_router(projects.router, prefix=PREFIX)
app.include_router(chat.router, prefix=PREFIX)
app.include_router(lorebooks.router, prefix=PREFIX)
app.include_router(chapters.router, prefix=PREFIX)
app.include_router(graph.router, prefix=PREFIX)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api"}


@app.get("/")
async def root():
    return {"message": "Welcome to AI Story Platform API"}
