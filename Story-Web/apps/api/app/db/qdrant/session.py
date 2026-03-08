import logging
from qdrant_client import AsyncQdrantClient
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class QdrantConnection:
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None

    def connect(self):
        try:
            # Qdrant Client thiết kế hỗ trợ async HTTP/gRPC khá tốt
            self.client = AsyncQdrantClient(
                host=settings.QDRANT_HOST, 
                port=settings.QDRANT_PORT
            )
            logger.info(f"Successfully connected to Qdrant vector database at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}.")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def close(self):
        # Qdrant Client sử dụng HTTPx nên đóng connection pool khi app tắt
        pass 

qdrant_db = QdrantConnection()

def get_qdrant_client() -> AsyncQdrantClient:
    """Dependency Injection cho FastAPI routes cần chọc vào Qdrant"""
    if not qdrant_db.client:
        qdrant_db.connect()
    return qdrant_db.client
