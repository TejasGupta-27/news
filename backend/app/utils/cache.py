import hashlib
import json

import redis.asyncio as redis

from app.config import settings

_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(settings.redis_url, decode_responses=True)
    return _pool


def text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


async def get_cached_prediction(hash_key: str) -> dict | None:
    r = await get_redis()
    data = await r.get(f"pred:{hash_key}")
    if data:
        return json.loads(data)
    return None


async def set_cached_prediction(hash_key: str, result: dict):
    r = await get_redis()
    await r.set(f"pred:{hash_key}", json.dumps(result), ex=settings.cache_ttl_seconds)


async def flush_prediction_cache():
    r = await get_redis()
    keys = []
    async for key in r.scan_iter("pred:*"):
        keys.append(key)
    if keys:
        await r.delete(*keys)
