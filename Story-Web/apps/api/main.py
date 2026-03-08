from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.neo4j.session import neo4j_db
from app.db.qdrant.session import qdrant_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DBs
    await neo4j_db.connect()
    qdrant_db.connect()
    yield
    # Shutdown: Close connections
    await neo4j_db.close()
    qdrant_db.close()

app = FastAPI(
    title="Story AI Platform API",
    version="1.0.0",
    description="Backend for AI Co-Authoring SaaS",
    lifespan=lifespan
)

# Cấu hình CORS cho Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api"}

@app.get("/")
async def root():
    return {"message": "Welcome to AI Story Platform API"}