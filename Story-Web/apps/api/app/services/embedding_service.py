import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_embedding(text: str) -> list[float]:
    """
    Gọi Ollama embedding endpoint (bge-m3:567m) để vector hóa text.
    Trả về list[float] — vector embedding.
    """
    payload = {
        "model": settings.OLLAMA_MODEL_EMBED,
        "prompt": text,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(settings.OLLAMA_EMBED_HOST, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise RuntimeError(f"Failed to generate embedding: {e}") from e
