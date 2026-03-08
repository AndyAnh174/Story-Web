import logging
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class Neo4jConnection:
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            logger.info("Successfully connected to Neo4j graph database.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def close(self):
        if self.driver is not None:
            await self.driver.close()
            logger.info("Closed Neo4j connection.")

neo4j_db = Neo4jConnection()

async def get_neo4j_session():
    """Dependency Injection cho FastAPI routes cần chọc vào Neo4j"""
    if not neo4j_db.driver:
        await neo4j_db.connect()
    
    # Mở một session mới cho mỗi request
    async with neo4j_db.driver.session() as session:
        yield session
