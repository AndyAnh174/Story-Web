"""
AI Service — Giao tiếp với Ollama để sinh văn bản và stream SSE.
"""
import json
import logging
from collections.abc import AsyncGenerator
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def stream_chat(
    system_prompt: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Stream text generation từ Ollama (gpt-oss:120b-cloud).
    Yield từng chunk text để trả về qua SSE.
    """
    payload = {
        "model": settings.OLLAMA_MODEL_GEN,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
            "num_predict": 2048,
        },
    }

    url = f"{settings.OLLAMA_GEN_HOST}/api/chat"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        # Ollama trả về {"done": true} khi xong
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    except httpx.ConnectError:
        logger.error(f"Cannot connect to Ollama at {url}")
        yield "[LỖI: Không thể kết nối tới AI server. Vui lòng kiểm tra Ollama đang chạy.]"
    except Exception as e:
        logger.error(f"AI stream error: {e}")
        yield f"[LỖI: {str(e)}]"


async def generate_once(prompt: str) -> str:
    """
    Gọi Ollama không stream — dùng cho Entity Extraction (background job).
    """
    payload = {
        "model": settings.OLLAMA_MODEL_GEN,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1},  # Nhiệt độ thấp cho structured output
    }
    url = f"{settings.OLLAMA_GEN_HOST}/api/chat"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
