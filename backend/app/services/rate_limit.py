"""Simple Redis-backed rate limiter (falls back to in-memory)."""

from __future__ import annotations

import time
from collections import defaultdict

_memory: dict[str, list[float]] = defaultdict(list)


async def allow_request(key: str, *, limit: int, window_seconds: int = 60) -> bool:
    if limit <= 0:
        return True
    now = time.time()
    try:
        from app.services.redis_client import get_redis

        redis = get_redis()
        pipe_key = f"rl:{key}"
        count = await redis.incr(pipe_key)
        if count == 1:
            await redis.expire(pipe_key, window_seconds)
        return int(count) <= limit
    except Exception:
        bucket = _memory[key]
        cutoff = now - window_seconds
        _memory[key] = [ts for ts in bucket if ts >= cutoff]
        if len(_memory[key]) >= limit:
            return False
        _memory[key].append(now)
        return True
